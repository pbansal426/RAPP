import hashlib
import hmac
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.core.security import create_access_token
from backend.main import app, settings


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _sign_payload(payload: bytes, secret: str) -> str:
    """Builds a real Stripe-format signature header (t=...,v1=...) so tests
    exercise actual HMAC verification, not a mocked stand-in for it."""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload.decode()}"
    signature = hmac.new(
        secret.encode(), signed_payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def test_create_checkout_falls_back_to_mock_when_unconfigured(client):
    assert not settings.stripe_secret_key
    response = client.post(
        "/api/payments/create-checkout",
        json={"vin": "1HGBH41JXMN109186", "symptoms": "rough idle"},
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "mock"


def test_create_checkout_uses_real_stripe_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    fake_session = MagicMock(url="https://checkout.stripe.com/c/pay/cs_test_abc")

    with patch(
        "backend.services.stripe.stripe.checkout.Session.create_async",
        AsyncMock(return_value=fake_session),
    ) as mock_create:
        response = client.post(
            "/api/payments/create-checkout",
            json={"vin": "1HGBH41JXMN109186", "symptoms": "rough idle"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "live"
    assert data["checkout_url"] == "https://checkout.stripe.com/c/pay/cs_test_abc"

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["metadata"]["vin"] == "1HGBH41JXMN109186"
    assert call_kwargs["metadata"]["symptoms"] == "rough idle"
    assert call_kwargs["metadata"]["user_id"] == ""  # no Authorization header sent


def test_create_checkout_attaches_user_id_from_bearer_token(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    fake_session = MagicMock(url="https://checkout.stripe.com/c/pay/cs_test_abc")
    token = create_access_token(data={"sub": "user-123"})

    with patch(
        "backend.services.stripe.stripe.checkout.Session.create_async",
        AsyncMock(return_value=fake_session),
    ) as mock_create:
        response = client.post(
            "/api/payments/create-checkout",
            json={"vin": "1HGBH41JXMN109186", "symptoms": "rough idle"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert mock_create.call_args.kwargs["metadata"]["user_id"] == "user-123"


def test_create_checkout_returns_502_on_stripe_failure(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")

    with patch(
        "backend.services.stripe.stripe.checkout.Session.create_async",
        AsyncMock(side_effect=RuntimeError("stripe is down")),
    ):
        response = client.post(
            "/api/payments/create-checkout",
            json={"vin": "1HGBH41JXMN109186", "symptoms": "rough idle"},
        )

    assert response.status_code == 502


def test_webhook_accepts_a_validly_signed_event(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_fake")
    payload = (
        b'{"id": "evt_1", "type": "checkout.session.completed", '
        b'"data": {"object": {"id": "cs_test_abc", '
        b'"metadata": {"vin": "1HGBH41JXMN109186", "user_id": "user-123"}}}}'
    )
    signature = _sign_payload(payload, "whsec_test_fake")

    response = client.post(
        "/api/webhooks/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "stripe-signature": signature},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "received"}


def test_webhook_rejects_an_invalid_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_fake")
    payload = b'{"id": "evt_1", "type": "checkout.session.completed"}'
    bad_signature = _sign_payload(payload, "wrong_secret")

    response = client.post(
        "/api/webhooks/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "stripe-signature": bad_signature},
    )
    assert response.status_code == 400


def test_webhook_rejects_a_missing_signature_header(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_fake")
    response = client.post(
        "/api/webhooks/stripe",
        content=b'{"id": "evt_1", "type": "checkout.session.completed"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
