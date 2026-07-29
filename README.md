# Document Search Platform
 
An end-to-end Generative AI platform for searching and answering questions
over a private PDF document collection, built as three apps in one codebase:
 
1. **Ingestion pipeline** (`ingestion/`) — reads PDFs, preprocesses them with
   Docling, chunks and embeds them, and indexes them into PostgreSQL/PGVector.
2. **Agentic RAG backend** (`backend/`) — a FastAPI service that retrieves
   relevant chunks and orchestrates a CrewAI multi-agent pipeline (query
   analysis → retrieval → synthesis → groundedness critique) to answer
   questions, with full inference tracing and RAGAs-based evaluation.
3. **Frontend** (`frontend/`) — [OpenWebUI](https://github.com/open-webui/open-webui),
   configured against the backend's OpenAI-compatible API.
Built to satisfy the "Document Search Platform" technical assessment (see
`doc/` for supplementary documentation referenced below).
 
## Architecture at a glance
 
```
doc/anmol/*.pdf
      │
      ▼
┌─────────────┐   Docling → LlamaIndex splitter → Ollama embeddings
│  Ingestion   │ ─────────────────────────────────────────────────►  Postgres
└─────────────┘                                                      + PGVector
                                                                          ▲
                                                                          │ semantic search
┌─────────────┐   CrewAI: Query Analyst → Retriever → Synthesizer →      │
│   Backend    │   Groundedness Critique  ◄───────────────────────────────
│ (FastAPI)    │        │                     ▲
└──────┬──────┘        ▼                     │ generation
       │           Ollama LLM ────────────────┘
       │ /v1/chat/completions (OpenAI-compatible)
       ▼
┌─────────────┐
│  OpenWebUI   │  (chat UI)
└─────────────┘
```
 
Full component diagram, sequence diagrams, and design rationale:
**[`doc/architecture.md`](doc/architecture.md)**.
 
## Repository layout
 
```
document-search-platform/
├── ingestion/              # App 1: PDF -> vectors -> Postgres
│   ├── src/                #   Docling loader, chunker, PGVector writer, CLI
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── backend/                # App 2: Agentic RAG REST API
│   ├── src/
│   │   ├── api/            #   FastAPI routes + Pydantic schemas
│   │   ├── rag/            #   CrewAI agents, LlamaIndex retriever, prompts/, tracing
│   │   └── evaluation/      #   RAGAs evaluation script
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── frontend/                # App 3: OpenWebUI integration notes (no custom code)
│   └── README.md
├── doc/                      # Supplementary/technical documentation (see below)
├── scripts/setup.sh          # Local (non-docker) bootstrap helper
├── docker-compose.yml         # Full stack: postgres, ollama, phoenix, backend, openwebui
├── .env.example
└── README.md                  # you are here
```
 
## Mandatory tools/frameworks used
 
| Requirement | Used as |
|---|---|
| Docling | PDF preprocessing (`ingestion/src/docling_loader.py`) |
| PostgreSQL + PGVector | Vector database (both apps, via `llama-index-vector-stores-postgres`) |
| LlamaIndex | Splitting, embeddings, retrieval (`ingestion/src/`, `backend/src/rag/llamaindex_setup.py`) |
| CrewAI | Multi-agent Agentic RAG pipeline (`backend/src/rag/crew_agents.py`) |
| Ollama | Local LLM + embedding provider (both apps) |
| Arize Phoenix | Tracing/observability (`backend/src/rag/tracing.py`) |
| RAGAs | RAG evaluation (`backend/src/evaluation/ragas_eval.py`) |
| OpenWebUI | Frontend chat UI (`frontend/README.md`, `docker-compose.yml`) |
 
## Quick start (Docker Compose — recommended)
 
Prerequisites: Docker + Docker Compose, ~10GB free disk for model weights.
 
```bash
git clone <this-repo> && cd document-search-platform
cp .env.example .env               # edit if you need non-default ports/credentials
 
# 1. Add your PDFs
cp /path/to/your/*.pdf doc/anmol/
 
# 2. Start the data + inference services
docker compose up -d postgres ollama phoenix
 
# 3. Pull the models the platform uses
docker compose exec ollama ollama pull llama3.1
docker compose exec ollama ollama pull nomic-embed-text
 
# 4. Ingest your PDFs (one-off job)
docker compose run --rm ingestion
 
# 5. Start the backend + frontend
docker compose up -d backend openwebui
```
 
Now:
- **Chat UI**: http://localhost:3000 (OpenWebUI — create the first admin account)
- **API docs**: http://localhost:8000/docs (Swagger UI)
- **Tracing UI**: http://localhost:6006 (Arize Phoenix)
## Quick start (without Docker)
 
See [`scripts/setup.sh`](scripts/setup.sh) for a scripted local bootstrap, or
follow the per-app instructions in `ingestion/README.md` and
`backend/README.md`. You'll still need a reachable Postgres instance with
the `pgvector` extension enabled, and Ollama installed locally.
 
## Configuration
 
Every setting across all three apps is an environment variable — see
[`.env.example`](.env.example) for the full list (Postgres connection,
Ollama base URL/models, chunk size/overlap, retrieval `top_k`, tracing
endpoint, CORS, etc.). Nothing is hard-coded.
 
## Supplementary documentation (`doc/`)
 
| Document | Contents |
|---|---|
| [`doc/architecture.md`](doc/architecture.md) | Solution architecture, component + sequence diagrams, design decisions, known limitations |
| [`doc/evaluation.md`](doc/evaluation.md) | RAGAs evaluation methodology, metrics explained, how to run it |
| [`doc/api/openapi.yaml`](doc/api/openapi.yaml) | Static OpenAPI/Swagger spec snapshot (live spec always at `/openapi.json`) |
| [`doc/eval/testset.json`](doc/eval/testset.json) | RAGAs test question set (replace placeholder ground truths with your own) |
| [`doc/presentation/document-search-platform.pptx`](doc/presentation) | Solution walkthrough deck |
| [`doc/anmol/`](doc/anmol) | Drop your source PDFs here for ingestion |
 
Each app also has its own README with app-specific detail:
[`ingestion/README.md`](ingestion/README.md) ·
[`backend/README.md`](backend/README.md) ·
[`frontend/README.md`](frontend/README.md)
 
## Testing
 
```bash
# Ingestion (unit tests, no live services needed)
cd ingestion && pip install -r requirements.txt pytest && pytest
 
# Backend (API tests mock the CrewAI pipeline, no live services needed)
cd backend && pip install -r requirements.txt pytest && pytest
 
# RAGAs evaluation (integration-level; needs the full live stack)
cd backend && python -m src.evaluation.ragas_eval
```
 
## Known limitations
 
Tracked in detail in `doc/architecture.md#6-known-limitations--next-steps`:
ingestion isn't yet idempotent on re-runs, chat completions don't stream,
and per-request `top_k` isn't threaded through end-to-end. None of these
block the platform from working end-to-end; they're documented as the
natural next iteration.
 
