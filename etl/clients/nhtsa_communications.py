"""Client for NHTSA's Manufacturer Communications (TSB) dataset.

There is no direct "TSBs by year/make/model" route on api.nhtsa.gov — the
tempting ``/manufacturerCommunications`` and ``/safetyIssues`` routes accept
vehicle query params but *silently ignore them* (verified 2026-07: a Corolla
query returns Audi and International Truck records). The reliable flow is the
two-step one nhtsa.gov's own vehicle pages use:

1. ``GET /vehicles/bySearch?query={year} {make} {model}&data=manufacturerCommunications``
   → one vehicle record whose ``safetyIssues.manufacturerCommunications[]``
   lists TSBs (NHTSA id, bulletin number, human summary) but exposes
   ``associatedDocuments`` only as a follow-up API URL.
2. ``GET /safetyIssues/byNhtsaId?nhtsaId={id}&filter=issueType&filterValue=manufacturerCommunications``
   → the same communication with ``associatedDocuments[]`` resolved to
   concrete PDF URLs on static.nhtsa.gov.
"""

from __future__ import annotations

import logging
from pathlib import Path
from types import TracebackType
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from etl.config import EtlConfig
from etl.models import TsbDocument, TsbRecord, VehicleKey

log = logging.getLogger(__name__)

_ISSUE_TYPE = "manufacturerCommunications"


class NhtsaApiError(RuntimeError):
    """Raised when the NHTSA API misbehaves after retries."""


def _is_retryable(exc: BaseException) -> bool:
    """Retry transport failures and 5xx; 4xx means the request itself is wrong."""
    if isinstance(exc, httpx.TransportError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


class NhtsaManufacturerCommunicationsClient:
    def __init__(self, config: EtlConfig) -> None:
        self._config = config
        self._http = httpx.Client(
            base_url=config.api_base,
            headers={"User-Agent": config.user_agent},
            timeout=config.request_timeout_s,
            follow_redirects=True,
        )

    def __enter__(self) -> NhtsaManufacturerCommunicationsClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        response = self._http.get(url, params=params)
        response.raise_for_status()
        return response

    def list_communications(self, vehicle: VehicleKey) -> list[TsbRecord]:
        """All TSBs NHTSA lists for the vehicle, in API order."""
        try:
            payload = self._get(
                "/vehicles/bySearch",
                params={
                    "query": f"{vehicle.year} {vehicle.make} {vehicle.model}",
                    "data": _ISSUE_TYPE,
                    "productDetail": "minimal",
                    "offset": 0,
                    "max": 10,
                },
            ).json()
        except (httpx.HTTPError, ValueError) as exc:
            raise NhtsaApiError(f"vehicle search failed for {vehicle}: {exc}") from exc

        match = self._select_vehicle(payload.get("results") or [], vehicle)
        if match is None:
            raise NhtsaApiError(f"NHTSA vehicle search found no match for {vehicle}")
        communications = (match.get("safetyIssues") or {}).get(_ISSUE_TYPE) or []
        records = [self._to_record(item) for item in communications]
        log.info(
            "NHTSA lists %d manufacturer communications for %s", len(records), vehicle
        )
        return records

    def resolve_documents(self, record: TsbRecord) -> list[TsbDocument]:
        """Resolve a record's attached documents to concrete download URLs."""
        try:
            payload = self._get(
                "/safetyIssues/byNhtsaId",
                params={
                    "nhtsaId": record.nhtsa_id,
                    "filter": "issueType",
                    "filterValue": _ISSUE_TYPE,
                },
            ).json()
        except (httpx.HTTPError, ValueError) as exc:
            raise NhtsaApiError(
                f"document resolution failed for NHTSA id {record.nhtsa_id}: {exc}"
            ) from exc

        documents: list[TsbDocument] = []
        for result in payload.get("results") or []:
            for item in result.get(_ISSUE_TYPE) or []:
                if item.get("nhtsaIdNumber") != record.nhtsa_id:
                    continue
                for doc in item.get("associatedDocuments") or []:
                    url = doc.get("url")
                    if not url:
                        continue
                    documents.append(
                        TsbDocument(
                            file_name=doc.get("fileName") or url.rsplit("/", 1)[-1],
                            url=url,
                            mime_type=doc.get("mimeType") or "",
                            doc_summary=doc.get("summary"),
                        )
                    )
        return documents

    def download(self, document: TsbDocument, dest_dir: Path) -> Path:
        """Download a document into the workspace, verifying it is a real PDF."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / document.file_name
        try:
            response = self._get(document.url)
        except httpx.HTTPError as exc:
            raise NhtsaApiError(f"download failed for {document.url}: {exc}") from exc
        if not response.content.startswith(b"%PDF"):
            raise NhtsaApiError(
                f"{document.url} did not return a PDF (starts with "
                f"{response.content[:8]!r})"
            )
        dest.write_bytes(response.content)
        log.info(
            "downloaded %s (%d bytes) -> %s",
            document.file_name,
            len(response.content),
            dest,
        )
        return dest

    @staticmethod
    def _select_vehicle(
        results: list[dict[str, Any]], vehicle: VehicleKey
    ) -> dict[str, Any] | None:
        """Pick the exact year/make/model match; the search is fuzzy-ish."""
        for result in results:
            if (
                result.get("modelYear") == vehicle.year
                and str(result.get("make", "")).upper() == vehicle.make.upper()
                and str(result.get("vehicleModel", "")).upper() == vehicle.model.upper()
            ):
                return result
        if results:
            log.warning(
                "no exact vehicle match for %s; falling back to first search result %s",
                vehicle,
                {k: results[0].get(k) for k in ("modelYear", "make", "vehicleModel")},
            )
            return results[0]
        return None

    @staticmethod
    def _to_record(item: dict[str, Any]) -> TsbRecord:
        components = tuple(
            component["name"]
            for component in item.get("components") or []
            if component.get("name")
        )
        return TsbRecord(
            nhtsa_id=item.get("nhtsaIdNumber") or 0,
            communication_number=item.get("manufacturerCommunicationNumber"),
            summary=item.get("summary"),
            communication_date=item.get("communicationDate"),
            components=components,
            document_count=item.get("associatedDocumentsCount") or 0,
        )
