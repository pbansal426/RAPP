"""Mock load stage: render the pipeline result as a terminal audit log.

This is the seam where the real loader (vector-store upsert via
``backend/rag/``) will plug in later; until then the audit log is the
acceptance artifact for the vertical-slice test.
"""

from __future__ import annotations

import json
import textwrap

from etl.pipeline import VerticalSliceResult

_WIDTH = 78


def _heading(title: str) -> None:
    print()
    print(title)
    print("─" * _WIDTH)


def _wrap(text: str, indent: str = "    ") -> str:
    paragraphs = text.splitlines() or [""]
    return "\n".join(
        (
            textwrap.fill(
                p, width=_WIDTH, initial_indent=indent, subsequent_indent=indent
            )
            if p.strip()
            else ""
        )
        for p in paragraphs
    )


def print_audit_log(result: VerticalSliceResult) -> None:
    vehicle, record, document = result.vehicle, result.record, result.document

    print("═" * _WIDTH)
    print(" RAPP ETL — VERTICAL SLICE AUDIT LOG")
    print(f" vehicle: {vehicle}  |  source: NHTSA Manufacturer Communications")
    print("═" * _WIDTH)

    _heading("[A] ORIGINAL NHTSA TSB SUMMARY")
    print(f"  NHTSA ID:    {record.nhtsa_id}")
    print(f"  Bulletin:    {record.communication_number or '—'}")
    print(f"  Date:        {record.communication_date or '—'}")
    print(f"  Components:  {', '.join(record.components) or '—'}")
    print(f"  Document:    {document.file_name} ({document.doc_summary or 'no label'})")
    print(f"  PDF URL:     {document.url}")
    print(f"  Local copy:  {result.pdf_path}")
    print("  Summary:")
    print(_wrap(record.summary or "(no summary provided by NHTSA)"))

    _heading(f"[B] EXTRACTED TEXT CHUNK  (showing 1 of {len(result.text_chunks)})")
    if result.text_chunks:
        chunk = result.text_chunks[0]
        print(f"  metadata:   {json.dumps(chunk.metadata)}")
        print(f"  provenance: {json.dumps(chunk.provenance)}")
        print("  content:")
        print(textwrap.indent(chunk.content, "    │ "))
    else:
        print(
            "  !! no machine-readable text extracted — likely a scanned/image-only PDF;"
        )
        print("     route to the OCR path when that stage exists.")

    _heading(f"[C] EXTRACTED TABLE  (showing 1 of {len(result.table_chunks)})")
    if result.table_chunks:
        table_chunk = result.table_chunks[0]
        print(f"  metadata:   {json.dumps(table_chunk.metadata)}")
        print(f"  provenance: {json.dumps(table_chunk.provenance)}")
        print("  table:")
        print(
            textwrap.indent(
                json.dumps(table_chunk.table, indent=2, ensure_ascii=False), "    "
            )
        )
    else:
        print(
            "  no tables detected in this document (normal for prose-only bulletins)."
        )

    _heading("[STATS]")
    print(
        f"  pages={result.parsed.page_count}"
        f"  prose_chars={len(result.parsed.prose)}"
        f"  text_chunks={len(result.text_chunks)}"
        f"  tables={len(result.table_chunks)}"
    )
    print("═" * _WIDTH)
