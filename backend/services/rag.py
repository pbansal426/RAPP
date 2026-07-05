"""Thin pass-through to backend.rag.

Kept separate from backend/rag/ itself (which owns the vector store
backends and is the only package allowed to touch that dependency directly,
per tests/unit/test_rag.py::test_import_hygiene) so routers depend on the
services layer rather than reaching into backend.rag directly.
"""

from typing import Any


def retrieve(
    query: str, vin_meta: dict[str, Any], k: int = 5
) -> list[dict[str, Any]] | None:
    from backend.rag.retriever import retrieve as _retrieve

    return _retrieve(query=query, vin_meta=vin_meta, k=k)
