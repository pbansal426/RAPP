"""Unit tests for Stage 2.6: POST /api/diagnose/verify-external."""

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

SAMPLE_REQUEST = {
    "vin": "1HGBH41JXMN109186",
    "symptoms": "engine misfiring on cylinder 3",
    "external_ai_text": (
        "Replace the spark plug with a NGK BCPR6E, torque to 18 ft-lbs, "
        "and the issue should be resolved."
    ),
}

# retrieve is imported inside the function body via 'from backend.services.rag import retrieve'
# so we must patch the retriever at the services layer, not at the router level.
_RAG_PATCH_TARGET = "backend.rag.retriever.retrieve"


def _post_verify(client, payload=None):
    return client.post(
        "/api/diagnose/verify-external",
        json=payload or SAMPLE_REQUEST,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_verify_external_degraded_no_gemini_key(client, monkeypatch):
    """When Gemini key is absent the endpoint returns a 200 with score=50 (degraded mode)."""
    monkeypatch.setattr(settings, "gemini_api_key", None)

    with patch(_RAG_PATCH_TARGET, return_value=[]):
        resp = _post_verify(client)

    assert resp.status_code == 200
    data = resp.json()
    assert data["accuracy_score"] == 50
    assert len(data["missing_safety_warnings"]) > 0
    assert "unavailable" in data["missing_safety_warnings"][0].lower()


def test_verify_external_accurate_advice(client, monkeypatch):
    """When Gemini returns a high score no errors should be present."""
    from backend.services.gemini import ExternalAiVerificationSchema

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    gemini_result = ExternalAiVerificationSchema(
        verified_claims=["NGK BCPR6E is the correct OEM plug for this engine."],
        fitment_or_spec_errors=[],
        missing_safety_warnings=[],
        accuracy_score=95,
    )

    with patch(_RAG_PATCH_TARGET, return_value=[]):
        with patch("backend.services.gemini.get_genai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.parsed = gemini_result
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            resp = _post_verify(client)

    assert resp.status_code == 200
    data = resp.json()
    assert data["accuracy_score"] == 95
    assert data["fitment_or_spec_errors"] == []
    assert data["missing_safety_warnings"] == []
    assert len(data["verified_claims"]) > 0


def test_verify_external_inaccurate_advice_with_errors(client, monkeypatch):
    """Gemini returns errors and a low score for hallucinated advice."""
    from backend.services.gemini import ExternalAiVerificationSchema

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    gemini_result = ExternalAiVerificationSchema(
        verified_claims=[],
        fitment_or_spec_errors=[
            "Wrong torque spec: ChatGPT said 18 ft-lbs; OEM spec is 13 ft-lbs.",
            "NGK BCPR6E is not the OEM-specified plug; correct part is NGK IZFR6K11.",
        ],
        missing_safety_warnings=[
            "No mention of disconnecting the negative battery terminal."
        ],
        accuracy_score=28,
    )

    with patch(_RAG_PATCH_TARGET, return_value=[]):
        with patch("backend.services.gemini.get_genai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.parsed = gemini_result
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            resp = _post_verify(client)

    assert resp.status_code == 200
    data = resp.json()
    assert data["accuracy_score"] == 28
    assert len(data["fitment_or_spec_errors"]) == 2
    assert len(data["missing_safety_warnings"]) == 1


def test_verify_external_rate_limited_returns_429(client, monkeypatch):
    """Gemini quota exhaustion should propagate as 429, not 500."""
    from backend.services.gemini import GeminiRateLimitError

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    async def _raise(*args, **kwargs):
        raise GeminiRateLimitError("quota exceeded")

    with patch(_RAG_PATCH_TARGET, return_value=[]):
        with patch(
            "backend.routers.diagnose.call_gemini_verify_external",
            side_effect=_raise,
        ):
            resp = _post_verify(client)

    assert resp.status_code == 429
    assert "limit" in resp.json()["error"].lower()


def test_verify_external_gemini_failure_returns_degraded_200(client, monkeypatch):
    """Non-rate-limit Gemini failure returns degraded 200, not 500."""
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    with patch(_RAG_PATCH_TARGET, return_value=[]):
        with patch(
            "backend.routers.diagnose.call_gemini_verify_external",
            return_value=None,
        ):
            resp = _post_verify(client)

    assert resp.status_code == 200
    data = resp.json()
    assert data["accuracy_score"] == 50
    assert "unavailable" in data["missing_safety_warnings"][0].lower()


def test_verify_external_uses_rag_context(client, monkeypatch):
    """RAG retrieval results are passed through to Gemini (context enrichment)."""
    from backend.services.gemini import ExternalAiVerificationSchema

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    rag_docs = [
        {"text": "OEM torque spec for spark plug: 13 ft-lbs (17.5 Nm).", "source": "TSB-2019-001"},
    ]
    gemini_result = ExternalAiVerificationSchema(
        verified_claims=[],
        fitment_or_spec_errors=["Wrong torque: 18 ft-lbs stated; OEM is 13 ft-lbs."],
        missing_safety_warnings=[],
        accuracy_score=60,
    )

    captured_calls: list[dict] = []

    async def _fake_gemini(external_ai_text, rag_context, symptoms):
        captured_calls.append({"rag_context": rag_context, "symptoms": symptoms})
        return gemini_result

    with patch(_RAG_PATCH_TARGET, return_value=rag_docs):
        with patch(
            "backend.routers.diagnose.call_gemini_verify_external",
            side_effect=_fake_gemini,
        ):
            resp = _post_verify(client)

    assert resp.status_code == 200
    assert len(captured_calls) == 1
    # Confirm OEM context was injected into the call
    assert "OEM torque spec" in captured_calls[0]["rag_context"]
