import base64
import os
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow


@dataclass
class WorkspaceConfig:
    client_email: str
    private_key: str
    delegated_user: str

    @classmethod
    def from_env(cls) -> "WorkspaceConfig":
        return cls(
            client_email=os.getenv("GOOGLE_WORKSPACE_CLIENT_EMAIL", ""),
            private_key=os.getenv("GOOGLE_WORKSPACE_PRIVATE_KEY", ""),
            delegated_user=os.getenv("GOOGLE_WORKSPACE_DELEGATED_USER", ""),
        )


@dataclass
class OAuthConfig:
    client_id: str
    client_secret: str
    token_file: str

    @classmethod
    def from_env(cls) -> "OAuthConfig":
        return cls(
            client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", ""),
            token_file=os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "token.json"),
        )


class GoogleWorkspaceMCP:
    """Minimal MCP-style wrapper for Google Workspace actions."""

    def __init__(self, config: WorkspaceConfig) -> None:
        self.config = config
        self.oauth_config = OAuthConfig.from_env()

    def send_email(self, to_address: str, subject: str, body: str) -> Dict[str, str]:
        if not to_address or not subject or not body:
            return {
                "status": "error",
                "message": "to, subject, and body are required.",
            }
        if self._has_oauth_config():
            return self._send_email_oauth(to_address, subject, body)
        if not self._has_credentials():
            return {
                "status": "error",
                "message": "Google Workspace credentials are not configured.",
            }
        return {
            "status": "queued",
            "message": "Email queued for delivery.",
            "to": to_address,
        }

    def delete_email(self, message_id: str) -> Dict[str, str]:
        if not message_id:
            return {"status": "error", "message": "message_id is required."}
        if self._has_oauth_config():
            return self._delete_email_oauth(message_id)
        if not self._has_credentials():
            return {
                "status": "error",
                "message": "Google Workspace credentials are not configured.",
            }
        return {"status": "deleted", "message_id": message_id}

    def list_emails(self, query: Optional[str] = None) -> Dict[str, List[Dict[str, str]]]:
        if self._has_oauth_config():
            return self._list_emails_oauth(query=query)
        if not self._has_credentials():
            return {
                "emails": [],
                "warning": "Google Workspace credentials are not configured.",
            }
        return {
            "emails": [
                {
                    "id": "sample-123",
                    "from": "demo@example.com",
                    "subject": "Welcome to Workspace MCP",
                    "snippet": "Replace this with a real Gmail API call.",
                }
            ],
            "query": query or "",
        }

    def _has_credentials(self) -> bool:
        return all(
            [
                self.config.client_email,
                self.config.private_key,
                self.config.delegated_user,
            ]
        )

    def _has_oauth_config(self) -> bool:
        return bool(self.oauth_config.client_id and self.oauth_config.client_secret)

    def _get_oauth_credentials(self) -> Credentials:
        scopes = [
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
        ]
        creds = None
        if os.path.exists(self.oauth_config.token_file):
            creds = Credentials.from_authorized_user_file(
                self.oauth_config.token_file, scopes
            )
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": self.oauth_config.client_id,
                        "client_secret": self.oauth_config.client_secret,
                        "redirect_uris": ["http://localhost:8080/"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes,
            )
            creds = flow.run_local_server(port=8080)
            with open(self.oauth_config.token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
        return creds

    def _get_gmail_service(self):
        creds = self._get_oauth_credentials()
        return build("gmail", "v1", credentials=creds)

    def _send_email_oauth(self, to_address: str, subject: str, body: str) -> Dict[str, str]:
        try:
            service = self._get_gmail_service()
            message = EmailMessage()
            message["To"] = to_address
            message["Subject"] = subject
            message.set_content(body)
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            result = (
                service.users()
                .messages()
                .send(userId="me", body={"raw": raw_message})
                .execute()
            )
            return {"status": "sent", "message_id": result.get("id", "")}
        except HttpError as exc:
            return {
                "status": "error",
                "message": "Gmail API error.",
                "detail": str(exc),
            }

    def _delete_email_oauth(self, message_id: str) -> Dict[str, str]:
        try:
            service = self._get_gmail_service()
            service.users().messages().delete(userId="me", id=message_id).execute()
            return {"status": "deleted", "message_id": message_id}
        except HttpError as exc:
            return {
                "status": "error",
                "message": "Gmail API error.",
                "detail": str(exc),
            }

    def _list_emails_oauth(
        self, query: Optional[str] = None
    ) -> Dict[str, List[Dict[str, str]]]:
        try:
            service = self._get_gmail_service()
            result = (
                service.users()
                .messages()
                .list(userId="me", q=query or "", maxResults=10)
                .execute()
            )
            messages = []
            for item in result.get("messages", []):
                detail = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=item["id"],
                        format="metadata",
                        metadataHeaders=["From", "Subject"],
                    )
                    .execute()
                )
                headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
                messages.append(
                    {
                        "id": item["id"],
                        "from": headers.get("From", ""),
                        "subject": headers.get("Subject", ""),
                        "snippet": detail.get("snippet", ""),
                    }
                )
            return {"emails": messages, "query": query or ""}
        except HttpError as exc:
            return {"emails": [], "error": "Gmail API error.", "detail": str(exc)}
