"""Stripe checkout: real integration when configured, mock fallback otherwise.

Same "optional secret, graceful degrade" pattern already used for
Gemini/Resend in this codebase. Building and testing this costs nothing --
Stripe's test mode is free -- it only starts costing anything once real
card payments flow through it in live mode.
"""

from typing import Any

import stripe

from backend.core.config import settings

# Keep in sync with backend/pricing.py's _RAPP_GUIDE_FEE.
_GUIDE_PRICE_USD_CENTS = 399


def stripe_is_configured() -> bool:
    return bool(settings.stripe_secret_key)


def build_mock_checkout_url(vin: str) -> str:
    return f"{settings.backend_url}/api/payments/success-stub?session_id=cs_test_123&vin={vin}"


async def create_real_checkout_session(
    vin: str, symptoms: str, user_id: str | None
) -> str:
    """A real Checkout Session hosted on checkout.stripe.com. The frontend
    must do a genuine full-page redirect here (see CheckoutResponse.mode)
    -- unlike the mock stub, there's a real payment page the customer has
    to complete before Stripe redirects them back."""
    stripe.api_key = settings.stripe_secret_key
    # stripe-python's bundled type stubs lag behind its runtime API --
    # create_async genuinely exists (verified against the installed
    # package), mypy just can't see it statically.
    session = await stripe.checkout.Session.create_async(  # type: ignore[attr-defined]
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "RAPP Repair Guide",
                        "description": f"Step-by-step repair guide for VIN {vin}",
                    },
                    "unit_amount": _GUIDE_PRICE_USD_CENTS,
                },
                "quantity": 1,
            }
        ],
        success_url=(
            f"{settings.frontend_url}/repair/success"
            f"?session_id={{CHECKOUT_SESSION_ID}}&vin={vin}"
        ),
        cancel_url=f"{settings.frontend_url}/results",
        # Stripe metadata values are capped at 500 characters each.
        metadata={"vin": vin, "symptoms": symptoms[:450], "user_id": user_id or ""},
    )
    if not session.url:
        raise RuntimeError("Stripe did not return a checkout URL")
    return str(session.url)


def build_success_redirect_url(
    session_id: str, vin: str, extra_params: dict[str, str]
) -> str:
    params = f"session_id={session_id}&vin={vin}"
    if extra_params:
        params += "&" + "&".join(f"{k}={v}" for k, v in extra_params.items())
    return f"{settings.frontend_url}/repair/success?{params}"


def verify_webhook_signature(payload: bytes, sig_header: str) -> Any:
    """Raises stripe.SignatureVerificationError on an invalid/forged
    signature, or ValueError on an unparseable payload -- callers must
    reject the request on either, never fall back to trusting it.

    Callers are responsible for checking settings.stripe_webhook_secret is
    configured before calling this -- that's a distinct "feature not set
    up yet" case, not a signature failure.
    """
    assert settings.stripe_webhook_secret, "caller must check this is configured"
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )
