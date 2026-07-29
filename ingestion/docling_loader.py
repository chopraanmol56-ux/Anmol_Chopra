"""
Document preprocessing step of the ingestion pipeline.

Uses Docling (https://github.com/docling-project/docling) to parse PDFs into
clean, structure-aware Markdown (headings, tables and reading order preserved),
which is a far better input to a chunker/embedder than raw pdftotext output.
"""
import logging
from pathlib import Path
from typing import List

from docling.document_converter import DocumentConverter
from llama_index.core import Document

logger = logging.getLogger(__name__)


def discover_pdfs(source_dir: str) -> List[Path]:
    """Return every .pdf file directly under `source_dir`, sorted for determinism."""
    base = Path(source_dir)
    if not base.exists():
        raise FileNotFoundError(
            f"Document source directory '{source_dir}' does not exist. "
            f"Create it and place your PDFs there, or set DOC_SOURCE_DIR."
        )
    pdf_paths = sorted(base.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(
            f"No PDF files found in '{source_dir}'. Add PDFs before running ingestion."
        )
    return pdf_paths


def load_pdfs_as_documents(source_dir: str) -> List[Document]:
    """
    Convert every PDF under `source_dir` into a LlamaIndex `Document`.

    Docling extracts each PDF's layout-aware Markdown representation
    (preserving section headings and tables) and stores basic provenance
    (source file name/path, page count) as node metadata, which is later
    surfaced in retrieval results as citations.
    """
    converter = DocumentConverter()
    documents: List[Document] = []

    for pdf_path in discover_pdfs(source_dir):
        logger.info("Converting %s with Docling...", pdf_path.name)
        result = converter.convert(str(pdf_path))
        markdown_text = result.document.export_to_markdown()

        if not markdown_text.strip():
            logger.warning("Docling produced no text for %s - skipping.", pdf_path.name)
            continue

        documents.append(
            Document(
                text=markdown_text,
                metadata={
                    "source_file": pdf_path.name,
                    "source_path": str(pdf_path.resolve()),
                    "num_pages": getattr(result.document, "num_pages", None),
                },
                excluded_llm_metadata_keys=["source_path"],
            )
        )
        logger.info("Converted %s -> %d characters of Markdown", pdf_path.name, len(markdown_text))

    return documents
