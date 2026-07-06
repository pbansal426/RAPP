from typing import Any

import stripe
import structlog
from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from backend.core.config import settings
from backend.core.security import decode_token
from backend.schemas import CheckoutRequest, CheckoutResponse
from backend.services.stripe import (
    build_mock_checkout_url,
    build_success_redirect_url,
    create_real_checkout_session,
    stripe_is_configured,
    verify_webhook_signature,
)

logger = structlog.get_logger()
router = APIRouter()


def _optional_user_id(authorization: str | None) -> str | None:
    """Best-effort caller identity for Stripe metadata -- checkout must work
    for logged-out visitors too, so a missing/invalid token just means no
    user_id gets attached, never a rejected request."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = decode_token(
        authorization.removeprefix("Bearer "), expected_type="access"
    )
    return payload.get("sub") if payload else None


@router.post("/api/payments/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest, authorization: str | None = Header(default=None)
) -> CheckoutResponse:
    if not stripe_is_configured():
        return CheckoutResponse(
            checkout_url=build_mock_checkout_url(request.vin), mode="mock"
        )

    try:
        checkout_url = await create_real_checkout_session(
            vin=request.vin,
            symptoms=request.symptoms,
            user_id=_optional_user_id(authorization),
        )
    except Exception as exc:
        logger.error("stripe_checkout_creation_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment service unavailable. Please try again.",
        ) from exc

    return CheckoutResponse(checkout_url=checkout_url, mode="live")


@router.get("/api/payments/success-stub")
async def success_stub(request: Request, session_id: str, vin: str) -> RedirectResponse:
    # Forward all query params (including extras like promo, referrer) to the frontend
    extra = {
        k: v for k, v in request.query_params.items() if k not in ("session_id", "vin")
    }
    redirect_url = build_success_redirect_url(session_id, vin, extra)
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict[str, str]:
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook is not configured.",
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event: Any = verify_webhook_signature(payload, sig_header)
    except stripe.SignatureVerificationError as exc:  # type: ignore[attr-defined]
        logger.warning("stripe_webhook_invalid_signature", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature."
        ) from exc
    except ValueError as exc:
        logger.warning("stripe_webhook_invalid_payload", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload."
        ) from exc

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata") or {}
        # Deliberately NOT auto-generating/saving a repair guide here: the
        # frontend already triggers generation (on the paywall CTA click,
        # or on landing at /repair) and caches it client-side, so doing it
        # again server-side would mean a second, redundant Gemini call per
        # purchase. Unlocking access itself also doesn't depend on this
        # webhook -- that already happens via the success_url redirect +
        # rapp_unlocked_{vin} localStorage flag. This handler's job is the
        # audit trail: proof a real payment happened, independent of
        # whether the customer's browser ever completes that redirect.
        logger.info(
            "stripe_checkout_completed",
            session_id=session.get("id"),
            vin=metadata.get("vin"),
            user_id=metadata.get("user_id") or None,
        )

    return {"status": "received"}
