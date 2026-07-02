# Analysis Report: Milestone 2 — RAG Vector Store & Retriever

## 1. Introduction and Scope
The goal of Milestone 2 is to design and recommend a modular, abstract vector store interface and a concrete ChromaDB implementation that can be dynamically switched via environment variables. The design must expose a retriever function `retrieve(query, vin_meta, k=5)` from `backend/rag/retriever.py` to fetch vehicle-specific OEM-like repair instructions.

To prevent architectural leaking, the `chromadb` library must only be imported within the `backend/rag/` module.

---

## 2. Current Workspace State
- **Workspace Directory**: `/Users/prathambansal/Dev/RAPP`
- **Files Present Outside `.agents/`**:
  - `PHASE_1_SPEC.md`
- **Verification of Python Environment**:
  - A `.venv` or `venv` virtual environment does not exist inside the workspace directory.
  - Python terminal command execution timed out during permission prompt checks, indicating that commands require interactive user approval.
  - There is currently no `requirements.txt` file in either the root directory or the planned `backend/` directory.
  - There is no source code written yet (directories like `backend/` are currently not created in the workspace).

---

## 3. Recommended Code Layout
The suggested structure for the backend RAG module is:
```
backend/
├── requirements.txt
└── rag/
    ├── __init__.py
    ├── vector_store.py
    └── retriever.py
```

---

## 4. Class and Interface Designs

### A. `backend/rag/vector_store.py`
This module defines:
1. `VectorStore` (Abstract Base Class): Defines the common interface.
2. `ChromaVectorStore` (Concrete Class): Integrates with ChromaDB, encapsulating client initialization, collection management, document mapping, and metadata filters.
3. `MockVectorStore` (Concrete Class): A dependency-free in-memory implementation for unit testing and offline development.

#### Proposed Content of `backend/rag/vector_store.py`:
```python
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class VectorStore(ABC):
    """
    Abstract Base Class defining the interface for RAG vector stores.
    """

    @abstractmethod
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add a list of documents to the vector store.

        Parameters:
        -----------
        documents : List[Dict[str, Any]]
            A list of document dictionaries, where each document has the format:
            {
                "id": str,
                "text": str,
                "metadata": Dict[str, Any]
            }
        """
        pass

    @abstractmethod
    def search(
        self, 
        query: str, 
        filter_metadata: Optional[Dict[str, Any]] = None, 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for the top k documents matching the query, optionally filtered by metadata.

        Parameters:
        -----------
        query : str
            The search query.
        filter_metadata : Optional[Dict[str, Any]]
            A dictionary containing key-value metadata pairs to filter by.
        k : int
            The number of results to return.

        Returns:
        --------
        List[Dict[str, Any]]
            A list of matching documents, each structured as:
            {
                "id": str,
                "text": str,
                "metadata": Dict[str, Any],
                "distance": float
            }
        """
        pass


class ChromaVectorStore(VectorStore):
    """
    ChromaDB implementation of the VectorStore interface.
    Encapsulates all chromadb imports and client logic.
    """

    def __init__(
        self, 
        persistent_path: Optional[str] = None, 
        collection_name: str = "repair_manuals"
    ):
        """
        Initialize the ChromaVectorStore client.
        
        Parameters:
        -----------
        persistent_path : Optional[str]
            Path to persistent directory. If None, runs an ephemeral client.
        collection_name : str
            Name of the collection to use.
        """
        import chromadb  # Confined import

        self.collection_name = collection_name
        if persistent_path:
            os.makedirs(persistent_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=persistent_path)
        else:
            self.client = chromadb.EphemeralClient()
            
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Adds flat documents and handles ChromaDB metadata serialization limits.
        """
        if not documents:
            return

        ids = []
        texts = []
        metadatas = []

        for doc in documents:
            ids.append(doc["id"])
            texts.append(doc["text"])
            
            # ChromaDB metadata must have flat types (str, int, float, bool)
            flat_metadata = {}
            for k, v in doc.get("metadata", {}).items():
                if isinstance(v, (str, int, float, bool)):
                    flat_metadata[k] = v
                elif isinstance(v, list):
                    flat_metadata[k] = ",".join(map(str, v))
                elif v is None:
                    continue
                else:
                    flat_metadata[k] = str(v)
            metadatas.append(flat_metadata)

        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )

    def search(
        self, 
        query: str, 
        filter_metadata: Optional[Dict[str, Any]] = None, 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Queries ChromaDB collection, constructing filters dynamically.
        """
        where_clause = None
        if filter_metadata:
            filter_conditions = []
            for key, value in filter_metadata.items():
                if value is not None:
                    if isinstance(value, (str, int, float, bool)):
                        filter_conditions.append({key: {"$eq": value}})
                    else:
                        filter_conditions.append({key: {"$eq": str(value)}})
            
            if len(filter_conditions) == 1:
                where_clause = filter_conditions[0]
            elif len(filter_conditions) > 1:
                where_clause = {"$and": filter_conditions}

        results = self.collection.query(
            query_texts=[query],
            n_results=k,
            where=where_clause
        )

        formatted_results = []
        if results and "documents" in results and results["documents"]:
            ids = results.get("ids", [[]])[0]
            docs = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0] if "distances" in results else [0.0] * len(docs)

            for idx in range(len(docs)):
                formatted_results.append({
                    "id": ids[idx],
                    "text": docs[idx],
                    "metadata": metadatas[idx] if metadatas else {},
                    "distance": distances[idx]
                })

        return formatted_results


class MockVectorStore(VectorStore):
    """
    A lightweight, in-memory Mock Vector Store designed for unit tests 
    and offline development without chromadb dependencies.
    """

    def __init__(self):
        self.documents: List[Dict[str, Any]] = []

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        for doc in documents:
            self.documents.append({
                "id": doc["id"],
                "text": doc["text"],
                "metadata": doc.get("metadata", {})
            })

    def search(
        self, 
        query: str, 
        filter_metadata: Optional[Dict[str, Any]] = None, 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        filtered_docs = []

        # 1. Filter by metadata values
        for doc in self.documents:
            match = True
            doc_meta = doc.get("metadata", {})
            if filter_metadata:
                for key, val in filter_metadata.items():
                    if val is not None:
                        doc_val = doc_meta.get(key)
                        if str(doc_val).lower() != str(val).lower():
                            match = False
                            break
            if match:
                filtered_docs.append(doc)

        # 2. Score text matching by word overlap
        query_words = set(query.lower().split())
        scored_docs = []
        for doc in filtered_docs:
            doc_words = set(doc["text"].lower().split())
            overlap = len(query_words.intersection(doc_words))
            # Distance mapping: higher overlap = lower distance
            distance = 1.0 / (1.0 + overlap)
            scored_docs.append((distance, doc))

        scored_docs.sort(key=lambda x: x[0])
        
        results = []
        for dist, doc in scored_docs[:k]:
            results.append({
                "id": doc["id"],
                "text": doc["text"],
                "metadata": doc["metadata"],
                "distance": dist
            })
        return results
```

---

### B. `backend/rag/retriever.py`
This module acts as the search entry point, translating vehicle parameters into vector database query arguments.

#### Proposed Content of `backend/rag/retriever.py`:
```python
from typing import Dict, Any, List

def retrieve(query: str, vin_meta: Dict[str, Any], k: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieves vehicle-specific repair instruction snippets.

    Parameters:
    -----------
    query : str
        The user symptom or diagnostic search query.
    vin_meta : Dict[str, Any]
        Vehicle metadata parsed from VIN. Example keys: 'make', 'model'.
    k : int
        Number of items to retrieve.

    Returns:
    --------
    List[Dict[str, Any]]
        List of relevant manual paragraphs and their citations.
    """
    from backend.rag import get_vector_store  # Local import prevents circular deps

    store = get_vector_store()

    # Normalize metadata keys for the search filter
    filter_metadata = {}
    if vin_meta:
        if "make" in vin_meta and vin_meta["make"]:
            filter_metadata["make"] = str(vin_meta["make"]).upper()
        if "model" in vin_meta and vin_meta["model"]:
            filter_metadata["model"] = str(vin_meta["model"]).upper()

    return store.search(query=query, filter_metadata=filter_metadata, k=k)
```

---

### C. `backend/rag/__init__.py`
This is the package entry point. It exports the factory method to dynamically get the configured database instance using the environment variables and exposes `retrieve()`.

#### Proposed Content of `backend/rag/__init__.py`:
```python
import os
from typing import Optional
from backend.rag.vector_store import VectorStore, ChromaVectorStore, MockVectorStore

_vector_store_instance: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    """
    Factory function producing a singleton instance of the configured vector store backend.
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        store_type = os.getenv("VECTOR_STORE", "chromadb").lower()
        if store_type == "chromadb":
            persistent_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
            _vector_store_instance = ChromaVectorStore(persistent_path=persistent_path)
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
```

---

## 5. Testing & Verification Plan

To verify that the vector database functions correctly under the expected contract, write unit tests checking:
1. Retrieval on the mock backend matching metadata attributes.
2. Retrieval on the ChromaDB backend (conditional on installation).
3. Verification that no `chromadb` imports bleed outside of `backend/rag/`.

### Recommended Unit Test Layout (`tests/unit/test_rag.py`)
```python
import os
import pytest
from backend.rag import get_vector_store, retrieve
from backend.rag.vector_store import MockVectorStore, ChromaVectorStore

# Define test dataset
TEST_DOCUMENTS = [
    {
        "id": "doc1",
        "text": "Change engine oil for Honda Civic. Use 0W-20 oil filter.",
        "metadata": {"make": "HONDA", "model": "CIVIC", "year": 2018}
    },
    {
        "id": "doc2",
        "text": "Brake pad replacement instructions for Honda Accord.",
        "metadata": {"make": "HONDA", "model": "ACCORD", "year": 2020}
    },
    {
        "id": "doc3",
        "text": "Ford F-150 alternator replacement sequence.",
        "metadata": {"make": "FORD", "model": "F-150", "year": 2019}
    }
]

@pytest.fixture
def setup_mock_store(monkeypatch):
    """Configures environment to use the mock vector store."""
    monkeypatch.setenv("VECTOR_STORE", "mock")
    # Reset singleton
    import backend.rag
    backend.rag._vector_store_instance = None
    store = get_vector_store()
    store.add_documents(TEST_DOCUMENTS)
    yield store
    backend.rag._vector_store_instance = None

def test_mock_metadata_filtering(setup_mock_store):
    """Test that retriever correctly filters documents by vehicle make/model."""
    results = retrieve(
        query="replacement",
        vin_meta={"make": "Honda", "model": "Accord"},
        k=5
    )
    assert len(results) == 1
    assert results[0]["id"] == "doc2"
    assert results[0]["metadata"]["model"] == "ACCORD"

def test_mock_word_similarity(setup_mock_store):
    """Test that text search score returns the correct result based on word match."""
    # Searching within Honda brand
    results = retrieve(
        query="oil filter change",
        vin_meta={"make": "Honda"},
        k=2
    )
    # The first document has oil, filter, and change, so it should rank higher
    assert results[0]["id"] == "doc1"

def test_import_hygiene():
    """Verify that no file outside backend/rag/ imports chromadb."""
    import re
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    bleed_files = []
    
    for file_path in project_root.glob("backend/**/*.py"):
        # Exclude backend/rag/
        if "backend/rag" in str(file_path):
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if re.search(r"\bimport\s+chromadb\b", content) or re.search(r"\bfrom\s+chromadb\b", content):
                bleed_files.append(str(file_path))
                
    assert len(bleed_files) == 0, f"Imports of chromadb found outside of backend/rag: {bleed_files}"
```

---

## 6. Project Integration Steps
1. Create `backend/rag/vector_store.py`, `backend/rag/retriever.py`, and `backend/rag/__init__.py`.
2. Write a minimal testing dependency definition in `backend/requirements.txt`:
   ```
   fastapi
   uvicorn
   chromadb>=0.4.0
   pytest
   ```
3. Set `VECTOR_STORE=mock` in localized unit test environment setups to run without external downloads or network reliance.
