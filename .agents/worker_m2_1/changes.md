# Changes Made for Milestone 2: RAG Vector Store & Retriever

This document records the implementations, files created, and design decisions made for Milestone 2.

## Summary of Changes

### 1. RAG Vector Store Directory
- **Action**: Created directory `backend/rag/` to house the vector database abstraction and implementations.

### 2. Vector Store Interface and Implementations (`backend/rag/vector_store.py`)
- **Action**: Created this file from scratch, defining:
  - **`VectorStore`**: An abstract base class defining `add_documents(documents)` and `search(query, filter_metadata, k)`.
  - **`ChromaVectorStore`**: A concrete subclass that encapsulates `chromadb`. It dynamically initializes a `PersistentClient` or `EphemeralClient` based on input parameters. Serializes non-flat metadata to prevent runtime errors in ChromaDB. Confines imports of `chromadb` to `__init__` so other components are not blocked if the library is not installed.
  - **`MockVectorStore`**: A concrete subclass that stores documents in-memory. Performs manual filtering by metadata and calculates text matching based on word-overlap similarity to return distance scores. This provides a lightweight, dependency-free backend for test environments.

### 3. Retriever Implementation (`backend/rag/retriever.py`)
- **Action**: Created this file from scratch, defining:
  - **`retrieve(query, vin_meta, k=5)`**: Extends the retrieval query. It queries the active vector store singleton. It extracts and normalizes the `make` and `model` parameters from the `vin_meta` dict (converting to uppercase to align with database storage conventions) and applies them as metadata search filters.

### 4. Package Initialization and Factory (`backend/rag/__init__.py`)
- **Action**: Created this file from scratch, defining:
  - **`get_vector_store()`**: A factory function that initializes and returns a singleton instance of the configured vector store. The backend type is dynamically selected via the `VECTOR_STORE` environment variable (`chromadb` or `mock`).
  - **Delayed Import**: Imports `retrieve` at the end of the module to prevent circular dependency issues when files reference each other during imports.

### 5. Backend Requirements (`backend/requirements.txt`)
- **Action**: Created this file from scratch to specify project dependencies:
  - `fastapi`
  - `uvicorn`
  - `chromadb>=0.4.0`
  - `pytest`

### 6. Test Suite (`tests/unit/test_rag.py`)
- **Action**: Created this file from scratch, containing:
  - **`setup_mock_store` fixture**: Configures `VECTOR_STORE=mock`, resets the singleton instance, and populates the store with test data.
  - **`test_mock_metadata_filtering`**: Asserts that retriever correctly filters by metadata (e.g., make and model) and returns the correct document.
  - **`test_mock_word_similarity`**: Asserts that query text matches documents based on term overlap.
  - **`test_chroma_vector_store_basic`**: Conditionally runs a basic search test on `ChromaVectorStore` using `chromadb.EphemeralClient` if the `chromadb` package is installed; skips cleanly if missing.
  - **`test_import_hygiene`**: Programmatically iterates over all Python files under `backend/` (excluding `backend/rag/`) and asserts that no references to `import chromadb` or `from chromadb` exist.

---

## Verification Results

### 1. Import Hygiene Search
A manual `grep_search` confirmed that `chromadb` is only referenced within `backend/rag/` and the tests file:
- `backend/rag/__init__.py`
- `backend/rag/vector_store.py`
- `tests/unit/test_rag.py`

There are no other imports of `chromadb` in the project.

### 2. Unit Tests execution
The command `PYTHONPATH=. python3 -m pytest tests/unit/test_rag.py` was initiated. Due to the host environment requiring interactive permission prompts for executing shell commands, the command execution timed out. However, the test files are fully written, clean, and ready to be run locally.
