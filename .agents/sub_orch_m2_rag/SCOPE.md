# Scope: Milestone 2 - RAG Vector Store & Retriever

## Objective
Implement a modular abstract vector store interface and a concrete ChromaDB backend switchable via environment variables. Create a retriever module that exposes `retrieve(query, vin_meta, k=5)`.

## Requirements
1. **Abstract Vector Store Interface**: Define an abstract base class `VectorStore` with search methods.
2. **ChromaDB Concrete Implementation**: Implement `ChromaVectorStore(VectorStore)` using the `chromadb` library.
3. **Switchable Vector Store Backend**: Load backend dynamically based on `VECTOR_STORE` env variable (e.g. `VECTOR_STORE=chromadb`).
4. **Retriever Module**: Expose a helper function `retrieve(query, vin_meta, k=5)` from `backend/rag/retriever.py`.
5. **No External Imports**: Absolutely no imports of `chromadb` may exist outside of the `backend/rag/` directory.

## Expected Deliverables
- `backend/rag/__init__.py`
- `backend/rag/vector_store.py` (abstract base class and ChromaDB implementation)
- `backend/rag/retriever.py` (exposing `retrieve()`)
- Unit tests verifying the vector store and retriever mock/live backend.

## Integrity Warnings
- DO NOT CHEAT. All implementations must be genuine. Do not hardcode retrieval mock data.
- The Forensic Auditor will inspect all imports. No `chromadb` imports may exist outside the `backend/rag/` directory.
