# Frontend — OpenWebUI

The frontend is [OpenWebUI](https://github.com/open-webui/open-webui), used
as-is (no fork required) and pointed at the backend's OpenAI-compatible API.
No frontend code lives in this repo — this folder documents how the two are
wired together.

## How the integration works

OpenWebUI can talk to any server that implements the OpenAI `/v1/chat/completions`
and `/v1/models` contract. The backend implements exactly that (see
`../backend/src/api/routes.py`), so OpenWebUI is configured as if the backend
were an OpenAI-compatible provider — every chat message a user sends is
routed to the Agentic RAG pipeline instead of a raw LLM completion.

```
Browser  ──►  OpenWebUI (chat UI)  ──►  Backend /v1/chat/completions  ──►  CrewAI agents ──► PGVector + Ollama
```

## Running via Docker Compose (recommended)

Already wired up in the root `docker-compose.yml` — the `openwebui` service's
`OPENAI_API_BASE_URL` is pre-set to the backend:

```bash
docker compose up -d
```

Open http://localhost:3000, create the first (admin) account, and start
chatting — the `document-search-agentic-rag` model should already appear in
the model dropdown.

## Manual configuration (running OpenWebUI standalone)

If you're running OpenWebUI separately (not via this repo's compose file):

1. Start it, e.g. `docker run -p 3000:8080 ghcr.io/open-webui/open-webui:main`
2. Sign in as an admin, go to **Admin Settings → Connections → OpenAI API**
3. Add a connection:
   - **API Base URL**: `http://<backend-host>:8000/v1`
   - **API Key**: any non-empty string (the backend doesn't check it)
4. Save, then start a new chat and select `document-search-agentic-rag` from
   the model picker.

## What you get for free from OpenWebUI

- Chat history, multi-user accounts, RBAC (if enabled)
- Markdown/code rendering of answers
- Regenerate / continue / copy on responses

## What's intentionally out of scope here

- OpenWebUI's own RAG/"Documents" feature is not used — retrieval happens
  entirely in the backend against the PGVector knowledge base, so OpenWebUI
  stays a thin chat client.
- Streaming responses (see `backend/README.md#known-extension-points`).
