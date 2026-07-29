# Solution Architecture — Document Search Platform

## 1. Component overview

Three independently deployable applications share one codebase and one
PostgreSQL/PGVector knowledge base:

```mermaid
flowchart LR
    subgraph Ingestion["1. Ingestion App (batch/CLI)"]
        A1[PDFs in doc/anmol] --> A2[Docling\npreprocessing]
        A2 --> A3[LlamaIndex\nSentenceSplitter]
        A3 --> A4[Ollama\nembeddings]
        A4 --> A5[(PGVector\ndocument_chunks)]
    end

    subgraph Backend["2. Backend App (FastAPI)"]
        B1[/POST /api/v1/query/]
        B2[/POST /v1/chat/completions/]
        B3[CrewAI Agentic RAG\nQuery Analyst -> Retriever -> Synthesizer -> Critique]
        B4[Ollama LLM]
        B1 --> B3
        B2 --> B3
        B3 -->|semantic search| A5
        B3 --> B4
        B3 -.traces.-> P[Arize Phoenix]
    end

    subgraph Frontend["3. Frontend App"]
        C1[OpenWebUI]
    end

    C1 -->|OpenAI-compatible API| B2
```

## 2. Query-time sequence

```mermaid
sequenceDiagram
    actor User
    participant OWUI as OpenWebUI
    participant API as Backend API
    participant QA as Query Analyst
    participant RET as Retriever Agent
    participant PGV as Postgres/PGVector
    participant SYN as Synthesizer
    participant CRIT as Critique Agent
    participant LLM as Ollama

    User->>OWUI: asks a question
    OWUI->>API: POST /v1/chat/completions
    API->>QA: analyze(query)
    QA->>LLM: rewrite/clarify query
    LLM-->>QA: refined query
    API->>RET: retrieve(refined query)
    RET->>PGV: vector similarity search (top_k)
    PGV-->>RET: top-k chunks + scores
    API->>SYN: synthesize(query, context)
    SYN->>LLM: generate grounded answer
    LLM-->>SYN: draft answer
    API->>CRIT: critique(query, context, answer)
    CRIT->>LLM: groundedness check
    LLM-->>CRIT: VERDICT
    alt NOT_GROUNDED and iterations remain
        API->>RET: retrieve again (refined query)
    else GROUNDED
        API-->>OWUI: final answer + sources + trace_id
        OWUI-->>User: rendered answer
    end
```

## 3. Ingestion-time sequence

```mermaid
sequenceDiagram
    participant CLI as Ingestion CLI
    participant DOC as Docling
    participant LI as LlamaIndex Splitter
    participant EMB as Ollama Embeddings
    participant PGV as Postgres/PGVector

    CLI->>DOC: convert each PDF
    DOC-->>CLI: structure-aware Markdown + metadata
    CLI->>LI: split into overlapping chunks
    LI-->>CLI: nodes (text + metadata)
    CLI->>EMB: embed each node
    EMB-->>CLI: vectors
    CLI->>PGV: upsert (vector, text, metadata)
```

## 4. Deployment view

All services run as containers via `docker-compose.yml`:

| Service | Image/Build | Purpose |
|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | Vector knowledge base |
| `ollama` | `ollama/ollama` | Local LLM + embedding inference |
| `phoenix` | `arizephoenix/phoenix` | Tracing/observability UI + OTLP collector |
| `ingestion` | built from `ingestion/Dockerfile` | One-off job (`profiles: tools`) |
| `backend` | built from `backend/Dockerfile` | FastAPI Agentic RAG API |
| `openwebui` | `ghcr.io/open-webui/open-webui` | Chat frontend |

## 5. Key design decisions

- **Docling over naive PDF text extraction**: preserves headings/tables and
  reading order, which meaningfully improves chunk quality for RAG.
- **PGVector over a dedicated vector DB**: keeps the whole platform on one
  well-understood, easy-to-self-host datastore; HNSW indexing keeps
  retrieval fast at the scale a single-team knowledge base needs.
- **CrewAI sequential agents with a critique loop** rather than a single
  retrieve→generate call: adds a genuine agentic/self-correcting step
  (re-retrieval on a failed groundedness check) while staying easy to trace
  and reason about — each stage is one agent, one task, one LLM call.
- **Prompts externalized as YAML**: satisfies the requirement that prompts
  be manageable independently of application code, and keeps `crew_agents.py`
  free of embedded prompt strings.
- **OpenAI-compatible endpoint for the frontend integration**: avoids
  needing a custom OpenWebUI plugin/pipeline — OpenWebUI treats the backend
  as just another OpenAI-compatible provider.

## 6. Known limitations / next steps

- Ingestion is currently additive; add delete-by-`source_file` before
  re-insert for clean re-ingestion of updated PDFs.
- `/v1/chat/completions` doesn't stream yet (see backend README).
- Per-request `top_k` override is accepted by the API schema but not yet
  wired through to the retriever.
- RAGAs evaluation test set (`doc/eval/testset.json`) ships with placeholder
  ground truths — replace with answers grounded in your real PDFs before
  treating the scores as meaningful.
