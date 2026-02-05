import os
from dataclasses import dataclass
from typing import Dict, List, Optional


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


class GoogleWorkspaceMCP:
    """Minimal MCP-style wrapper for Google Workspace actions."""

    def __init__(self, config: WorkspaceConfig) -> None:
        self.config = config

    def send_email(self, to_address: str, subject: str, body: str) -> Dict[str, str]:
        if not to_address or not subject or not body:
            return {
                "status": "error",
                "message": "to, subject, and body are required.",
            }
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
        if not self._has_credentials():
            return {
                "status": "error",
                "message": "Google Workspace credentials are not configured.",
            }
        return {"status": "deleted", "message_id": message_id}

    def list_emails(self, query: Optional[str] = None) -> Dict[str, List[Dict[str, str]]]:
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
