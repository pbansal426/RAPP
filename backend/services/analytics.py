"""Server-side PostHog event capture. No-ops entirely when POSTHOG_API_KEY
is unset (the default) -- matches gemini/resend/stripe: never crash or block
a request on a missing third-party key."""

from __future__ import annotations

from typing import Any

import structlog

from backend.core.config import settings

logger = structlog.get_logger()

# Typed as Any because the posthog SDK ships no type stubs; keeping the client
# untyped here confines that Any to this module instead of leaking into callers.
_client: Any = None


def _get_client() -> Any:
    global _client
    if _client is not None:
        return _client
    if not settings.posthog_api_key:
        return None
    try:
        from posthog import Posthog

        _client = Posthog(  # type: ignore[no-untyped-call]
            project_api_key=settings.posthog_api_key, host=settings.posthog_host
        )
    except Exception as exc:  # never let analytics init break a request
        logger.warning("posthog_init_failed", error=str(exc))
        _client = None
    return _client


def track(
    event: str,
    properties: dict[str, object] | None = None,
    distinct_id: str = "server",
) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.capture(
            distinct_id=distinct_id, event=event, properties=properties or {}
        )
    except Exception as exc:  # analytics must never surface as a 5xx
        logger.warning("posthog_capture_failed", event=event, error=str(exc))
