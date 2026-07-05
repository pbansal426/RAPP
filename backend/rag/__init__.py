import os
import threading
from typing import Optional
from backend.rag.vector_store import VectorStore, ChromaVectorStore, MockVectorStore

_vector_store_instance: Optional[VectorStore] = None
_vector_store_lock = threading.Lock()

def get_vector_store() -> VectorStore:
    """
    Factory function producing a singleton instance of the configured vector store backend.
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        with _vector_store_lock:
            if _vector_store_instance is None:
                store_type = os.getenv("VECTOR_STORE", "chromadb").lower()
                if store_type == "chromadb":
                    persistent_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
                    use_gemini = os.getenv("USE_GEMINI_EMBEDDINGS", "true").lower() == "true"
                    _vector_store_instance = ChromaVectorStore(
                        persistent_path=persistent_path,
                        use_gemini_embeddings=use_gemini
                    )
                elif store_type == "mock":
                    _vector_store_instance = MockVectorStore()
                else:
                    raise ValueError(f"Unsupported VECTOR_STORE backend type: '{store_type}'")
    return _vector_store_instance

# Delayed import to avoid circular imports during module load
from backend.rag.retriever import retrieve

__all__ = [
    "VectorStore",
    "ChromaVectorStore",
    "MockVectorStore",
    "get_vector_store",
    "retrieve"
]
