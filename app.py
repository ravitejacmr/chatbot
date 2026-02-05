import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from google_workspace_mcp import GoogleWorkspaceMCP, WorkspaceConfig


@dataclass
class ChatConfig:
    openai_api_key: str
    openai_model: str
    gemini_api_key: str
    gemini_model: str

    @classmethod
    def from_env(cls) -> "ChatConfig":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", ""),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", ""),
        )


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


SEND_EMAIL_PATTERN = re.compile(
    r"send email to\\s+(?P<to>[^\\s]+)"
    r"(?:\\s+subject\\s+(?P<subject>.+?))?"
    r"(?:\\s+(?:body|message)\\s+(?P<body>.+))?$",
    re.IGNORECASE | re.DOTALL,
)

DELETE_EMAIL_PATTERN = re.compile(
    r"delete email\\s+(?P<message_id>[\\w-]+)", re.IGNORECASE
)

LIST_EMAILS_PATTERN = re.compile(r"list emails(?:\\s+(?P<query>.+))?$", re.IGNORECASE)


def parse_chat_intent(message: str) -> Optional[Dict[str, str]]:
    send_match = SEND_EMAIL_PATTERN.search(message)
    if send_match:
        subject = send_match.group("subject") or ""
        body = send_match.group("body") or ""
        if not body:
            remainder = message[send_match.end("to") :].strip()
            if remainder.lower().startswith("subject"):
                remainder = remainder[len("subject") :].strip()
            body = remainder
        return {
            "intent": "send_email",
            "to": send_match.group("to").strip(),
            "subject": subject.strip(),
            "body": body.strip(),
        }
    delete_match = DELETE_EMAIL_PATTERN.search(message)
    if delete_match:
        return {
            "intent": "delete_email",
            "message_id": delete_match.group("message_id").strip(),
        }
    list_match = LIST_EMAILS_PATTERN.search(message.strip())
    if list_match:
        query = list_match.group("query")
        return {
            "intent": "list_emails",
            "query": query.strip() if query else "",
        }
    return None


def build_chat_response(provider: str, message: str, config: ChatConfig) -> Dict[str, Any]:
    provider = provider.lower()
    if provider == "gemini":
        if not config.gemini_api_key:
            raise HTTPException(status_code=400, detail="GEMINI_API_KEY is not set.")
        if not config.gemini_model:
            raise HTTPException(status_code=400, detail="GEMINI_MODEL is not set.")
        return call_gemini(config.gemini_api_key, config.gemini_model, message)
    if not config.openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not set.")
    if not config.openai_model:
        raise HTTPException(status_code=400, detail="OPENAI_MODEL is not set.")
    return call_openai(config.openai_api_key, config.openai_model, message)


def call_openai(api_key: str, model: str, message: str) -> Dict[str, Any]:
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "temperature": 0.3,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return {"provider": "openai", "reply": content}


def call_gemini(api_key: str, model: str, message: str) -> Dict[str, Any]:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    response = requests.post(
        url,
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": message}]}], "temperature": 0.3},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    reply = data["candidates"][0]["content"]["parts"][0]["text"]
    return {"provider": "gemini", "reply": reply}


@app.post("/api/chat")
def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    message = str(payload.get("message", "")).strip()
    provider = str(payload.get("provider", "openai"))
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")
    try:
        intent = parse_chat_intent(message)
        if intent and intent["intent"] == "send_email":
            mcp = GoogleWorkspaceMCP(WorkspaceConfig.from_env())
            return {
                "reply": "Email request received.",
                "action": mcp.send_email(
                    to_address=intent["to"],
                    subject=intent["subject"],
                    body=intent["body"],
                ),
            }
        if intent and intent["intent"] == "delete_email":
            mcp = GoogleWorkspaceMCP(WorkspaceConfig.from_env())
            return {
                "reply": "Delete request received.",
                "action": mcp.delete_email(message_id=intent["message_id"]),
            }
        if intent and intent["intent"] == "list_emails":
            mcp = GoogleWorkspaceMCP(WorkspaceConfig.from_env())
            return {
                "reply": "Listing emails.",
                "action": mcp.list_emails(query=intent["query"]),
            }
        return build_chat_response(provider, message, ChatConfig.from_env())
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    except requests.RequestException:
        return JSONResponse(
            status_code=502,
            content={"error": "Upstream chat provider request failed."},
        )


@app.post("/api/email/send")
def send_email(payload: Dict[str, Any]) -> Dict[str, Any]:
    config = WorkspaceConfig.from_env()
    mcp = GoogleWorkspaceMCP(config)
    return mcp.send_email(
        to_address=str(payload.get("to", "")),
        subject=str(payload.get("subject", "")),
        body=str(payload.get("body", "")),
    )


@app.post("/api/email/delete")
def delete_email(payload: Dict[str, Any]) -> Dict[str, Any]:
    config = WorkspaceConfig.from_env()
    mcp = GoogleWorkspaceMCP(config)
    return mcp.delete_email(message_id=str(payload.get("message_id", "")))


@app.get("/api/email/list")
def list_emails(query: Optional[str] = None) -> Dict[str, Any]:
    config = WorkspaceConfig.from_env()
    mcp = GoogleWorkspaceMCP(config)
    return mcp.list_emails(query=query)
