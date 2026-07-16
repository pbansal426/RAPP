"""Orchestration of one extract → transform → (mock) load run."""

from __future__ import annotations

import contextlib
import errno
import fcntl
import json
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
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


# Conservative blocklist: these phrase patterns only ever appear on pure
# dealer-process/tooling bulletins (verified against real NHTSA samples
# during the 2026-07-16 on-site batch), never on genuine repair/failure
# TSBs. Deliberately narrow -- a false-positive skip here silently loses
# real repair content, which is worse than a little ingestion noise.
#
# NOTE: a bare "gds2" pattern was in the original plan but REMOVED after the
# dry-run review -- it caught genuine repair bulletins that merely reference
# the GDS2 diagnostic tool (e.g. NHTSA 10190387, "recover the TCM before
# declaring it a bad part and replacing"). Every truly-administrative record
# also contains "session log" or "technical assistance case", so dropping
# "gds2" loses no real admin coverage while eliminating those false positives.
_ADMINISTRATIVE_SUMMARY_PATTERNS = (
    "session log",
    "cx connect",
    "technical assistance case",
    "how to email",
)


def _is_administrative_record(record: TsbRecord) -> bool:
    # record.summary is Optional[str]; guard against None or it AttributeErrors.
    summary_lower = (record.summary or "").lower()
    return any(pattern in summary_lower for pattern in _ADMINISTRATIVE_SUMMARY_PATTERNS)


class PipelineError(RuntimeError):
    """A stage failed in a way the pipeline cannot recover from."""


class PipelineLockedError(PipelineError):
    """Another etl process already holds the workspace lock."""


@contextlib.contextmanager
def _workspace_lock(workspace_dir: Path) -> Iterator[None]:
    """Advisory lock so two `--load` runs never write the same ChromaDB
    persistent store concurrently. POSIX-only (flock), matching the project's
    macOS/Linux-only dev and CI targets."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    lock_path = workspace_dir / ".etl.lock"
    lock_file = open(lock_path, "w")
    try:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                raise PipelineLockedError(
                    f"Another etl ingest is already running against {workspace_dir} "
                    f"(lock held on {lock_path}). Wait for it to finish or use a "
                    f"different --workspace."
                ) from exc
            raise
        yield
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()


def _write_progress(workspace_dir: Path, payload: dict[str, object]) -> None:
    """Best-effort live progress snapshot for `watch`-ing from outside the
    process -- never let a progress-file write failure abort ingestion."""
    try:
        workspace_dir.mkdir(parents=True, exist_ok=True)
        progress_path = workspace_dir / "progress.json"
        tmp_path = progress_path.with_suffix(".json.tmp")
        payload = {**payload, "updated_at": datetime.now(UTC).isoformat()}
        tmp_path.write_text(json.dumps(payload, indent=2))
        tmp_path.replace(progress_path)  # atomic on POSIX -- no partial reads
    except OSError as exc:
        log.warning("failed to write progress snapshot: %s", exc)


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
    """Ingest all PDFs for a vehicle, using the manifest to resume.

    Manifest entries are scoped per-vehicle (VehicleKey.slug): the same NHTSA
    bulletin is frequently shared across models, and a global key would only
    ever tag it with whichever vehicle's run happened to process it first.
    """
    summary = IngestSummary(vehicle=vehicle)
    workspace = config.workspace_dir / vehicle.slug

    splitter = RecursiveCharacterSplitter(
        chunk_size_chars=config.chunking.chunk_size_chars,
        overlap_chars=config.chunking.overlap_chars,
    )

    def progress(current_file: str | None, status: str = "running") -> None:
        _write_progress(
            config.workspace_dir,
            {
                "vehicle": str(vehicle),
                "status": status,
                "records_found": summary.records_found,
                "pdfs_ingested": summary.pdfs_ingested,
                "pdfs_skipped_no_text": summary.pdfs_skipped_no_text,
                "pdfs_failed": summary.pdfs_failed,
                "chunks_loaded": summary.chunks_loaded,
                "current_file": current_file,
            },
        )

    with _workspace_lock(workspace):
        progress(None, status="starting")

        with NhtsaManufacturerCommunicationsClient(config) as client:
            records = client.list_communications(vehicle)
            summary.records_found = len(records)
            progress(None)

            for record in records:
                if _is_administrative_record(record):
                    log.info(
                        f"Skipping administrative bulletin (NHTSA ID {record.nhtsa_id}): "
                        f"{(record.summary or '')[:80]}"
                    )
                    continue
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
                    progress(document.file_name)

                    if manifest.is_ingested(
                        vehicle.slug, nhtsa_id_str, document.file_name
                    ):
                        log.info(
                            f"Skipping already ingested PDF: {document.file_name} (NHTSA ID {nhtsa_id_str})"
                        )
                        summary.pdfs_ingested += 1
                        # Note: we don't know chunks_loaded for previously ingested items easily, skip adding it
                        continue

                    if (
                        manifest.get_status(
                            vehicle.slug, nhtsa_id_str, document.file_name
                        )
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
                                vehicle.slug,
                                nhtsa_id_str,
                                document.file_name,
                                "skipped_no_text",
                            )
                            summary.pdfs_skipped_no_text += 1
                            progress(document.file_name)
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
                            for index, content in enumerate(
                                splitter.split(parsed.prose)
                            )
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
                            vehicle.slug,
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
                        progress(document.file_name)

                    except Exception as exc:
                        log.error(
                            f"Failed to process {document.file_name} (NHTSA ID {nhtsa_id_str}): {exc}"
                        )
                        manifest.mark_status(
                            vehicle.slug, nhtsa_id_str, document.file_name, "failed"
                        )
                        summary.pdfs_failed += 1
                        progress(document.file_name)

        progress(None, status="done")

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
    workspace = config.workspace_dir / vehicle.slug
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
