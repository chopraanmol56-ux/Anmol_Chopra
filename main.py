import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import settings
from .rag.tracing import configure_tracing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("backend")

app = FastAPI(
    title="Document Search Platform API",
    description=(
        "Agentic RAG backend: retrieves relevant chunks from a PGVector "
        "knowledge base and orchestrates a CrewAI agent crew (query analysis, "
        "retrieval, synthesis, groundedness critique) to answer questions over "
        "ingested documents. Includes an OpenAI-compatible `/v1/chat/completions` "
        "endpoint for direct integration with OpenWebUI."
    ),
    version="1.0.0",
    contact={"name": "Document Search Platform"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Starting Document Search Platform backend...")
    configure_tracing()
    logger.info(
        "Config: ollama_llm_model=%s top_k=%d max_agent_iterations=%d tracing=%s",
        settings.ollama_llm_model, settings.top_k, settings.max_agent_iterations, settings.enable_tracing,
    )


@app.get("/", tags=["platform"])
def root() -> dict:
    return {
        "name": "Document Search Platform API",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/api/v1/health",
    }
