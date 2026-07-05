"""Pipeline configuration.

Every tunable lives here so the vertical slice can scale to more vehicles and
sources without touching stage logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

NHTSA_API_BASE = "https://api.nhtsa.gov"
USER_AGENT = "RAPP-ETL/0.1 (automotive repair RAG ingestion; vertical slice)"


@dataclass(frozen=True)
class ChunkingConfig:
    """Chunking targets from the RAG spec (~1000-token chunks, ~200 overlap).

    ``chars_per_token`` is a deliberate cheap heuristic (~4 chars/token for
    English prose) so the ETL layer needs no tokenizer dependency; swap in a
    real tokenizer here if chunk-size precision ever starts to matter.
    """

    target_tokens: int = 1000
    overlap_tokens: int = 200
    chars_per_token: int = 4

    @property
    def chunk_size_chars(self) -> int:
        return self.target_tokens * self.chars_per_token

    @property
    def overlap_chars(self) -> int:
        return self.overlap_tokens * self.chars_per_token


@dataclass(frozen=True)
class EtlConfig:
    api_base: str = NHTSA_API_BASE
    user_agent: str = USER_AGENT
    request_timeout_s: float = 30.0
    max_retries: int = 3
    # Downloaded source PDFs land here (per-vehicle subdirectory) so a failed
    # or suspicious run can be audited against the original artifact.
    workspace_dir: Path = Path("data/etl_workspace")
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    # How many TSB records to scan, in API order, before giving up on finding
    # a downloadable PDF (some records have no attached documents).
    max_record_scan: int = 10
