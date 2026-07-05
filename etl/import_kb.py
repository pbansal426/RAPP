"""Merge a pulled kb_export/chroma_db snapshot into the live vector store.

The SSD-hosted data/chroma_db (via the data/ symlink) is the real, primary
knowledge base -- GitHub/kb_export/ is only the transit mechanism for
getting Jules's (or anyone else's) ingestion work back onto this machine,
not a second permanent home for it. After `git lfs pull` brings down a
teammate's or Jules's exported snapshot, run this to fold it into the live
store.

Deliberately upserts document-by-document through the same add_documents()
path normal ingestion uses, rather than copying files over the live store
wholesale: chroma.sqlite3 is a single metadata file shared across every
collection, so a raw file copy from an export that doesn't have this
machine's other vehicles would silently delete them. Upserting is safe to
re-run and safe with overlapping content either direction.

    git lfs pull
    uv run python -m etl.import_kb
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Deliberate, narrow exception to backend/rag/'s chromadb-isolation rule
# (tests/unit/test_rag.py::test_import_hygiene only scans backend/**, not
# etl/**): this needs to open an arbitrary *snapshot* path, not the one
# live store get_vector_store() is bound to.
import chromadb
from chromadb.config import Settings

from backend.rag import get_vector_store


def main(argv: list[str] | None = None) -> int:
    source = Path("kb_export/chroma_db")
    if not source.exists():
        print(f"No {source} found -- nothing to import.", file=sys.stderr)
        return 1

    snapshot_client = chromadb.PersistentClient(
        path=str(source), settings=Settings(anonymized_telemetry=False)
    )
    snapshot_collection = snapshot_client.get_or_create_collection("repair_manuals")
    total = snapshot_collection.count()
    if total == 0:
        print("Snapshot has no documents -- nothing to import.")
        return 0

    store = get_vector_store()
    batch_size = 500
    imported = 0
    for offset in range(0, total, batch_size):
        batch = snapshot_collection.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas"],  # type: ignore[list-item]
        )
        documents: list[dict[str, Any]] = [
            {"id": doc_id, "text": text, "metadata": meta}
            for doc_id, text, meta in zip(
                batch["ids"],
                batch["documents"] or [],
                batch["metadatas"] or [],
                strict=True,
            )
        ]
        store.add_documents(documents)
        imported += len(documents)
        print(f"Imported {imported}/{total}")

    print(f"Done: merged {imported} documents from {source} into the live store.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
