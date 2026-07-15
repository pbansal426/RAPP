import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.core.security import create_access_token
from backend.main import app, settings
from backend.core.database import get_db
from backend.core.models import DbGuideUnlock, DbUser


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    # Retrieve the database session configured for testing
    from backend.core.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sign_payload(payload: bytes, secret: str) -> str:
    """Builds a real Polar-format signature header (sha256 hex signature)
    so tests exercise actual HMAC verification."""
    mac = hmac.new(
        secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256
    )
    return f"sha256={mac.hexdigest()}"


def test_create_checkout_falls_back_to_mock_when_unconfigured(client):
    assert not settings.polar_access_token
    response = client.post(
        "/api/payments/create-checkout",
        json={"vin": "1HGBH41JXMN109186", "symptoms": "rough idle", "price_type": "single"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "mock"
    assert "success-stub" in data["checkout_url"]


def test_create_checkout_uses_real_polar_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "polar_access_token", "pat_test_fake")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"url": "https://api.polar.sh/checkout/cs_test_abc"}
    
    with patch(
        "backend.services.payments_mor.httpx.AsyncClient.post",
        AsyncMock(return_value=mock_response),
    ) as mock_post:
        response = client.post(
            "/api/payments/create-checkout",
            json={"vin": "1HGBH41JXMN109186", "symptoms": "rough idle", "price_type": "single"},
        )
        
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "live"
    assert data["checkout_url"] == "https://api.polar.sh/checkout/cs_test_abc"
    
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["product_id"] == settings.polar_product_id_tier_2
    assert call_kwargs["json"]["metadata"]["vin"] == "1HGBH41JXMN109186"


def test_create_checkout_attaches_user_id_from_bearer_token(client, monkeypatch):
    monkeypatch.setattr(settings, "polar_access_token", "pat_test_fake")
    token = create_access_token(data={"sub": "user-123"})
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"url": "https://api.polar.sh/checkout/cs_test_abc"}
    
    with patch(
        "backend.services.payments_mor.httpx.AsyncClient.post",
        AsyncMock(return_value=mock_response),
    ) as mock_post:
        response = client.post(
            "/api/payments/create-checkout",
            json={"vin": "1HGBH41JXMN109186", "symptoms": "rough idle", "price_type": "annual"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
    assert response.status_code == 200
    assert mock_post.call_args.kwargs["json"]["metadata"]["user_id"] == "user-123"
    assert mock_post.call_args.kwargs["json"]["product_id"] == settings.polar_product_id_annual


def test_create_checkout_returns_502_on_polar_failure(client, monkeypatch):
    monkeypatch.setattr(settings, "polar_access_token", "pat_test_fake")
    
    with patch(
        "backend.services.payments_mor.httpx.AsyncClient.post",
        AsyncMock(side_effect=RuntimeError("Polar is down")),
    ):
        response = client.post(
            "/api/payments/create-checkout",
            json={"vin": "1HGBH41JXMN109186", "symptoms": "rough idle", "price_type": "single"},
        )
        
    assert response.status_code == 502


def test_polar_webhook_accepts_validly_signed_event(client, monkeypatch, db_session):
    monkeypatch.setattr(settings, "polar_webhook_secret", "whsec_test_fake")
    
    # Pre-create user to verify link
    test_user = DbUser(id="user-123", email="webhook-test@example.com")
    db_session.merge(test_user)
    db_session.commit()

    payload = (
        b'{"event": "subscription.created", "data": {'
        b'"id": "sub_abc", "customer_id": "cust_123", "status": "active", '
        b'"current_period_end": "2027-07-15T09:00:00Z", '
        b'"metadata": {"user_id": "user-123"}}}'
    )
    signature = _sign_payload(payload, "whsec_test_fake")

    response = client.post(
        "/api/webhooks/payments",
        content=payload,
        headers={"Content-Type": "application/json", "x-polar-signature": signature},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "received"}
    
    # Reload and verify DB fields
    db_session.expire_all()
    user = db_session.query(DbUser).filter(DbUser.id == "user-123").first()
    assert user is not None
    assert user.subscription_status == "active"
    assert user.mor_customer_id == "cust_123"
    assert user.mor_subscription_id == "sub_abc"
    assert user.subscription_expires_at is not None


def test_webhook_rejects_an_invalid_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "polar_webhook_secret", "whsec_test_fake")
    payload = b'{"event": "subscription.created", "data": {}}'
    bad_signature = _sign_payload(payload, "wrong_secret")

    response = client.post(
        "/api/webhooks/payments",
        content=payload,
        headers={"Content-Type": "application/json", "x-polar-signature": bad_signature},
    )
    assert response.status_code == 401


def test_deprecated_stripe_webhook_returns_410(client):
    response = client.post(
        "/api/webhooks/stripe",
        json={"id": "evt_1"}
    )
    assert response.status_code == 410


def test_repair_rejects_a_fabricated_session_id_never_recorded_as_paid(client, db_session):
    """A client sending any non-empty stripe_session_id used to be enough to
    unlock a guide -- this is the exact "ephemeral localStorage" flaw
    imp.md Stage 1.3/1.4 requires fixing. A session_id that was never
    written by the webhook / success-stub must still be rejected."""
    db_session.query(DbGuideUnlock).filter(
        DbGuideUnlock.session_id == "cs_never_paid"
    ).delete()
    db_session.commit()

    response = client.post(
        "/api/repair",
        json={
            "vin": "1HGBH41JXMN109186",
            "symptoms": "rough idle",
            "stripe_session_id": "cs_never_paid",
        },
    )
    assert response.status_code == 402


def test_success_stub_records_unlock_that_then_authorizes_repair(client, db_session, monkeypatch):
    """The mock/dev checkout flow never fires a real webhook, so the
    success-stub redirect is the only place a single-incident "payment"
    completes -- it must itself record the server-side unlock."""
    from backend.routers import repair as repair_router

    db_session.query(DbGuideUnlock).filter(
        DbGuideUnlock.session_id == "cs_stub_flow"
    ).delete()
    db_session.commit()

    stub_response = client.get(
        "/api/payments/success-stub?session_id=cs_stub_flow&vin=1HGBH41JXMN109186&price_type=single",
        follow_redirects=False,
    )
    assert stub_response.status_code == 303

    monkeypatch.setattr(
        repair_router, "generate_repair_procedure",
        AsyncMock(return_value=(["Step 1"], ["Citation 1"])),
    )
    repair_response = client.post(
        "/api/repair",
        json={
            "vin": "1HGBH41JXMN109186",
            "vehicle": {"year": 2010, "make": "Honda", "model": "Civic"},
            "symptoms": "rough idle",
            "stripe_session_id": "cs_stub_flow",
        },
    )
    assert repair_response.status_code == 200


def test_webhook_checkout_created_alone_does_not_unlock(client, monkeypatch, db_session):
    """`checkout.created` only means the customer started checkout, not that
    payment succeeded -- it must not be enough to unlock a guide."""
    monkeypatch.setattr(settings, "polar_webhook_secret", "whsec_test_fake")
    db_session.query(DbGuideUnlock).filter(
        DbGuideUnlock.session_id == "co_unpaid"
    ).delete()
    db_session.commit()

    payload = (
        b'{"event": "checkout.created", "data": {'
        b'"id": "co_unpaid", "status": "open", '
        b'"metadata": {"vin": "1HGBH41JXMN109186", "price_type": "tier_1"}}}'
    )
    signature = _sign_payload(payload, "whsec_test_fake")
    response = client.post(
        "/api/webhooks/payments",
        content=payload,
        headers={"Content-Type": "application/json", "x-polar-signature": signature},
    )
    assert response.status_code == 200

    db_session.expire_all()
    assert (
        db_session.query(DbGuideUnlock)
        .filter(DbGuideUnlock.session_id == "co_unpaid")
        .first()
        is None
    )


def test_webhook_order_created_records_the_unlock(client, monkeypatch, db_session):
    """`order.created` is Polar's definitive completed-payment event and
    must record a server-side unlock keyed by the *checkout* id (what the
    frontend actually sends back to /api/repair), not the order's own id."""
    monkeypatch.setattr(settings, "polar_webhook_secret", "whsec_test_fake")
    db_session.query(DbGuideUnlock).filter(
        DbGuideUnlock.session_id == "co_paid_123"
    ).delete()
    db_session.commit()

    payload = (
        b'{"event": "order.created", "data": {'
        b'"id": "order_999", "checkout_id": "co_paid_123", '
        b'"metadata": {"vin": "1HGBH41JXMN109186", "price_type": "tier_2"}}}'
    )
    signature = _sign_payload(payload, "whsec_test_fake")
    response = client.post(
        "/api/webhooks/payments",
        content=payload,
        headers={"Content-Type": "application/json", "x-polar-signature": signature},
    )
    assert response.status_code == 200

    db_session.expire_all()
    unlock = (
        db_session.query(DbGuideUnlock)
        .filter(DbGuideUnlock.session_id == "co_paid_123")
        .first()
    )
    assert unlock is not None
    assert unlock.vin == "1HGBH41JXMN109186"
    assert unlock.price_type == "tier_2"


def test_webhook_annual_pass_checkout_does_not_record_a_vin_unlock(client, monkeypatch, db_session):
    """Annual pass access is gated on DbUser.subscription_status, not a
    per-VIN DbGuideUnlock row -- the webhook must not write one for it."""
    monkeypatch.setattr(settings, "polar_webhook_secret", "whsec_test_fake")
    db_session.query(DbGuideUnlock).filter(
        DbGuideUnlock.session_id == "co_annual_1"
    ).delete()
    db_session.commit()

    payload = (
        b'{"event": "order.created", "data": {'
        b'"id": "order_annual_1", "checkout_id": "co_annual_1", '
        b'"metadata": {"vin": "1HGBH41JXMN109186", "price_type": "annual"}}}'
    )
    signature = _sign_payload(payload, "whsec_test_fake")
    response = client.post(
        "/api/webhooks/payments",
        content=payload,
        headers={"Content-Type": "application/json", "x-polar-signature": signature},
    )
    assert response.status_code == 200

    db_session.expire_all()
    assert (
        db_session.query(DbGuideUnlock)
        .filter(DbGuideUnlock.session_id == "co_annual_1")
        .first()
        is None
    )
