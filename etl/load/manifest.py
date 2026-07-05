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

    def _get_key(self, vehicle_slug: str, nhtsa_id: str, file_name: str) -> str:
        # Scoped per-vehicle: the same NHTSA bulletin ID is frequently shared
        # across multiple models/years (e.g. a shared driveline TSB). A global
        # key would mark it "ingested" the first time any vehicle processes
        # it, silently skipping the metadata tagging (make/model/year) every
        # other vehicle needs for its own RAG filter to ever find that chunk.
        return f"{vehicle_slug}/{nhtsa_id}/{file_name}"

    def mark_status(
        self,
        vehicle_slug: str,
        nhtsa_id: str,
        file_name: str,
        status: Status,
        chunks_count: int = 0,
    ) -> None:
        key = self._get_key(vehicle_slug, nhtsa_id, file_name)
        self.manifest[key] = {
            "status": status,
            "chunks_count": chunks_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.save()

    def get_status(
        self, vehicle_slug: str, nhtsa_id: str, file_name: str
    ) -> Status | None:
        key = self._get_key(vehicle_slug, nhtsa_id, file_name)
        entry = self.manifest.get(key)
        return entry.get("status") if entry else None

    def is_ingested(self, vehicle_slug: str, nhtsa_id: str, file_name: str) -> bool:
        return self.get_status(vehicle_slug, nhtsa_id, file_name) == "ingested"

    def reset_vehicle(self, vehicle_slug: str) -> int:
        """Clear all manifest entries for one vehicle so it can be
        re-ingested from scratch (e.g. after wiping the vector store).
        Returns the number of entries removed."""
        prefix = f"{vehicle_slug}/"
        keys_to_remove = [k for k in self.manifest if k.startswith(prefix)]
        for key in keys_to_remove:
            del self.manifest[key]
        if keys_to_remove:
            self.save()
        return len(keys_to_remove)
