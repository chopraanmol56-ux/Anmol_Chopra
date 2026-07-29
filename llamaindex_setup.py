"""
Read-side LlamaIndex setup: connects to the same Postgres/PGVector table the
ingestion app writes to, and exposes a retriever used by the CrewAI
`RetrievalTool`.
"""
import logging
from typing import List, NamedTuple

from llama_index.core import VectorStoreIndex
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from ..config import settings

logger = logging.getLogger(__name__)


class RetrievedChunk(NamedTuple):
    text: str
    source_file: str
    score: float


_index = None  # lazily built singleton


def get_embedding_model() -> OllamaEmbedding:
    return OllamaEmbedding(
        model_name=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
        request_timeout=settings.ollama_request_timeout,
    )


def get_vector_store() -> PGVectorStore:
    return PGVectorStore.from_params(
        database=settings.postgres_db,
        host=settings.postgres_host,
        password=settings.postgres_password,
        port=settings.postgres_port,
        user=settings.postgres_user,
        table_name=settings.pgvector_table,
        schema_name=settings.pgvector_schema,
        embed_dim=settings.embed_dim,
    )


def get_index() -> VectorStoreIndex:
    global _index
    if _index is None:
        vector_store = get_vector_store()
        _index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=get_embedding_model(),
        )
        logger.info("Connected LlamaIndex to Postgres table '%s.%s'.",
                    settings.pgvector_schema, settings.pgvector_table)
    return _index


def retrieve(query: str, top_k: int = None) -> List[RetrievedChunk]:
    """Semantic search over the knowledge base; returns the top_k chunks with scores."""
    top_k = top_k or settings.top_k
    retriever = get_index().as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)
    return [
        RetrievedChunk(
            text=node.get_content(),
            source_file=node.metadata.get("source_file", "unknown"),
            score=float(node.score) if node.score is not None else 0.0,
        )
        for node in nodes
    ]
