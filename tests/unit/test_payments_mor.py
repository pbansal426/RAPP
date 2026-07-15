from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.core.config import settings
from backend.pricing import estimate_pricing
from backend.services.payments_mor import (
    polar_is_configured,
    build_mock_checkout_url,
    build_success_redirect_url,
    create_polar_checkout_session,
    verify_webhook_signature,
    parse_date,
)


def test_pricing_intervals():
    # Tier 1 ($4.99): dealer quote < $150
    assert estimate_pricing(None, 149.99) == 4.99
    assert estimate_pricing(None, 50.0) == 4.99
    
    # Tier 2 ($9.99): dealer quote $150 - $600
    assert estimate_pricing(None, 150.0) == 9.99
    assert estimate_pricing(None, 400.0) == 9.99
    assert estimate_pricing(None, 600.0) == 9.99
    
    # Tier 3 ($14.99): dealer quote > $600
    assert estimate_pricing(None, 600.01) == 14.99
    assert estimate_pricing(None, 1000.0) == 14.99


def test_polar_configuration(monkeypatch):
    monkeypatch.setattr(settings, "polar_access_token", None)
    assert not polar_is_configured()
    
    monkeypatch.setattr(settings, "polar_access_token", "some_token")
    assert polar_is_configured()


def test_build_mock_checkout_url():
    url = build_mock_checkout_url("123", "annual")
    assert "session_id=cs_test_123" in url
    assert "vin=123" in url
    assert "price_type=annual" in url


def test_build_success_redirect_url():
    url = build_success_redirect_url("session_123", "vin_abc", {"price_type": "single"})
    assert "session_id=session_123" in url
    assert "vin=vin_abc" in url
    assert "price_type=single" in url


def test_verify_webhook_signature(monkeypatch):
    monkeypatch.setattr(settings, "polar_webhook_secret", "secret_key")
    payload = b"test_payload"
    
    # Correct signature
    import hmac
    import hashlib
    mac = hmac.new(b"secret_key", payload, hashlib.sha256)
    valid_sig = f"sha256={mac.hexdigest()}"
    
    assert verify_webhook_signature(payload, valid_sig)
    assert verify_webhook_signature(payload, mac.hexdigest()) # without prefix
    assert not verify_webhook_signature(payload, "invalid_sig")


def test_parse_date():
    # Int timestamp
    dt = parse_date(1689408000)
    assert isinstance(dt, datetime)
    assert dt.year == 2023
    
    # ISO string
    dt_str = parse_date("2026-07-15T09:00:00Z")
    assert isinstance(dt_str, datetime)
    assert dt_str.year == 2026
    
    # Invalid formats
    assert parse_date(None) is None
    assert parse_date("invalid_date") is None


@pytest.mark.asyncio
async def test_create_polar_checkout_session_mock(monkeypatch):
    monkeypatch.setattr(settings, "polar_access_token", None)
    url = await create_polar_checkout_session("vin_test", "annual", "engine light", "user-1")
    assert "success-stub" in url
    assert "price_type=annual" in url


@pytest.mark.asyncio
async def test_create_polar_checkout_session_live(monkeypatch):
    monkeypatch.setattr(settings, "polar_access_token", "token_123")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"url": "https://api.polar.sh/checkout/live_session"}
    
    with patch(
        "backend.services.payments_mor.httpx.AsyncClient.post",
        AsyncMock(return_value=mock_response)
    ) as mock_post:
        url = await create_polar_checkout_session("vin_test", "single", "brakes grinding", "user-1")
        
    assert url == "https://api.polar.sh/checkout/live_session"
    mock_post.assert_called_once()
    
    # Verify dynamic tier resolution for "single"
    # brakes grinding maps to brakes template which has parts total + labor, causing a dealership cost estimate.
    # It should fall into one of the pricing tiers. Let's make sure it was mapped to a product ID.
    payload = mock_post.call_args.kwargs["json"]
    assert "product_id" in payload
    assert payload["metadata"]["vin"] == "vin_test"
    assert payload["metadata"]["price_type"] in ("tier_1", "tier_2", "tier_3")
