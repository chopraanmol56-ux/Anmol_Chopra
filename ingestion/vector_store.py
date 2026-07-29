"""
Vectorization + indexing step of the ingestion pipeline.

Embeds chunks with an Ollama embedding model and persists them into a
PostgreSQL + PGVector-backed LlamaIndex vector store. All connection details
come from `config.settings`, which is entirely environment-driven, so the
same code works against any Postgres instance (local, docker-compose, RDS...)
by simply changing env vars.
"""
import logging
from typing import List

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import BaseNode
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from .config import settings

logger = logging.getLogger(__name__)


def get_embedding_model() -> OllamaEmbedding:
    return OllamaEmbedding(
        model_name=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
        request_timeout=settings.ollama_request_timeout,
    )


def get_vector_store() -> PGVectorStore:
    """
    Build (or connect to) the PGVector-backed table used as the platform's
    knowledge base. `PGVectorStore` creates the table + HNSW index on first
    use if it doesn't already exist.
    """
    return PGVectorStore.from_params(
        database=settings.postgres_db,
        host=settings.postgres_host,
        password=settings.postgres_password,
        port=settings.postgres_port,
        user=settings.postgres_user,
        table_name=settings.pgvector_table,
        schema_name=settings.pgvector_schema,
        embed_dim=settings.embed_dim,
        hnsw_kwargs={
            "hnsw_m": 16,
            "hnsw_ef_construction": 64,
            "hnsw_ef_search": 40,
            "hnsw_dist_method": "vector_cosine_ops",
        },
    )


def build_index(nodes: List[BaseNode]) -> VectorStoreIndex:
    """Embed `nodes` and upsert them into Postgres/PGVector."""
    embed_model = get_embedding_model()
    vector_store = get_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    logger.info(
        "Embedding %d node(s) with '%s' and writing to Postgres table '%s.%s'...",
        len(nodes), settings.ollama_embed_model, settings.pgvector_schema, settings.pgvector_table,
    )
    index = VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
    logger.info("Ingestion complete.")
    return index
