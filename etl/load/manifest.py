import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

Status = Literal["ingested", "skipped_no_text", "failed"]


class IngestManifest:
    """Tracks the state of ingested PDFs to allow resuming pipelines."""

    def __init__(self, manifest_path: str = "data/etl_workspace/ingest_manifest.json"):
        self.manifest_path = Path(manifest_path)
        self.manifest: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, encoding="utf-8") as f:
                    self.manifest = json.load(f)
            except json.JSONDecodeError:
                self.manifest = {}

    def save(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2)

    def _get_key(self, nhtsa_id: str, file_name: str) -> str:
        return f"{nhtsa_id}/{file_name}"

    def mark_status(
        self, nhtsa_id: str, file_name: str, status: Status, chunks_count: int = 0
    ) -> None:
        key = self._get_key(nhtsa_id, file_name)
        self.manifest[key] = {
            "status": status,
            "chunks_count": chunks_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.save()

    def get_status(self, nhtsa_id: str, file_name: str) -> Status | None:
        key = self._get_key(nhtsa_id, file_name)
        entry = self.manifest.get(key)
        return entry.get("status") if entry else None

    def is_ingested(self, nhtsa_id: str, file_name: str) -> bool:
        return self.get_status(nhtsa_id, file_name) == "ingested"
