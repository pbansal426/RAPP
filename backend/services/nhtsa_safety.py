"""Live NHTSA vehicle-safety lookups: open recalls and consumer complaints.

Deliberately NOT ingested into the RAG vector store the way Technical
Service Bulletins are (see etl/ and backend/rag/). Recall status changes
over time -- a bulk-ingested snapshot could tell a user "no open recall"
when one was issued after the last ingestion run, which is a real
safety/trust problem this app can't afford (unlike TSB text, which doesn't
go stale the same way). Both endpoints are queried live, every time, with
only a short in-memory TTL cache to avoid re-hitting NHTSA for the same
popular vehicle on every page load.
"""

import time
from collections import Counter
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.core.config import settings
from backend.schemas import (
    ComplaintComponentFrequency,
    ComplaintsSummaryResponse,
    RecallInfo,
    RecallsResponse,
)

logger = structlog.get_logger()

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_USER_AGENT = "RAPP-Backend/1.0 (+https://github.com/rapp; vehicle safety lookups)"

# Recalls refresh more eagerly than complaints -- they're the safety-
# critical, "route to a free dealer repair" signal, so staleness matters
# more here even within a cache. Complaints are a softer statistical
# signal that doesn't need to be as fresh.
_RECALLS_TTL_SECONDS = 60 * 60  # 1 hour
_COMPLAINTS_TTL_SECONDS = 60 * 60 * 24  # 24 hours

_TOP_COMPONENTS_LIMIT = 5

_CacheKey = tuple[str, str, str]
_recalls_cache: dict[_CacheKey, tuple[float, list[dict[str, Any]]]] = {}
_complaints_cache: dict[_CacheKey, tuple[float, list[dict[str, Any]]]] = {}


def _cache_key(make: str, model: str, year: str) -> _CacheKey:
    return (make.strip().lower(), model.strip().lower(), year.strip())


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type(
        (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)
    ),
)
async def _get(url: str) -> dict[str, Any]:
    # A fresh client per call rather than a shared pool -- see vin.py's
    # _fetch_nhtsa_vin_fields for why (avoids a long-lived pool silently
    # degrading and wedging every lookup).
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.get(url, headers={"User-Agent": _USER_AGENT})
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    return result


async def _fetch_recall_records(
    make: str, model: str, year: str
) -> list[dict[str, Any]]:
    key = _cache_key(make, model, year)
    cached = _recalls_cache.get(key)
    if cached and time.monotonic() - cached[0] < _RECALLS_TTL_SECONDS:
        return cached[1]

    url = (
        f"{settings.nhtsa_safety_api_base}/recalls/recallsByVehicle"
        f"?make={make}&model={model}&modelYear={year}"
    )
    data = await _get(url)
    records: list[dict[str, Any]] = data.get("results") or []
    _recalls_cache[key] = (time.monotonic(), records)
    return records


async def _fetch_complaint_records(
    make: str, model: str, year: str
) -> list[dict[str, Any]]:
    key = _cache_key(make, model, year)
    cached = _complaints_cache.get(key)
    if cached and time.monotonic() - cached[0] < _COMPLAINTS_TTL_SECONDS:
        return cached[1]

    url = (
        f"{settings.nhtsa_safety_api_base}/complaints/complaintsByVehicle"
        f"?make={make}&model={model}&modelYear={year}"
    )
    data = await _get(url)
    records: list[dict[str, Any]] = data.get("results") or []
    _complaints_cache[key] = (time.monotonic(), records)
    return records


async def get_open_recalls(make: str, model: str, year: str) -> RecallsResponse:
    """Never raises on NHTSA failure -- callers (the /results page) must not
    break just because a live third-party lookup timed out. Logs and
    returns an empty result instead."""
    try:
        records = await _fetch_recall_records(make, model, year)
    except httpx.HTTPError as exc:
        logger.warning(
            "nhtsa_recalls_fetch_failed",
            make=make,
            model=model,
            year=year,
            error=str(exc),
        )
        return RecallsResponse(open_recalls=[], count=0)

    recalls = [
        RecallInfo(
            campaign_number=str(r.get("NHTSACampaignNumber") or ""),
            component=str(r.get("Component") or ""),
            summary=str(r.get("Summary") or ""),
            consequence=str(r.get("Consequence") or ""),
            remedy=str(r.get("Remedy") or ""),
            report_received_date=str(r.get("ReportReceivedDate") or ""),
        )
        for r in records
    ]
    return RecallsResponse(open_recalls=recalls, count=len(recalls))


async def get_complaints_summary(
    make: str, model: str, year: str
) -> ComplaintsSummaryResponse:
    """Same never-raise contract as get_open_recalls."""
    try:
        records = await _fetch_complaint_records(make, model, year)
    except httpx.HTTPError as exc:
        logger.warning(
            "nhtsa_complaints_fetch_failed",
            make=make,
            model=model,
            year=year,
            error=str(exc),
        )
        return ComplaintsSummaryResponse(total_complaints=0, top_components=[])

    # NHTSA's `components` field is a single comma-separated string per
    # complaint (e.g. "POWER TRAIN,AIR BAGS,ENGINE"), not a list -- a
    # complaint naming multiple components counts toward each of them.
    counts: Counter[str] = Counter()
    for record in records:
        components_field = str(record.get("components") or "")
        for component in components_field.split(","):
            component = component.strip()
            if component:
                counts[component] += 1

    top_components = [
        ComplaintComponentFrequency(component=component, count=count)
        for component, count in counts.most_common(_TOP_COMPONENTS_LIMIT)
    ]
    return ComplaintsSummaryResponse(
        total_complaints=len(records), top_components=top_components
    )
