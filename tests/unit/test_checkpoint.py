"""Unit tests for Stage 2.4: POST /api/repair/checkpoint/verify."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_checkpoint(
    client,
    file_bytes=b"fake-image-bytes",
    content_type="image/jpeg",
    step="Verify belt routing.",
):
    return client.post(
        "/api/repair/checkpoint/verify",
        files={"file": ("photo.jpg", file_bytes, content_type)},
        data={"step_description": step},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_checkpoint_verify_success_milestone_met(client, monkeypatch):
    """Happy path: Gemini says milestone is met."""
    from backend.services.gemini import CheckpointVerification

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    result = CheckpointVerification(
        is_milestone_met=True,
        confidence=0.92,
        explanation="Belt routing aligns with all four pulleys and tensioner.",
    )

    with patch("backend.services.gemini.get_genai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.parsed = result
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        resp = _post_checkpoint(client)

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_milestone_met"] is True
    assert 0.0 <= data["confidence"] <= 1.0
    assert "Belt routing" in data["explanation"]


def test_checkpoint_verify_success_milestone_not_met(client, monkeypatch):
    """Gemini flags the work as incorrect — still a 200, but is_milestone_met=False."""
    from backend.services.gemini import CheckpointVerification

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    result = CheckpointVerification(
        is_milestone_met=False,
        confidence=0.78,
        explanation="Belt is off the tensioner pulley — reseat before torquing.",
    )

    with patch("backend.services.gemini.get_genai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.parsed = result
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        resp = _post_checkpoint(client)

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_milestone_met"] is False
    assert "reseat" in data["explanation"]


def test_checkpoint_verify_rejects_invalid_mime(client):
    """Unsupported MIME type must be rejected (400 or 422 from FastAPI validation)."""
    resp = _post_checkpoint(client, file_bytes=b"data", content_type="application/pdf")
    # In some test environments FastAPI's multipart parser rejects the content-type
    # at the validation layer (422) before our handler can return 400. Both mean
    # the request was refused; we only care that it's not 2xx.
    assert resp.status_code in (400, 422), f"Expected 400/422, got {resp.status_code}"


def test_checkpoint_verify_rejects_empty_file(client, monkeypatch):
    """Empty upload should return 400."""
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    resp = _post_checkpoint(client, file_bytes=b"")
    assert resp.status_code == 400
    assert "empty" in resp.json()["error"].lower()


def test_checkpoint_verify_unavailable_without_gemini_key(client, monkeypatch):
    """No Gemini key configured → 503 Service Unavailable."""
    monkeypatch.setattr(settings, "gemini_api_key", None)

    resp = _post_checkpoint(client)
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["error"].lower()
