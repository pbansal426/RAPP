import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from backend.main import app, settings

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_vin_decoding_success(mock_get, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Results": [
            {"Variable": "Model Year", "Value": "2018"},
            {"Variable": "Make", "Value": "HONDA"},
            {"Variable": "Model", "Value": "CIVIC"},
            {"Variable": "Displacement (L)", "Value": "1.5"},
            {"Variable": "Engine Number of Cylinders", "Value": "4"},
            {"Variable": "Drive Type", "Value": "FWD"},
        ]
    }
    mock_get.return_value = mock_response

    response = client.get("/api/vin/1HGBH41JXMN109186")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2018
    assert data["make"] == "HONDA"
    assert data["model"] == "CIVIC"
    assert data["engine"] == "1.5L 4 Cylinders"
    assert data["drive_type"] == "FWD"

def test_vin_decoding_invalid_format(client):
    # Short VIN
    response = client.get("/api/vin/1HGB")
    assert response.status_code == 400
    assert "Invalid VIN" in response.json()["error"]

    # Non-alphanumeric VIN
    response = client.get("/api/vin/1HGBH41JXMN10918@")
    assert response.status_code == 400
    assert "Invalid VIN" in response.json()["error"]

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_vin_decoding_not_found(mock_get, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Results": [
            {"Variable": "Model Year", "Value": "2018"},
            {"Variable": "Make", "Value": ""},
            {"Variable": "Model", "Value": ""},
        ]
    }
    mock_get.return_value = mock_response

    response = client.get("/api/vin/1HGBH41JXMN109186")
    assert response.status_code == 404
    assert "make or model not found" in response.json()["error"]

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_vin_decoding_api_error(mock_get, client):
    import httpx
    mock_get.side_effect = httpx.ConnectError("Connection timed out")

    response = client.get("/api/vin/1HGBH41JXMN109186")
    assert response.status_code == 502
    assert "Error communicating with NHTSA API" in response.json()["error"]

def test_diagnose_low_risk(client):
    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "Squeaking sound when breaking",
        "obd_codes": "P0101",
        "tools": ["basic wrenches"]
    }
    response = client.post("/api/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_high_risk"] is False
    assert data["high_risk_system"] is None
    assert data["warning_message"] is None
    assert "Misfire or other symptom detected" in data["summary"]

def test_diagnose_high_risk_airbag(client):
    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "airbag light is flashing on the dashboard",
        "obd_codes": ["B1001"],
        "tools": []
    }
    response = client.post("/api/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_high_risk"] is True
    assert data["high_risk_system"] == "Airbag/SRS"
    assert "SRS / Airbag systems are explosive" in data["warning_message"]

def test_diagnose_high_risk_ev_battery(client):
    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "hybrid battery cell imbalance detected",
        "obd_codes": [],
        "tools": []
    }
    response = client.post("/api/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_high_risk"] is True
    assert data["high_risk_system"] == "EV Battery"
    assert "High-voltage EV/hybrid battery systems carry lethal voltage" in data["warning_message"]

def test_diagnose_high_risk_fuel_line(client):
    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "Strong gasoline smell near the engine bay, possible fuel line leak",
        "obd_codes": [],
        "tools": []
    }
    response = client.post("/api/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_high_risk"] is True
    assert data["high_risk_system"] == "Fuel Line"
    assert "Pressurized fuel lines are highly flammable" in data["warning_message"]

def test_repair_missing_payment(client):
    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "Squeaking sound",
        "stripe_session_id": ""
    }
    response = client.post("/api/repair", json=payload)
    assert response.status_code == 402
    assert "Payment Required" in response.json()["error"]

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("backend.rag.retriever.retrieve")
def test_repair_with_rag_results(mock_retrieve, mock_get, client):
    # Setup mock VIN Decode
    mock_decode_resp = MagicMock()
    mock_decode_resp.status_code = 200
    mock_decode_resp.json.return_value = {
        "Results": [
            {"Variable": "Model Year", "Value": "2018"},
            {"Variable": "Make", "Value": "HONDA"},
            {"Variable": "Model", "Value": "CIVIC"},
        ]
    }
    mock_get.return_value = mock_decode_resp

    # Setup RAG mock
    mock_retrieve.return_value = [
        {
            "id": "doc_test_1",
            "text": "1. Remove the air filter box. 2. Loosen the spark plug using standard spark plug socket.",
            "metadata": {"citation": "Honda Civic Service Manual 2018 Section 5"},
            "distance": 0.1
        }
    ]

    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "spark plug replacement",
        "stripe_session_id": "cs_test_123"
    }

    response = client.post("/api/repair", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["repair_steps"]) == 1
    assert "Remove the air filter box" in data["repair_steps"][0]
    assert data["citations"] == ["Honda Civic Service Manual 2018 Section 5"]

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("backend.rag.retriever.retrieve")
def test_repair_fallback(mock_retrieve, mock_get, client):
    # Setup mock VIN Decode
    mock_decode_resp = MagicMock()
    mock_decode_resp.status_code = 200
    mock_decode_resp.json.return_value = {
        "Results": [
            {"Variable": "Model Year", "Value": "2018"},
            {"Variable": "Make", "Value": "HONDA"},
            {"Variable": "Model", "Value": "CIVIC"},
        ]
    }
    mock_get.return_value = mock_decode_resp

    # Setup RAG returning empty results
    mock_retrieve.return_value = []

    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "Unknown weird noise",
        "stripe_session_id": "cs_test_123"
    }

    response = client.post("/api/repair", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Disconnect negative battery terminal." in data["repair_steps"]
    assert "Honda Civic ESM 2016-2021 Section 12-4" in data["citations"]

def test_create_checkout(client):
    payload = {
        "vin": "1HGBH41JXMN109186",
        "price_type": "single"
    }
    response = client.post("/api/payments/create-checkout", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "checkout_url" in data
    assert "success-stub" in data["checkout_url"]
    assert "vin=1HGBH41JXMN109186" in data["checkout_url"]

def test_success_stub(client):
    # Redirects back to frontend with parameters
    response = client.get("/api/payments/success-stub?session_id=cs_test_123&vin=1HGBH41JXMN109186", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"{settings.frontend_url}/repair/success?session_id=cs_test_123&vin=1HGBH41JXMN109186"

def test_payments_webhook(client):
    response = client.post("/api/payments/webhook")
    assert response.status_code == 200
    assert response.json() == {"status": "received"}


def test_synthetic_vin_decoding_success(client):
    # Test Honda synthetic VIN
    response = client.get("/api/vin/SYN23HONDAACCORDX")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2023
    assert data["make"] == "HONDA"
    assert data["model"] == "ACCORD"
    assert data["engine"] == "1.5L 4-Cylinder"
    assert data["drive_type"] == "FWD"

    # Test Ford synthetic VIN (mixed case)
    response = client.get("/api/vin/syn26fordxf150xxx")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2026
    assert data["make"] == "FORD"
    assert data["model"] == "F-150"
    assert data["engine"] == "3.5L V6"
    assert data["drive_type"] == "AWD"


def test_synthetic_vin_decoding_errors(client):
    # Invalid make code
    response = client.get("/api/vin/SYN23ZZZZZACCORDX")
    assert response.status_code == 404
    assert "make not found" in response.json()["error"].lower()

    # Invalid model code
    response = client.get("/api/vin/SYN23HONDABIGCARS")
    assert response.status_code == 404
    assert "model not found" in response.json()["error"].lower()

    # Invalid length (18 chars)
    response = client.get("/api/vin/SYN23HONDAACCORDXX")
    assert response.status_code == 400
    assert "invalid vin format" in response.json()["error"].lower()

    # Invalid year format
    response = client.get("/api/vin/SYNXXHONDAACCORDX")
    assert response.status_code == 400
    assert "invalid year format" in response.json()["error"].lower()

