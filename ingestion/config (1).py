"""
Centralised, environment-driven configuration for the ingestion app.
Nothing here is hard-coded: every value can be overridden via an environment
variable (or a `.env` file loaded by docker-compose / python-dotenv).
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # no-op if .env doesn't exist (e.g. inside a container using env_file)


@dataclass(frozen=True)
class Settings:
    # PostgreSQL / PGVector
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "docsearch")
    postgres_user: str = os.getenv("POSTGRES_USER", "docsearch")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "docsearch")
    pgvector_table: str = os.getenv("PGVECTOR_TABLE", "document_chunks")
    pgvector_schema: str = os.getenv("PGVECTOR_SCHEMA", "public")
    embed_dim: int = int(os.getenv("PGVECTOR_EMBED_DIM", "768"))

    # Source documents
    doc_source_dir: str = os.getenv("DOC_SOURCE_DIR", "doc/anmol")

    # Chunking
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "512"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "64"))

    # Ollama (embeddings)
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    ollama_request_timeout: float = float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "120"))


settings = Settings()
