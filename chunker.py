import logging
from typing import List
 
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode
 
logger = logging.getLogger(__name__)
 
 
def chunk_documents(
    documents: List[Document],
    chunk_size: int,
    chunk_overlap: int,
) -> List[BaseNode]:
    """Split documents into nodes, preserving each node's source metadata."""
    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        include_metadata=True,
        include_prev_next_rel=True,
    )
    nodes = splitter.get_nodes_from_documents(documents, show_progress=True)
    logger.info(
        "Split %d document(s) into %d chunk(s) (chunk_size=%d, overlap=%d)",
        len(documents), len(nodes), chunk_size, chunk_overlap,
    )
    return nodes
 
