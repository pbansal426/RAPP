# ruff: noqa: B008 -- FastAPI's Depends(...) is meant to be called in
# argument defaults; this isn't the mutable-default-argument bug B008 flags.
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.models import DbGuideUnlock, DbUser
from backend.core.security import decode_token
from backend.schemas import CheckoutRequest, CheckoutResponse
from backend.services.payments_mor import (
    build_mock_checkout_url,
    build_success_redirect_url,
    create_polar_checkout_session,
    parse_date,
    polar_is_configured,
    verify_webhook_signature,
)

logger = structlog.get_logger()
router = APIRouter()


def _optional_user_id(authorization: str | None) -> str | None:
    """Best-effort caller identity for Polar metadata -- checkout must work
    for logged-out visitors too, so a missing/invalid token just means no
    user_id gets attached, never a rejected request."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = decode_token(
        authorization.removeprefix("Bearer "), expected_type="access"
    )
    return payload.get("sub") if payload else None


def _record_guide_unlock(
    db: Session,
    session_id: str,
    vin: str,
    user_id: str | None,
    price_type: str | None,
) -> None:
    """Upsert server-side proof that `session_id` paid to unlock `vin`'s guide."""
    if not session_id or not vin:
        return
    unlock = (
        db.query(DbGuideUnlock).filter(DbGuideUnlock.session_id == session_id).first()
    )
    if unlock is None:
        unlock = DbGuideUnlock(session_id=session_id, vin=vin.strip().upper())
        db.add(unlock)
    else:
        unlock.vin = vin.strip().upper()
    unlock.user_id = user_id
    unlock.price_type = price_type
    db.commit()


@router.post("/api/payments/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest, authorization: str | None = Header(default=None)
) -> CheckoutResponse:
    if not polar_is_configured():
        return CheckoutResponse(
            checkout_url=build_mock_checkout_url(request.vin, request.price_type),
            mode="mock",
        )

    try:
        checkout_url = await create_polar_checkout_session(
            vin=request.vin,
            price_type=request.price_type,
            symptoms=request.symptoms,
            user_id=_optional_user_id(authorization),
        )
    except Exception as exc:
        logger.error("polar_checkout_creation_failed", error=str(exc))
        raise HTTPException(
            status_code=(
                status.HTTP_524_A_TIMEOUT_OCCURRED
                if "Timeout" in str(exc)
                else status.HTTP_502_BAD_GATEWAY
            ),
            detail="Payment service unavailable. Please try again.",
        ) from exc

    return CheckoutResponse(checkout_url=checkout_url, mode="live")


@router.get("/api/payments/success-stub")
async def success_stub(
    request: Request,
    session_id: str,
    vin: str,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> RedirectResponse:
    # Forward all query params (including extras like price_type, etc) to the frontend
    extra = {
        k: v for k, v in request.query_params.items() if k not in ("session_id", "vin")
    }
    # Mock/dev checkouts never hit a real webhook, so this stub is the only
    # place a single-incident "payment" ever completes -- record the unlock
    # here or /api/repair would have nothing server-side to verify against.
    _record_guide_unlock(
        db,
        session_id=session_id,
        vin=vin,
        user_id=_optional_user_id(authorization),
        price_type=extra.get("price_type"),
    )
    redirect_url = build_success_redirect_url(session_id, vin, extra)
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/api/webhooks/payments")
async def polar_webhook(
    request: Request, db: Session = Depends(get_db)
) -> dict[str, str]:
    if not settings.polar_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polar webhook is not configured.",
        )

    payload = await request.body()
    sig_header = request.headers.get("x-polar-signature", "")
    if not sig_header or not verify_webhook_signature(payload, sig_header):
        logger.warning("polar_webhook_invalid_signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature.",
        )

    try:
        event = await request.json()
    except ValueError as exc:
        logger.warning("polar_webhook_invalid_payload", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload.",
        ) from exc

    # Support both Polar's standard "event" and general webhook "type" fields
    event_type = event.get("event") or event.get("type")
    data_obj = event.get("data", {})
    metadata = data_obj.get("metadata", {}) or {}

    logger.info("polar_webhook_received", event_type=event_type)

    # Identify user from metadata user_id or email
    user = None
    user_id = metadata.get("user_id")
    if user_id:
        user = db.query(DbUser).filter(DbUser.id == user_id).first()

    if not user:
        email = data_obj.get("customer_email") or data_obj.get("email")
        if not email and "customer" in data_obj:
            email = data_obj["customer"].get("email")
        if email:
            user = (
                db.query(DbUser).filter(DbUser.email == email.strip().lower()).first()
            )

    if event_type in ("subscription.created", "subscription.updated"):
        if user:
            user.subscription_status = data_obj.get("status") or "active"
            user.mor_customer_id = data_obj.get("customer_id")
            user.mor_subscription_id = data_obj.get("id")

            expires_at_val = data_obj.get("current_period_end") or data_obj.get(
                "ends_at"
            )
            user.subscription_expires_at = parse_date(expires_at_val)

            db.add(user)
            db.commit()
            logger.info(
                "polar_subscription_updated",
                user_id=user.id,
                status=user.subscription_status,
                subscription_id=user.mor_subscription_id,
            )
        else:
            logger.warning(
                "polar_subscription_webhook_user_not_found", metadata=metadata
            )

    elif event_type == "subscription.cancelled":
        if user:
            user.subscription_status = "cancelled"
            ends_at_val = data_obj.get("ends_at") or data_obj.get("current_period_end")
            if ends_at_val:
                user.subscription_expires_at = parse_date(ends_at_val)
            db.add(user)
            db.commit()
            logger.info("polar_subscription_cancelled", user_id=user.id)
        else:
            logger.warning(
                "polar_subscription_cancelled_user_not_found", metadata=metadata
            )

    elif event_type in ("checkout.created", "checkout.updated", "order.created"):
        # The frontend's `stripe_session_id` is always the *checkout* id (the
        # `{CHECKOUT_ID}` placeholder substituted into success_url at
        # creation) -- an Order event must key off `checkout_id`, not the
        # Order's own `id`, or the unlock record would never match what the
        # client later sends to /api/repair.
        checkout_session_id = (
            data_obj.get("checkout_id") or data_obj.get("id") or event.get("id")
        )
        vin = metadata.get("vin")
        checkout_status = (data_obj.get("status") or "").lower()
        # "checkout.created"/an unconfirmed "checkout.updated" only means the
        # customer *started* checkout, not that payment succeeded -- unlocking
        # here would let anyone skip payment entirely. Polar only emits
        # "order.created" (or a "checkout.updated" carrying a
        # confirmed/succeeded status) once the payment has actually cleared.
        payment_confirmed = event_type == "order.created" or checkout_status in (
            "confirmed",
            "succeeded",
        )
        # Only single-incident purchases need a per-VIN unlock record --
        # annual pass access is gated on DbUser.subscription_status instead.
        if (
            payment_confirmed
            and metadata.get("price_type") != "annual"
            and checkout_session_id
            and vin
        ):
            _record_guide_unlock(
                db,
                session_id=checkout_session_id,
                vin=vin,
                user_id=user_id or (user.id if user else None),
                price_type=metadata.get("price_type"),
            )
        logger.info(
            "polar_checkout_completed",
            session_id=checkout_session_id,
            vin=vin,
            user_id=user_id or (user.id if user else None),
            payment_confirmed=payment_confirmed,
        )

    return {"status": "received"}


@router.post("/api/webhooks/stripe")
async def stripe_webhook_deprecated() -> dict[str, str]:
    """Deprecated Stripe webhook endpoint."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Stripe webhook endpoint is deprecated. Please use Polar Merchant of Record.",
    )
