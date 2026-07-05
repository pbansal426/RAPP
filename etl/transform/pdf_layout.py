"""Layout-aware PDF parsing: separate structured tables from prose.

Tables are the payload the Tool-Aware RAG algorithm cross-references against
the user's tool inventory (torque specs, part numbers, fluid capacities), so
they are extracted as header-keyed row dicts rather than flattened into text.
Prose is extracted *outside* detected table bounding boxes so table cells are
never duplicated into (and never corrupt) the instructional text stream.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pdfplumber

from etl.models import ParsedPdf

log = logging.getLogger(__name__)

BBox = tuple[float, float, float, float]  # (x0, top, x1, bottom)


class LayoutAwarePdfParser:
    # A "table" smaller than this is almost always a text box or layout
    # artifact of pdfplumber's line-based detection — keep it in the prose.
    MIN_ROWS = 2  # header + at least one data row
    MIN_COLS = 2

    def parse(self, pdf_path: Path) -> ParsedPdf:
        prose_pages: list[str] = []
        tables: list[dict[str, Any]] = []
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            for page_number, page in enumerate(pdf.pages, start=1):
                table_bboxes: list[BBox] = []
                for found in page.find_tables():
                    structured = self._structure_table(found.extract(), page_number)
                    if structured is not None:
                        tables.append(structured)
                        table_bboxes.append(found.bbox)
                prose = self._prose_outside(page, table_bboxes).strip()
                if prose:
                    prose_pages.append(prose)
        log.info(
            "parsed %s: %d pages, %d tables, %d chars of prose",
            pdf_path.name,
            page_count,
            len(tables),
            sum(len(p) for p in prose_pages),
        )
        return ParsedPdf(
            prose="\n\n".join(prose_pages), tables=tables, page_count=page_count
        )

    @staticmethod
    def _prose_outside(page: pdfplumber.page.Page, bboxes: list[BBox]) -> str:
        """Page text with everything inside table bounding boxes removed."""
        if not bboxes:
            return page.extract_text() or ""

        def keep(obj: dict[str, Any]) -> bool:
            try:
                v_mid = (obj["top"] + obj["bottom"]) / 2
                h_mid = (obj["x0"] + obj["x1"]) / 2
            except KeyError:
                return True
            return not any(
                x0 <= h_mid < x1 and top <= v_mid < bottom
                for (x0, top, x1, bottom) in bboxes
            )

        return page.filter(keep).extract_text() or ""

    def _structure_table(
        self, raw_rows: list[list[str | None]] | None, page_number: int
    ) -> dict[str, Any] | None:
        """Normalize a raw pdfplumber table into a retrieval-friendly dict.

        Output rows are keyed by header so downstream code can do
        ``row["Torque (ft-lbf)"]`` instead of positional indexing. Returns
        ``None`` for degenerate detections (too small, effectively empty).
        """
        rows = [[self._clean_cell(cell) for cell in row] for row in raw_rows or []]
        rows = [row for row in rows if any(row)]
        if not rows:
            return None
        width = max(len(row) for row in rows)
        rows = [row + [""] * (width - len(row)) for row in rows]
        keep_cols = [i for i in range(width) if any(row[i] for row in rows)]
        rows = [[row[i] for i in keep_cols] for row in rows]
        if len(rows) < self.MIN_ROWS or (rows and len(rows[0]) < self.MIN_COLS):
            return None

        headers = self._header_row(rows[0])
        body = rows[1:] if headers is not None else rows
        if headers is None:
            headers = [f"col_{i + 1}" for i in range(len(rows[0]))]
        if not body:
            return None
        return {
            "page": page_number,
            "headers": headers,
            "n_rows": len(body),
            "n_columns": len(headers),
            "rows": [dict(zip(headers, row, strict=True)) for row in body],
        }

    @staticmethod
    def _clean_cell(cell: str | None) -> str:
        """Collapse cell whitespace (pdfplumber keeps intra-cell line breaks)."""
        return " ".join(str(cell).split()) if cell is not None else ""

    @staticmethod
    def _header_row(first_row: list[str]) -> list[str] | None:
        """First row is the header only if every cell is populated; dedupe names."""
        if not all(first_row):
            return None
        headers: list[str] = []
        for cell in first_row:
            name, n = cell, 2
            while name in headers:
                name = f"{cell}_{n}"
                n += 1
            headers.append(name)
        return headers
