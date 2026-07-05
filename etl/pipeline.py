"""Orchestration of one extract → transform → (mock) load run."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from etl.clients.nhtsa_communications import (
    NhtsaApiError,
    NhtsaManufacturerCommunicationsClient,
)
from etl.config import EtlConfig
from etl.models import (
    ParsedPdf,
    TableChunk,
    TextChunk,
    TsbDocument,
    TsbRecord,
    VehicleKey,
)
from etl.transform.chunking import RecursiveCharacterSplitter, estimate_tokens
from etl.transform.pdf_layout import LayoutAwarePdfParser

log = logging.getLogger(__name__)


class PipelineError(RuntimeError):
    """A stage failed in a way the pipeline cannot recover from."""


@dataclass(frozen=True)
class VerticalSliceResult:
    vehicle: VehicleKey
    record: TsbRecord
    document: TsbDocument
    pdf_path: Path
    parsed: ParsedPdf
    text_chunks: list[TextChunk]
    table_chunks: list[TableChunk]


def run_vertical_slice(vehicle: VehicleKey, config: EtlConfig) -> VerticalSliceResult:
    # Extract: list TSBs, take the first record whose PDF actually downloads.
    with NhtsaManufacturerCommunicationsClient(config) as client:
        records = client.list_communications(vehicle)
        if not records:
            raise PipelineError(
                f"NHTSA returned no manufacturer communications for {vehicle}"
            )
        record, document, pdf_path = _fetch_first_pdf(client, records, vehicle, config)

    # Transform: layout-aware parse, then chunk the prose.
    parsed = LayoutAwarePdfParser().parse(pdf_path)
    splitter = RecursiveCharacterSplitter(
        chunk_size_chars=config.chunking.chunk_size_chars,
        overlap_chars=config.chunking.overlap_chars,
    )
    text_chunks = [
        TextChunk(
            content=content,
            metadata=vehicle.metadata_tag("text"),
            provenance={
                "source_url": document.url,
                "nhtsa_id": record.nhtsa_id,
                "chunk_index": index,
                "estimated_tokens": estimate_tokens(
                    content, config.chunking.chars_per_token
                ),
            },
        )
        for index, content in enumerate(splitter.split(parsed.prose))
    ]
    table_chunks = [
        TableChunk(
            table=table,
            metadata=vehicle.metadata_tag("table"),
            provenance={
                "source_url": document.url,
                "nhtsa_id": record.nhtsa_id,
                "page": table["page"],
            },
        )
        for table in parsed.tables
    ]
    return VerticalSliceResult(
        vehicle=vehicle,
        record=record,
        document=document,
        pdf_path=pdf_path,
        parsed=parsed,
        text_chunks=text_chunks,
        table_chunks=table_chunks,
    )


def _fetch_first_pdf(
    client: NhtsaManufacturerCommunicationsClient,
    records: list[TsbRecord],
    vehicle: VehicleKey,
    config: EtlConfig,
) -> tuple[TsbRecord, TsbDocument, Path]:
    """First record (in API order) with a PDF that actually downloads.

    Records with no attached PDF or a dead link are skipped with a log line —
    upstream data quality is not this pipeline's failure.
    """
    workspace = (
        config.workspace_dir
        / f"{vehicle.year}_{vehicle.make}_{vehicle.model}".lower().replace(" ", "_")
    )
    for record in records[: config.max_record_scan]:
        documents = client.resolve_documents(record)
        pdf = next((doc for doc in documents if doc.is_pdf), None)
        if pdf is None:
            log.info(
                "skipping NHTSA id %s (%d documents, none PDF)",
                record.nhtsa_id,
                len(documents),
            )
            continue
        try:
            return record, pdf, client.download(pdf, workspace)
        except NhtsaApiError as exc:
            log.warning("skipping NHTSA id %s: %s", record.nhtsa_id, exc)
    raise PipelineError(
        f"no downloadable PDF among the first "
        f"{min(len(records), config.max_record_scan)} records for {vehicle}"
    )
