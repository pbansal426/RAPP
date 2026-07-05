"""Re-index existing TSB data with Gemini embeddings.

This script loads existing TSB chunks from the vector store and re-embeds them
using Gemini text-embedding-004 for improved retrieval quality.

Usage:
    python scripts/reindex_with_gemini.py
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog  # noqa: E402

from backend.rag import get_vector_store  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()


def reindex_with_gemini() -> bool:
    """Re-index all documents with Gemini embeddings."""
    logger.info("Starting re-indexing with Gemini embeddings...")

    # Get vector store instance
    store = get_vector_store()

    # Check if it's ChromaDB with Gemini embeddings
    if not hasattr(store, "use_gemini_embeddings") or not store.use_gemini_embeddings:
        logger.error("Vector store is not configured to use Gemini embeddings")
        logger.error("Set USE_GEMINI_EMBEDDINGS=true in .env and restart")
        return False

    # Get current collection info
    try:
        count = getattr(store, "collection").count()  # noqa: B009
        logger.info(f"Current document count: {count}")
    except Exception as e:
        logger.error(f"Failed to get collection count: {e}")
        return False

    if count == 0:
        logger.warning("No documents to re-index")
        return True

    # Get all existing documents
    try:
        # In ChromaDB 0.5.x, 'ids' is always returned and invalid in `include` list
        results = getattr(store, "collection").get(  # noqa: B009
        include=["documents", "metadatas"])
        logger.info(f"Retrieved {len(results['ids'])} documents")
    except Exception as e:
        logger.error(f"Failed to retrieve documents: {e}")
        return False

    # Re-embed with Gemini
    logger.info("Re-embedding documents with Gemini text-embedding-004...")

    documents_to_add = []
    for idx, (doc_id, text, metadata) in enumerate(
        zip(results["ids"], results["documents"], results["metadatas"], strict=False)
    ):
        if idx % 10 == 0:
            logger.info(f"Processing {idx}/{len(results['ids'])}...")

        documents_to_add.append({"id": doc_id, "text": text, "metadata": metadata})

    # No need to manually delete and recreate. store.add_documents now does upsert!
    # Because IDs match, they will be updated in-place with new embeddings.

    # Add documents with Gemini embeddings using the batched UPSERT behavior
    try:
        logger.info(
            f"Upserting {len(documents_to_add)} documents with Gemini embeddings..."
        )
        store.add_documents(documents_to_add)
        logger.info("Re-indexing completed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        return False


if __name__ == "__main__":
    success = reindex_with_gemini()
    sys.exit(0 if success else 1)
