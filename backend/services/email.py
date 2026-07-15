"""Magic-link email delivery via Resend.

Callers should treat a `False` return as "not sent" and fall back to
dev-mode behavior (returning the link directly in the API response) rather
than treating it as a hard error -- see backend/routers/auth.py.
"""

import httpx
import structlog

from backend.core.config import settings

logger = structlog.get_logger()

RESEND_API_URL = "https://api.resend.com/emails"


async def send_magic_link_email(to_email: str, magic_link: str) -> bool:
    if not settings.resend_api_key:
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.email_from,
                    "to": [to_email],
                    "subject": "Your RAPP sign-in link",
                    "html": (
                        "<p>Click below to sign in to RAPP:</p>"
                        f'<p><a href="{magic_link}">{magic_link}</a></p>'
                        "<p>This link expires in 15 minutes. If you didn't "
                        "request this, you can ignore this email.</p>"
                    ),
                },
            )
        if response.status_code >= 400:
            logger.warning(
                "resend_send_failed",
                status_code=response.status_code,
                body=response.text[:500],
            )
            return False
        return True
    except httpx.HTTPError as exc:
        logger.warning("resend_send_error", error=str(exc))
        return False


async def send_recall_alert_email(
    to_email: str, vehicle_desc: str, recalls: list[dict[str, str]]
) -> bool:
    """Notifies a user of newly-detected open NHTSA recalls on their saved
    vehicle. Same dev-mode contract as send_magic_link_email: returns False
    (rather than raising) when no email provider is configured or the send
    fails, so the caller (the recall-watch cron) can log and move on to the
    next vehicle instead of crashing the whole run."""
    if not settings.resend_api_key:
        return False

    items_html = "".join(
        f"<li><strong>{r['component']}</strong>: {r['summary']}"
        f"<br/><em>Remedy:</em> {r['remedy']}</li>"
        for r in recalls
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.email_from,
                    "to": [to_email],
                    "subject": f"Safety recall alert for your {vehicle_desc}",
                    "html": (
                        f"<p>NHTSA has issued a new safety recall for your "
                        f"<strong>{vehicle_desc}</strong>:</p>"
                        f"<ul>{items_html}</ul>"
                        "<p>Recall repairs are free at any authorized "
                        "dealership. Sign in to RAPP to see the full "
                        "details for your vehicle.</p>"
                    ),
                },
            )
        if response.status_code >= 400:
            logger.warning(
                "resend_recall_alert_send_failed",
                status_code=response.status_code,
                body=response.text[:500],
            )
            return False
        return True
    except httpx.HTTPError as exc:
        logger.warning("resend_recall_alert_send_error", error=str(exc))
        return False
