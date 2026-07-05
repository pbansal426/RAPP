"""RAPP data-ingestion (ETL) pipelines.

Offline batch ingestion for the Tool-Aware RAG store. Deliberately a sibling
of ``backend/`` rather than part of it: ingestion runs on a different cadence
(batch vs. request/response), carries heavier parsing dependencies (see the
``etl`` dependency group in ``pyproject.toml``), and must never be imported by
the serving app. The eventual real load stage will call into ``backend/rag/``
through its public factory — nothing here may import ``chromadb`` directly.

Layout:
    clients/    — upstream source-API clients (NHTSA manufacturer communications)
    transform/  — layout-aware PDF parsing and recursive text chunking
    load/       — sinks; currently a mock loader that prints a terminal audit log
    pipeline.py — orchestration of one extract → transform → load run
    config.py   — all tunables (endpoints, workspace, chunking parameters)
    models.py   — typed records passed between stages

Run the 2010 Toyota Corolla vertical slice:
    uv run --group etl python -m etl
"""
