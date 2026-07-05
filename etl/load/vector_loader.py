from typing import Any

from backend.rag import get_vector_store
from etl.models import TableChunk, TextChunk, TsbDocument, TsbRecord, VehicleKey


def chunks_to_documents(
    text_chunks: list[TextChunk],
    table_chunks: list[TableChunk],
    record: TsbRecord,
    document: TsbDocument,
    vehicle: VehicleKey,
) -> list[dict[str, Any]]:
    """Converts ETL chunks into VectorStore-compatible documents."""
    documents = []

    # Enhanced metadata as described in docs/knowledge_base_metadata_schema.md Phase 1
    enhanced_fields = {
        "source_url": document.url,
        "nhtsa_id": record.nhtsa_id,
        "bulletin_number": record.communication_number or "",
        "communication_date": record.communication_date or "",
        "component_category": ",".join(record.components) if record.components else "",
        "source_type": "nhtsa_tsb",
        "source_authority": "official",
        "quality_score": 0.9,
    }

    # Process prose chunks
    for chunk in text_chunks:
        chunk_idx = chunk.provenance.get("chunk_index", 0)

        # Merge vehicle tag with enhanced fields
        metadata = vehicle.metadata_tag(chunk_type="text", **enhanced_fields)

        documents.append(
            {
                "id": f"tsb_{record.nhtsa_id}_text_{chunk_idx}",
                "text": chunk.content,
                "metadata": metadata,
            }
        )

    # Process table chunks
    for table_chunk in table_chunks:
        chunk_idx = table_chunk.provenance.get("chunk_index", 0)
        table_data = table_chunk.table

        # Serialize table to Markdown
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        page = table_data.get("page", "?")

        if not headers and rows:
            # If no headers, infer length from first row
            headers = [f"Col {i+1}" for i in range(len(rows[0]))]

        if headers:
            header_row = "| " + " | ".join(str(h) for h in headers) + " |"
            separator_row = "| " + " | ".join("---" for _ in headers) + " |"

            md_rows = []
            for row in rows:
                md_rows.append(
                    "| "
                    + " | ".join(str(cell) if cell is not None else "" for cell in row)
                    + " |"
                )

            bulletin_disp = record.communication_number or f"NHTSA {record.nhtsa_id}"
            table_md = f"Table from {bulletin_disp}, page {page}:\n\n"
            table_md += "\n".join([header_row, separator_row] + md_rows)
        else:
            # Fallback if the table structure is completely unrecognizable
            table_md = f"Empty table from {record.communication_number}, page {page}"

        # Merge vehicle tag with enhanced fields
        metadata = vehicle.metadata_tag(chunk_type="table", **enhanced_fields)

        documents.append(
            {
                "id": f"tsb_{record.nhtsa_id}_table_{chunk_idx}",
                "text": table_md,
                "metadata": metadata,
            }
        )

    return documents


def load_into_vector_store(documents: list[dict[str, Any]]) -> None:
    """Loads documents into the vector store."""
    if documents:
        store = get_vector_store()
        store.add_documents(documents)
