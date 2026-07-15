"""Polar Merchant of Record (MoR) checkout: real integration when configured, mock fallback otherwise.

Graceful degradation when token/secrets are missing, similar to Stripe integration.
"""

import hashlib
import hmac
from typing import Any

import httpx

from backend.core.config import settings


def polar_is_configured() -> bool:
    """Check if Polar token is configured."""
    return bool(settings.polar_access_token)


def build_mock_checkout_url(vin: str, price_type: str) -> str:
    """Build mock success redirect URL for local development/testing."""
    return f"{settings.backend_url}/api/payments/success-stub?session_id=cs_test_123&vin={vin}&price_type={price_type}"


def build_success_redirect_url(session_id: str, vin: str, extra: dict[str, Any]) -> str:
    """Construct redirect URL to the frontend successful payment page."""
    params = f"session_id={session_id}&vin={vin}"
    if extra:
        params += "&" + "&".join(f"{k}={v}" for k, v in extra.items())
    return f"{settings.frontend_url}/repair/success?{params}"


async def create_polar_checkout_session(
    vin: str, price_type: str, symptoms: str, user_id: str | None
) -> str:
    """Create a checkout session with Polar. Maps price_type to configured product IDs."""
    resolved_price_type = price_type
    if resolved_price_type == "single":
        # Resolve to tier_1, tier_2, or tier_3 dynamically based on pricing breakdown
        from backend.pricing import build_cost_breakdown
        from backend.repair_templates import select_template

        template = select_template(symptoms, [])
        breakdown = build_cost_breakdown(template)
        guide_fee = breakdown["guide_fee"]
        if guide_fee == 4.99:
            resolved_price_type = "tier_1"
        elif guide_fee == 9.99:
            resolved_price_type = "tier_2"
        else:
            resolved_price_type = "tier_3"

    # Map resolved price_type to product ID
    if resolved_price_type == "tier_1":
        product_id = settings.polar_product_id_tier_1
    elif resolved_price_type == "tier_2":
        product_id = settings.polar_product_id_tier_2
    elif resolved_price_type == "tier_3":
        product_id = settings.polar_product_id_tier_3
    elif resolved_price_type == "annual":
        product_id = settings.polar_product_id_annual
    else:
        product_id = settings.polar_product_id_tier_1

    if polar_is_configured():
        headers = {
            "Authorization": f"Bearer {settings.polar_access_token}",
            "Content-Type": "application/json",
        }
        success_url = (
            f"{settings.frontend_url}/repair/success"
            f"?session_id={{CHECKOUT_ID}}&vin={vin}"
        )
        payload = {
            "product_id": product_id,
            "success_url": success_url,
            "metadata": {
                "vin": vin,
                "price_type": resolved_price_type,
                "symptoms": symptoms[:450],
                "user_id": user_id or "",
            },
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.polar.sh/v1/checkouts/custom",
                json=payload,
                headers=headers,
                timeout=10.0,
            )
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Polar API error: {response.status_code} - {response.text}"
                )

            data = response.json()
            checkout_url = data.get("url")
            if not checkout_url:
                raise RuntimeError("Polar did not return a checkout URL")
            return str(checkout_url)
    else:
        return build_mock_checkout_url(vin, resolved_price_type)


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify HMAC signature of the Polar webhook payload."""
    if not settings.polar_webhook_secret:
        return False

    expected_prefix = "sha256="
    if signature.startswith(expected_prefix):
        signature = signature[len(expected_prefix) :]

    mac = hmac.new(
        settings.polar_webhook_secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    )
    computed = mac.hexdigest()
    return hmac.compare_digest(computed, signature)


def parse_date(val: Any) -> Any:
    """Parse dynamic date representation from Polar API payload."""
    if not val:
        return None
    from datetime import datetime

    if isinstance(val, int | float):
        return datetime.utcfromtimestamp(val)
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            try:
                return datetime.strptime(val[:19], "%Y-%m-%dT%H:%M:%S")
            except Exception:
                return None
    return None
