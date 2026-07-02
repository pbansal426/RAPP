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

def test_chroma_vector_store_basic():
    """Test ChromaVectorStore if chromadb is installed."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb is not installed")

    # If chromadb is installed, we can test ChromaVectorStore with EphemeralClient
    store = ChromaVectorStore(persistent_path=None, collection_name="test_collection")
    store.add_documents(TEST_DOCUMENTS)
    
    # Check that retrieve works with the ChromaVectorStore
    import backend.rag
    backend.rag._vector_store_instance = store
    try:
        results = retrieve(
            query="alternator replacement",
            vin_meta={"make": "Ford"},
            k=1
        )
        assert len(results) == 1
        assert results[0]["id"] == "doc3"
    finally:
        backend.rag._vector_store_instance = None

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


def test_empty_database():
    """Verify querying an empty database is handled gracefully by both stores."""
    # Test Mock store
    mock_store = MockVectorStore()
    results = mock_store.search("test query", filter_metadata={"make": "HONDA"})
    assert results == []

    # Test ChromaVectorStore
    try:
        import chromadb
    except ImportError:
        return  # skip if chromadb not installed

    import tempfile
    import shutil
    tmpdir = tempfile.mkdtemp()
    try:
        chroma_store = ChromaVectorStore(persistent_path=tmpdir, collection_name="empty_test")
        results = chroma_store.search("test query", filter_metadata={"make": "HONDA"})
        assert results == []
    finally:
        shutil.rmtree(tmpdir)


def test_full_vin_metadata_filtering():
    """Verify filtering works on all required fields: year, engine, drive_type."""
    mock_store = MockVectorStore()
    docs = [
        {
            "id": "doc1",
            "text": "Honda Civic manual for 1.5L turbo engine with FWD.",
            "metadata": {
                "make": "Honda",
                "model": "Civic",
                "year": 2021,
                "engine": "1.5T",
                "drive_type": "FWD"
            }
        },
        {
            "id": "doc2",
            "text": "Honda Civic manual for 2.0L engine with AWD.",
            "metadata": {
                "make": "Honda",
                "model": "Civic",
                "year": 2022,
                "engine": "2.0L",
                "drive_type": "AWD"
            }
        }
    ]
    mock_store.add_documents(docs)
    
    import backend.rag
    backend.rag._vector_store_instance = mock_store
    try:
        results = retrieve(
            query="manual",
            vin_meta={
                "make": "Honda",
                "model": "Civic",
                "year": 2021,
                "engine": "1.5T",
                "drive_type": "FWD"
            }
        )
        assert len(results) == 1
        assert results[0]["id"] == "doc1"
        
        results = retrieve(
            query="manual",
            vin_meta={
                "make": "Honda",
                "model": "Civic",
                "year": 2022,
                "engine": "1.5T",
                "drive_type": "FWD"
            }
        )
        assert len(results) == 0
    finally:
        backend.rag._vector_store_instance = None


def test_case_normalization():
    """Verify metadata case normalization during ingestion and query."""
    mock_store = MockVectorStore()
    docs = [
        {
            "id": "doc1",
            "text": "Honda Civic FWD",
            "metadata": {
                "make": "hOnDa",
                "model": "ciViC",
                "engine": "1.5t",
                "drive_type": "fwd"
            }
        }
    ]
    mock_store.add_documents(docs)
    assert mock_store.documents[0]["metadata"]["make"] == "HONDA"
    assert mock_store.documents[0]["metadata"]["model"] == "CIVIC"
    assert mock_store.documents[0]["metadata"]["engine"] == "1.5T"
    assert mock_store.documents[0]["metadata"]["drive_type"] == "FWD"
    
    import backend.rag
    backend.rag._vector_store_instance = mock_store
    try:
        results = retrieve(
            query="Civic",
            vin_meta={
                "make": "Honda",
                "model": "civic",
                "engine": "1.5T",
                "drive_type": "fwd"
            }
        )
        assert len(results) == 1
        assert results[0]["id"] == "doc1"
    finally:
        backend.rag._vector_store_instance = None


def test_list_type_metadata_filtering():
    """Verify list-type metadata serialization and query matching."""
    mock_store = MockVectorStore()
    docs = [
        {
            "id": "doc1",
            "text": "Universal brake repair manual.",
            "metadata": {
                "make": ["Honda", "Ford"],
                "model": "Accord"
            }
        }
    ]
    mock_store.add_documents(docs)
    assert mock_store.documents[0]["metadata"]["make"] == "HONDA,FORD"
    
    import backend.rag
    backend.rag._vector_store_instance = mock_store
    try:
        results = retrieve(
            query="brake",
            vin_meta={
                "make": ["Honda", "Ford"],
                "model": "Accord"
            }
        )
        assert len(results) == 1
        assert results[0]["id"] == "doc1"
    finally:
        backend.rag._vector_store_instance = None

    # Test Chroma if installed
    try:
        import chromadb
    except ImportError:
        return

    import tempfile
    import shutil
    tmpdir = tempfile.mkdtemp()
    try:
        chroma_store = ChromaVectorStore(persistent_path=tmpdir, collection_name="list_test")
        chroma_store.add_documents(docs)
        results = chroma_store.search("brake", filter_metadata={"make": ["Honda", "Ford"], "model": "Accord"})
        assert len(results) == 1
        assert results[0]["id"] == "doc1"
    finally:
        shutil.rmtree(tmpdir)


def test_mock_punctuation_handling():
    """Verify mock store search strips punctuation from query and document words."""
    mock_store = MockVectorStore()
    docs = [
        {
            "id": "doc1",
            "text": "Change the engine oil. Make sure the filter, gasket, and plug are clean!",
            "metadata": {"make": "HONDA"}
        }
    ]
    mock_store.add_documents(docs)
    results = mock_store.search("oil. clean? gasket,", k=1)
    assert len(results) == 1
    assert results[0]["id"] == "doc1"


def test_singleton_thread_safety():
    """Verify double-checked locking handles concurrent initialization safely."""
    import threading
    import backend.rag
    from backend.rag import get_vector_store
    
    orig_instance = backend.rag._vector_store_instance
    orig_store = os.environ.get("VECTOR_STORE")
    
    os.environ["VECTOR_STORE"] = "mock"
    backend.rag._vector_store_instance = None
    
    instances = []
    def worker():
        instances.append(get_vector_store())
        
    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    if orig_store is not None:
        os.environ["VECTOR_STORE"] = orig_store
    else:
        os.environ.pop("VECTOR_STORE", None)
    backend.rag._vector_store_instance = orig_instance
    
    assert len(instances) == 20
    first_instance = instances[0]
    for inst in instances:
        assert inst is first_instance

