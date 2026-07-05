import pytest
import os
from etl.load.manifest import IngestManifest
from etl.load.vector_loader import chunks_to_documents, load_into_vector_store
from etl.models import VehicleKey, TsbRecord, TsbDocument, TextChunk, TableChunk
import tempfile

def test_manifest():
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = os.path.join(tmpdir, "manifest.json")
        manifest = IngestManifest(manifest_path)

        assert manifest.get_status("123", "doc.pdf") is None
        assert not manifest.is_ingested("123", "doc.pdf")

        manifest.mark_status("123", "doc.pdf", "ingested", chunks_count=5)

        assert manifest.get_status("123", "doc.pdf") == "ingested"
        assert manifest.is_ingested("123", "doc.pdf")

        # Test reload
        manifest2 = IngestManifest(manifest_path)
        assert manifest2.get_status("123", "doc.pdf") == "ingested"


def test_chunks_to_documents():
    vehicle = VehicleKey(year=2010, make="Toyota", model="Corolla")
    record = TsbRecord(
        nhtsa_id=10034234,
        communication_number="T-SB-001",
        communication_date="2010-01-01",
        components=("Engine", "Cooling"),
        summary="Test",
        document_count=1
    )
    document = TsbDocument(
        file_name="doc.pdf",
        url="http://example.com/doc.pdf",
        mime_type="application/pdf",
        doc_summary="Test doc"
    )

    text_chunks = [
        TextChunk(
            content="This is a test chunk",
            metadata={},
            provenance={"chunk_index": 0}
        )
    ]
    table_chunks = [
        TableChunk(
            table={"headers": ["Part", "Torque"], "rows": [["Bolt", "10 Nm"], ["Nut", "15 Nm"]], "page": 2},
            metadata={},
            provenance={"chunk_index": 0}
        )
    ]

    docs = chunks_to_documents(text_chunks, table_chunks, record, document, vehicle)
    assert len(docs) == 2

    # Text doc
    assert docs[0]["id"] == "tsb_10034234_text_0"
    assert docs[0]["text"] == "This is a test chunk"
    assert docs[0]["metadata"]["type"] == "text"
    assert docs[0]["metadata"]["make"] == "TOYOTA"
    assert docs[0]["metadata"]["nhtsa_id"] == 10034234
    assert docs[0]["metadata"]["component_category"] == "Engine,Cooling"

    # Table doc
    assert docs[1]["id"] == "tsb_10034234_table_0"
    assert "Table from T-SB-001, page 2" in docs[1]["text"]
    assert "| Part | Torque |" in docs[1]["text"]
    assert "| --- | --- |" in docs[1]["text"]
    assert "| Bolt | 10 Nm |" in docs[1]["text"]
    assert docs[1]["metadata"]["type"] == "table"


def test_load_into_vector_store():
    docs = [{"id": "test_id", "text": "test", "metadata": {"year": 2010}}]
    os.environ["VECTOR_STORE"] = "mock"
    load_into_vector_store(docs)
