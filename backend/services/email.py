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
