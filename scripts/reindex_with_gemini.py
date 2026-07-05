"""Re-index existing TSB data with Gemini embeddings.

This script loads existing TSB chunks from the vector store and re-embeds them
using Gemini text-embedding-004 for improved retrieval quality.

Usage:
    python scripts/reindex_with_gemini.py
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rag import get_vector_store
import structlog

logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()


def reindex_with_gemini():
    """Re-index all documents with Gemini embeddings."""
    logger.info("Starting re-indexing with Gemini embeddings...")
    
    # Get vector store instance
    store = get_vector_store()
    
    # Check if it's ChromaDB with Gemini embeddings
    if not hasattr(store, 'use_gemini_embeddings') or not store.use_gemini_embeddings:
        logger.error("Vector store is not configured to use Gemini embeddings")
        logger.error("Set USE_GEMINI_EMBEDDINGS=true in .env and restart")
        return False
    
    # Get current collection info
    try:
        count = store.collection.count()
        logger.info(f"Current document count: {count}")
    except Exception as e:
        logger.error(f"Failed to get collection count: {e}")
        return False
    
    if count == 0:
        logger.warning("No documents to re-index")
        return True
    
    # Get all existing documents
    try:
        results = store.collection.get(include=['documents', 'metadatas', 'ids'])
        logger.info(f"Retrieved {len(results['ids'])} documents")
    except Exception as e:
        logger.error(f"Failed to retrieve documents: {e}")
        return False
    
    # Re-embed with Gemini
    logger.info("Re-embedding documents with Gemini text-embedding-004...")
    
    documents_to_add = []
    for idx, (doc_id, text, metadata) in enumerate(zip(
        results['ids'], 
        results['documents'], 
        results['metadatas']
    )):
        if idx % 10 == 0:
            logger.info(f"Processing {idx}/{len(results['ids'])}...")
        
        documents_to_add.append({
            'id': doc_id,
            'text': text,
            'metadata': metadata
        })
    
    # Delete old collection and create new one
    try:
        logger.info("Deleting old collection...")
        store.client.delete_collection(name=store.collection_name)
        logger.info("Creating new collection...")
        store.collection = store.client.get_or_create_collection(name=store.collection_name)
    except Exception as e:
        logger.error(f"Failed to recreate collection: {e}")
        return False
    
    # Add documents with Gemini embeddings
    try:
        logger.info(f"Adding {len(documents_to_add)} documents with Gemini embeddings...")
        store.add_documents(documents_to_add)
        logger.info("Re-indexing completed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        return False


if __name__ == "__main__":
    success = reindex_with_gemini()
    sys.exit(0 if success else 1)
