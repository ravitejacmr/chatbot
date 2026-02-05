import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
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
    return build_chat_response(provider, message, ChatConfig.from_env())


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
