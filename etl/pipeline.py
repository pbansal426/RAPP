"""Orchestration of one extract → transform → (mock) load run."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from etl.clients.nhtsa_communications import (
    NhtsaApiError,
    NhtsaManufacturerCommunicationsClient,
)
from etl.config import EtlConfig
from etl.load.manifest import IngestManifest
from etl.load.vector_loader import chunks_to_documents, load_into_vector_store
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


@dataclass
class IngestSummary:
    vehicle: VehicleKey
    records_found: int = 0
    pdfs_ingested: int = 0
    pdfs_skipped_no_text: int = 0
    pdfs_failed: int = 0
    chunks_loaded: int = 0


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
                "chunk_index": index,
            },
        )
        for index, table in enumerate(parsed.tables)
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


def run_full_ingest(
    vehicle: VehicleKey, config: EtlConfig, manifest: IngestManifest, load: bool = True
) -> IngestSummary:
    """Ingest all PDFs for a vehicle, using the manifest to resume."""
    summary = IngestSummary(vehicle=vehicle)

    workspace = (
        config.workspace_dir
        / f"{vehicle.year}_{vehicle.make}_{vehicle.model}".lower().replace(" ", "_")
    )

    splitter = RecursiveCharacterSplitter(
        chunk_size_chars=config.chunking.chunk_size_chars,
        overlap_chars=config.chunking.overlap_chars,
    )

    with NhtsaManufacturerCommunicationsClient(config) as client:
        records = client.list_communications(vehicle)
        summary.records_found = len(records)

        for record in records:
            try:
                documents = client.resolve_documents(record)
                time.sleep(0.5)  # Polite pacing for NHTSA API
            except NhtsaApiError as exc:
                log.warning(
                    "failed to resolve documents for NHTSA id %s: %s",
                    record.nhtsa_id,
                    exc,
                )
                continue

            for document in documents:
                if not document.is_pdf:
                    continue

                nhtsa_id_str = str(record.nhtsa_id)
                if manifest.is_ingested(nhtsa_id_str, document.file_name):
                    log.info(
                        f"Skipping already ingested PDF: {document.file_name} (NHTSA ID {nhtsa_id_str})"
                    )
                    summary.pdfs_ingested += 1
                    # Note: we don't know chunks_loaded for previously ingested items easily, skip adding it
                    continue

                if (
                    manifest.get_status(nhtsa_id_str, document.file_name)
                    == "skipped_no_text"
                ):
                    log.info(
                        f"Skipping PDF previously marked no-text: {document.file_name} (NHTSA ID {nhtsa_id_str})"
                    )
                    summary.pdfs_skipped_no_text += 1
                    continue

                try:
                    pdf_path = client.download(document, workspace)
                    time.sleep(0.5)  # Polite pacing for NHTSA API

                    parsed = LayoutAwarePdfParser().parse(pdf_path)

                    if not parsed.prose.strip() and not parsed.tables:
                        log.info(
                            f"PDF {document.file_name} (NHTSA ID {nhtsa_id_str}) contains no text/tables. Marking skipped."
                        )
                        manifest.mark_status(
                            nhtsa_id_str, document.file_name, "skipped_no_text"
                        )
                        summary.pdfs_skipped_no_text += 1
                        continue

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
                                "page": table.get("page", "?"),
                                "chunk_index": index,
                            },
                        )
                        for index, table in enumerate(parsed.tables)
                    ]

                    total_chunks = len(text_chunks) + len(table_chunks)

                    if load:
                        documents_to_load = chunks_to_documents(
                            text_chunks, table_chunks, record, document, vehicle
                        )
                        load_into_vector_store(documents_to_load)

                    manifest.mark_status(
                        nhtsa_id_str,
                        document.file_name,
                        "ingested",
                        chunks_count=total_chunks,
                    )
                    summary.pdfs_ingested += 1
                    summary.chunks_loaded += total_chunks
                    log.info(
                        f"Successfully ingested {document.file_name} (NHTSA ID {nhtsa_id_str}): {total_chunks} chunks."
                    )

                except Exception as exc:
                    log.error(
                        f"Failed to process {document.file_name} (NHTSA ID {nhtsa_id_str}): {exc}"
                    )
                    manifest.mark_status(nhtsa_id_str, document.file_name, "failed")
                    summary.pdfs_failed += 1

    return summary


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
