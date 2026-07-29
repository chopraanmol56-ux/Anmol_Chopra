# Backend — Agentic RAG API

A FastAPI service that answers questions over the ingested document
knowledge base using a CrewAI multi-agent pipeline, and exposes both a
native REST API and an OpenAI-compatible endpoint for OpenWebUI.

## Agentic RAG pipeline

```
User query
   │
   ▼
┌────────────────────┐
│  Query Analyst      │  rewrites/clarifies the query for retrieval
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Knowledge Base       │  calls the knowledge_base_search tool
│ Retriever            │  (LlamaIndex retriever over PGVector)
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Answer Synthesizer   │  answers strictly from retrieved context,
└─────────┬──────────┘  cites source file per claim
          ▼
┌────────────────────┐
│ Groundedness         │  checks the answer against the context
│ Reviewer             │
└─────────┬──────────┘
          │  NOT_GROUNDED → loop back to retrieval with a refined
          │  query (up to MAX_AGENT_ITERATIONS times)
          ▼
      Final answer + sources + trace id
```

This loop — critique triggering another retrieval pass — is what makes the
pipeline "agentic" rather than a single fixed retrieve→generate chain. See
`src/rag/crew_agents.py`.

## Prompts are externalized

Every agent's role/goal/backstory and every task prompt template lives in
`src/rag/prompts/*.yaml`, not inline in Python:

| File | Contents |
|---|---|
| `agents.yaml` | Role/goal/backstory for all 4 CrewAI agents |
| `query_analyzer.yaml` | Query-rewriting task prompt |
| `synthesis.yaml` | Answer-generation task prompt |
| `critique.yaml` | Groundedness-check task prompt |
| `system.yaml` | General system message |

`src/rag/prompt_manager.py` loads and renders these at request time and
supports `reload()` to bust its cache, so prompts can be iterated on without
a code change or restart.

## Tracing (Arize Phoenix)

`src/rag/tracing.py` instruments both LlamaIndex (retrieval + embedding
calls) and CrewAI (agent/task/tool calls) via OpenInference, and ships spans
to a Phoenix collector (`PHOENIX_COLLECTOR_ENDPOINT`). Every `/api/v1/query`
and `/v1/chat/completions` response includes a `trace_id` you can look up in
the Phoenix UI (`http://localhost:6006` in the default docker-compose setup)
to inspect the full agent trajectory, prompts, retrieved chunks, and latency
for that request. Disable with `ENABLE_TRACING=false`.

## Evaluation (RAGAs)

`src/evaluation/ragas_eval.py` runs a test set of questions through the live
pipeline and scores it on faithfulness, answer relevancy, context precision,
and context recall:

```bash
python -m src.evaluation.ragas_eval --testset ../doc/eval/testset.json --out ../doc/eval/ragas_results.csv
```

Replace the placeholder `ground_truth` values in `doc/eval/testset.json`
with answers grounded in your actual ingested PDFs before running this for
real — see `doc/evaluation.md` for methodology notes.

## REST API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | Postgres + Ollama connectivity check |
| `POST` | `/api/v1/query` | Run the agentic RAG pipeline for one question |
| `GET` | `/v1/models` | OpenAI-compatible model listing (used by OpenWebUI) |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat endpoint (used by OpenWebUI) |
| `GET` | `/docs` | Interactive Swagger UI |
| `GET` | `/openapi.json` | Raw OpenAPI schema |

A static snapshot of the OpenAPI spec is also kept at `../doc/api/openapi.yaml`
per the assessment's documentation requirements.

### Example

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the escalation process for a P1 incident?"}'
```

```json
{
  "answer": "... (source: handbook.pdf)",
  "sources": [{"source_file": "handbook.pdf", "score": 0.87}],
  "rewritten_query": "P1 incident escalation process",
  "grounded": true,
  "iterations": 1,
  "latency_ms": 842.3,
  "trace_id": "4b1f9c2e8a3d4f7b9c0e1a2b3c4d5e6f"
}
```

## Configuration

All configuration is via environment variables — see `../.env.example` and
`src/config.py`. Notable ones: `OLLAMA_LLM_MODEL`, `TOP_K`,
`MAX_AGENT_ITERATIONS`, `PHOENIX_COLLECTOR_ENDPOINT`, `ENABLE_TRACING`.

## Running locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

ollama pull llama3.1
ollama pull nomic-embed-text

export $(grep -v '^#' ../.env | xargs)
uvicorn src.main:app --reload --port 8000
```

Then open http://localhost:8000/docs for interactive Swagger docs.

## Running tests

```bash
pip install pytest
pytest
```

(`test_api.py` mocks the CrewAI pipeline so it runs without a live
Postgres/Ollama/Phoenix stack; `ragas_eval.py` is an integration script that
does need the live stack, by design.)

## Known extension points

- **Streaming**: `/v1/chat/completions` currently returns a single
  non-streamed message even when `stream: true` is requested. To stream,
  wrap the synthesis stage in a `StreamingResponse` yielding
  `data: {...}\n\n` SSE chunks in the OpenAI streaming format.
- **Per-request `top_k`**: `QueryRequest.top_k` is accepted by the schema
  but not yet threaded into `run_agentic_rag`; thread it through as a
  parameter instead of relying on the global `TOP_K` setting.
- **Idempotent ingestion**: see `ingestion/README.md`.
