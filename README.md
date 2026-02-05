# Workspace MCP Assistant

This demo provides a FastAPI-backed interface for a Google Workspace MCP wrapper. It includes:

- Chat interface powered by OpenAI or Gemini APIs.
- Send, delete, and list email actions wired to a minimal MCP-style Python class.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables (system env)

- `OPENAI_API_KEY` / `OPENAI_MODEL` (required for OpenAI chat; set in your system env)
- `GEMINI_API_KEY` / `GEMINI_MODEL` (required for Gemini chat; set in your system env)
- `GOOGLE_WORKSPACE_CLIENT_EMAIL`
- `GOOGLE_WORKSPACE_PRIVATE_KEY`
- `GOOGLE_WORKSPACE_DELEGATED_USER`

## Run

Start the API with:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000.

## Chat commands

You can send email commands directly in the chat box using this format:

```
send email to recipient@example.com subject Hello body This is the message.
```

To delete a message by ID:

```
delete email MESSAGE_ID
```
