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
- `GOOGLE_OAUTH_CLIENT_ID` (required for OAuth email actions)
- `GOOGLE_OAUTH_CLIENT_SECRET` (required for OAuth email actions)
- `GOOGLE_OAUTH_TOKEN_FILE` (optional; defaults to `token.json`)
- `GOOGLE_WORKSPACE_CLIENT_EMAIL` (service-account option)
- `GOOGLE_WORKSPACE_PRIVATE_KEY` (service-account option)
- `GOOGLE_WORKSPACE_DELEGATED_USER` (service-account option)

## Run

Start the API with:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000.

## Chat commands

Send email directly in chat:

```
send email to recipient@example.com subject Hello body This is the message.
send email to recipient@example.com body This is the message.
send email to recipient@example.com message This is the message.
send email to recipient@example.com This is the message.
send email
```

Delete a message by ID:

```
delete email MESSAGE_ID
```

List emails (optional query):

```
list emails
list emails from:me
```

## Gmail OAuth setup (client ID + secret)

1. Create an OAuth client ID in Google Cloud Console (Desktop app).
2. Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`.
3. Start the app and run any chat command that sends/list/deletes emails.
4. A browser window will open for consent and store a token in `token.json`.
