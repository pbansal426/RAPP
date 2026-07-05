import os

from backend.rag.retriever import retrieve
from backend.rag.vector_store import ChromaVectorStore, MockVectorStore, VectorStore

# We maintain a singleton instance of the vector store to avoid re-initializing
# ChromaDB connection pools on every request.
_vector_store_instance: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """
    Get or create the singleton VectorStore instance.

    Returns:
        VectorStore: The active vector store implementation.
    """
    global _vector_store_instance

    if _vector_store_instance is None:
        store_type = os.environ.get("VECTOR_STORE", "chroma").lower()
        if store_type == "mock":
            _vector_store_instance = MockVectorStore()
        else:
            db_path = os.environ.get("CHROMA_DB_PATH", "./data/chroma_db")
            _vector_store_instance = ChromaVectorStore(
                persistent_path=db_path, collection_name="repair_manuals"
            )

    return _vector_store_instance


__all__ = ["retrieve", "get_vector_store", "VectorStore"]
