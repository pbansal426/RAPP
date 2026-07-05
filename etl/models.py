"""Typed records passed between ETL stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VehicleKey:
    """The year/make/model identity every ingested payload is tagged with."""

    year: int
    make: str
    model: str

    def metadata_tag(self, chunk_type: str, **extra_metadata: Any) -> dict[str, Any]:
        """The enhanced metadata tag attached to every RAG payload.

        Key order and shape are load-bearing for the retrieval layer:
        ``{"year": 2010, "make": "Toyota", "model": "Corolla", "type": ...}``.

        Additional metadata fields for enhanced filtering:
        - component_category, component_name, component_location
        - procedure_type, difficulty_level, estimated_time_minutes
        - symptom_category, obd_codes, diagnostic_confidence
        - source_type, source_authority, quality_score
        """
        base_metadata = {
            "year": self.year,
            "make": self.make.upper(),
            "model": self.model.upper(),
            "type": chunk_type,
        }
        base_metadata.update(extra_metadata)
        return base_metadata

    def __str__(self) -> str:
        return f"{self.year} {self.make} {self.model}"


@dataclass(frozen=True)
class TsbRecord:
    """One NHTSA manufacturer communication (TSB) as listed for a vehicle."""

    nhtsa_id: int
    communication_number: str | None
    summary: str | None
    communication_date: str | None
    components: tuple[str, ...]
    document_count: int


@dataclass(frozen=True)
class TsbDocument:
    """A downloadable artifact attached to a :class:`TsbRecord`."""

    file_name: str
    url: str
    mime_type: str
    doc_summary: str | None

    @property
    def is_pdf(self) -> bool:
        return self.mime_type == "application/pdf" or self.url.lower().endswith(".pdf")


@dataclass(frozen=True)
class ParsedPdf:
    """Layout-separated content of one PDF: prose with tables cut out."""

    prose: str
    tables: list[dict[str, Any]]
    page_count: int


@dataclass(frozen=True)
class TextChunk:
    """One retrieval unit of instructional prose."""

    content: str
    metadata: dict[str, Any]  # strict RAG tag — see VehicleKey.metadata_tag
    provenance: dict[str, Any]  # source URL, chunk index, token estimate


@dataclass(frozen=True)
class TableChunk:
    """One structured table, retrievable programmatically (e.g. torque specs)."""

    table: dict[str, Any]  # {"page", "headers", "n_rows", "n_columns", "rows"}
    metadata: dict[str, Any]
    provenance: dict[str, Any]
