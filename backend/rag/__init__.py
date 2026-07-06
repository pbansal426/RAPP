import os

import structlog

from backend.core.config import settings
from backend.rag.retriever import retrieve
from backend.rag.vector_store import ChromaVectorStore, MockVectorStore, VectorStore

logger = structlog.get_logger()

# We maintain a singleton instance of the vector store to avoid re-initializing
# ChromaDB connection pools on every request.
_vector_store_instance: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """
    Get or create the singleton VectorStore instance.

    The knowledge base (``data/chroma_db``) lives on an external SSD. When the SSD is
    unplugged that path is a dangling symlink and constructing ``ChromaVectorStore``
    raises. Rather than 500, we degrade gracefully: return a transient, empty
    ``MockVectorStore`` **without caching it**, so a later call (once the SSD is
    plugged back in) retries the real store. Only a successfully-constructed
    ChromaDB store is cached as the singleton.

    Returns:
        VectorStore: The active vector store implementation.
    """
    global _vector_store_instance

    if _vector_store_instance is not None:
        return _vector_store_instance

    # CI/test runs always get the mock store, regardless of VECTOR_STORE --
    # a real ChromaDB path could still resolve locally and quietly do
    # nothing useful (or, with Gemini embeddings opted in, dial out).
    store_type = (
        "mock"
        if settings.is_test_mode
        else os.environ.get("VECTOR_STORE", "chroma").lower()
    )
    if store_type == "mock":
        _vector_store_instance = MockVectorStore()
        return _vector_store_instance

    db_path = os.environ.get("CHROMA_DB_PATH", "./data/chroma_db")
    try:
        _vector_store_instance = ChromaVectorStore(
            persistent_path=db_path, collection_name="repair_manuals"
        )
        return _vector_store_instance
    except Exception as exc:  # noqa: BLE001 - degrade instead of crashing the request
        # Most likely the SSD holding the KB is unplugged (dangling symlink).
        # Serve an empty store for this call and do NOT cache it, so retrieval
        # recovers automatically once the drive is back.
        logger.warning(
            "Vector store unavailable; degrading to empty results "
            "(is the knowledge-base SSD connected?)",
            path=db_path,
            error=str(exc),
        )
        return MockVectorStore()


__all__ = ["retrieve", "get_vector_store", "VectorStore"]
