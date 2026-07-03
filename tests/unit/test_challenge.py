import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from backend.main import app, settings
from tests.unit.test_api import _extended_vin_payload

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# 1. Test /api/repair with valid Stripe session ID and various RAG outputs

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("backend.rag.retriever.retrieve")
def test_repair_symptom_only_no_obd_codes(mock_retrieve, mock_get, client):
    """
    Test when obd_codes is missing from the payload.
    Expected: The server should gracefully handle the missing field (normalize to empty list) and not crash.
    """
    mock_decode_resp = MagicMock()
    mock_decode_resp.status_code = 200
    mock_decode_resp.json.return_value = {"Results": [_extended_vin_payload()]}
    mock_get.return_value = mock_decode_resp
    mock_retrieve.return_value = []

    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "spark plug replacement",
        "stripe_session_id": "cs_test_123"
        # obd_codes is missing!
    }

    response = client.post("/api/repair", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Disconnect negative battery terminal." in data["repair_steps"]

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("backend.rag.retriever.retrieve")
def test_repair_rag_returns_none(mock_retrieve, mock_get, client):
    """
    Test when RAG retrieve returns None.
    Expected: The server should gracefully fall back to the default/Honda steps.
    """
    mock_decode_resp = MagicMock()
    mock_decode_resp.status_code = 200
    mock_decode_resp.json.return_value = {"Results": [_extended_vin_payload()]}
    mock_get.return_value = mock_decode_resp
    
    mock_retrieve.return_value = None

    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "spark plug replacement",
        "obd_codes": [],
        "stripe_session_id": "cs_test_123"
    }

    response = client.post("/api/repair", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Disconnect negative battery terminal." in data["repair_steps"]
    assert "Honda Civic ESM 2016-2021 Section 12-4" in data["citations"]

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("backend.rag.retriever.retrieve")
def test_repair_rag_returns_empty_list(mock_retrieve, mock_get, client):
    """
    Test when RAG retrieve returns an empty list.
    Expected: The server should gracefully fall back to the default/Honda steps.
    """
    mock_decode_resp = MagicMock()
    mock_decode_resp.status_code = 200
    mock_decode_resp.json.return_value = {"Results": [_extended_vin_payload()]}
    mock_get.return_value = mock_decode_resp
    
    mock_retrieve.return_value = []

    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "spark plug replacement",
        "obd_codes": [],
        "stripe_session_id": "cs_test_123"
    }

    response = client.post("/api/repair", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Disconnect negative battery terminal." in data["repair_steps"]
    assert "Honda Civic ESM 2016-2021 Section 12-4" in data["citations"]

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("backend.rag.retriever.retrieve")
def test_repair_rag_missing_metadata_key(mock_retrieve, mock_get, client):
    """
    Test when RAG returns documents that are missing the 'metadata' key entirely.
    Expected: The server should gracefully use default/fallback info (e.g. VIN meta) for the citation.
    """
    mock_decode_resp = MagicMock()
    mock_decode_resp.status_code = 200
    mock_decode_resp.json.return_value = {"Results": [_extended_vin_payload()]}
    mock_get.return_value = mock_decode_resp
    
    mock_retrieve.return_value = [
        {
            "id": "doc_1",
            "text": "Clean the area around the spark plug.",
            # metadata key is completely missing!
        }
    ]

    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "spark plug replacement",
        "obd_codes": [],
        "stripe_session_id": "cs_test_123"
    }

    response = client.post("/api/repair", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["repair_steps"] == ["Clean the area around the spark plug."]
    assert data["citations"] == ["HONDA CIVIC Manual (2018)"]

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("backend.rag.retriever.retrieve")
def test_repair_rag_metadata_none(mock_retrieve, mock_get, client):
    """
    Test when RAG returns documents where the 'metadata' key is explicitly None.
    Expected: The server should handle NoneType metadata gracefully and not crash.
    """
    mock_decode_resp = MagicMock()
    mock_decode_resp.status_code = 200
    mock_decode_resp.json.return_value = {"Results": [_extended_vin_payload()]}
    mock_get.return_value = mock_decode_resp
    
    mock_retrieve.return_value = [
        {
            "id": "doc_1",
            "text": "Clean the area around the spark plug.",
            "metadata": None  # Explicitly None
        }
    ]

    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "spark plug replacement",
        "obd_codes": [],
        "stripe_session_id": "cs_test_123"
    }

    response = client.post("/api/repair", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["repair_steps"] == ["Clean the area around the spark plug."]
    assert data["citations"] == ["HONDA CIVIC Manual (2018)"]

# Test for /api/diagnose when obd_codes is missing from the payload
def test_diagnose_no_obd_codes(client):
    """
    Test when obd_codes is missing from the /api/diagnose payload.
    Expected: The server should handle the missing field gracefully and not crash.
    """
    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "Squeaking sound when breaking"
        # obd_codes is missing!
    }
    response = client.post("/api/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Misfire or other symptom detected" in data["summary"]


# 2. Validate success-stub redirects correctly with all query params intact, and uses 303 or 307

def test_success_stub_redirect_status_code(client):
    """
    Validate that success-stub redirects using HTTP status 303 or 307.
    """
    response = client.get("/api/payments/success-stub?session_id=cs_test_123&vin=1HGBH41JXMN109186", follow_redirects=False)
    assert response.status_code in (303, 307)

def test_success_stub_redirect_retains_all_query_params(client):
    """
    Validate that success-stub redirects with all query params intact, including extra parameters.
    """
    response = client.get("/api/payments/success-stub?session_id=cs_test_123&vin=1HGBH41JXMN109186&promo=SAVE10&referrer=google", follow_redirects=False)
    location = response.headers.get("location", "")
    assert f"session_id=cs_test_123" in location
    assert f"vin=1HGBH41JXMN109186" in location
    assert "promo=SAVE10" in location
    assert "referrer=google" in location


# 3. Test /api/payments/webhook with various payload structures (including malformed JSON)

def test_webhook_valid_payload(client):
    """
    Validate webhook returns HTTP 200/400 for standard JSON.
    """
    response = client.post("/api/payments/webhook", json={"id": "evt_1", "type": "checkout.session.completed"})
    assert response.status_code in (200, 400)
    if response.status_code == 200:
        assert response.json() == {"status": "received"}

def test_webhook_empty_payload(client):
    """
    Validate webhook returns HTTP 200/400 for empty body.
    """
    response = client.post("/api/payments/webhook")
    assert response.status_code in (200, 400)

def test_webhook_malformed_json(client):
    """
    Validate webhook returns HTTP 200/400 and doesn't crash the app for malformed JSON.
    """
    headers = {"Content-Type": "application/json"}
    response = client.post("/api/payments/webhook", content="{'invalid_json': ", headers=headers)
    assert response.status_code in (200, 400)
