"""Stripe checkout helpers.

There is deliberately no real Stripe SDK call here yet -- /api/payments/*
are mock endpoints (see CLAUDE.md) that redirect through a stub rather than
a live Checkout Session. This module exists as the seam where a real
`stripe.checkout.Session.create(...)` call would go.
"""

from backend.core.config import settings


def build_mock_checkout_url(vin: str) -> str:
    return f"{settings.backend_url}/api/payments/success-stub?session_id=cs_test_123&vin={vin}"


def build_success_redirect_url(
    session_id: str, vin: str, extra_params: dict[str, str]
) -> str:
    params = f"session_id={session_id}&vin={vin}"
    if extra_params:
        params += "&" + "&".join(f"{k}={v}" for k, v in extra_params.items())
    return f"{settings.frontend_url}/repair/success?{params}"
