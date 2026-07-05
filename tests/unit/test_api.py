from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app, settings


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def _extended_vin_payload(**overrides):
    payload = {
        "ModelYear": "2018",
        "Make": "HONDA",
        "Model": "CIVIC",
        "Trim": "EX",
        "BodyClass": "Sedan/Saloon",
        "VehicleType": "PASSENGER CAR",
        "DisplacementL": "1.5",
        "EngineCylinders": "4",
        "EngineConfiguration": "Inline",
        "DriveType": "FWD",
        "FuelTypePrimary": "Gasoline",
        "FuelTypeSecondary": "",
        "ElectrificationLevel": "",
    }
    payload.update(overrides)
    return payload


@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_vin_decoding_success(mock_get, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Results": [_extended_vin_payload()]}
    mock_get.return_value = mock_response

    response = client.get("/api/vin/1HGBH41JXMN109186")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2018
    assert data["make"] == "HONDA"
    assert data["model"] == "CIVIC"
    assert data["trim"] == "EX"
    assert data["body_class"] == "Sedan/Saloon"
    assert data["engine"] == "1.5L I4"
    assert data["drive_type"] == "FWD"
    assert data["powertrain"] == "Gasoline"

    # User-Agent header must be sent — some upstream NHTSA edge nodes reject
    # requests with no User-Agent at all.
    _, call_kwargs = mock_get.call_args
    assert "User-Agent" in call_kwargs["headers"]


@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_vin_decoding_powertrain_electric(mock_get, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Results": [
            _extended_vin_payload(
                Make="TESLA",
                Model="MODEL 3",
                FuelTypePrimary="Electric",
                ElectrificationLevel="BEV - Battery Electric Vehicle (BEV)",
            )
        ]
    }
    mock_get.return_value = mock_response

    response = client.get("/api/vin/5YJ3E1EA1KF000001")
    assert response.status_code == 200
    assert response.json()["powertrain"] == "Electric (EV)"


@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_vin_decoding_powertrain_plugin_hybrid(mock_get, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Results": [
            _extended_vin_payload(
                Make="TOYOTA",
                Model="RAV4 PRIME",
                FuelTypePrimary="Gasoline",
                FuelTypeSecondary="Electric",
                ElectrificationLevel="PHEV - Plug-in Hybrid Electric Vehicle",
            )
        ]
    }
    mock_get.return_value = mock_response

    response = client.get("/api/vin/JTMAB3FV0LD000001")
    assert response.status_code == 200
    assert response.json()["powertrain"] == "Plug-in Hybrid"


@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_vin_decoding_retries_then_succeeds(mock_get, client):
    import httpx

    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.json.return_value = {"Results": [_extended_vin_payload()]}
    mock_get.side_effect = [httpx.ConnectError("transient"), ok_response]

    response = client.get("/api/vin/1HGBH41JXMN109186")
    assert response.status_code == 200
    assert response.json()["make"] == "HONDA"
    assert mock_get.call_count == 2

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
        "Results": [_extended_vin_payload(Make="", Model="")]
    }
    mock_get.return_value = mock_response

    response = client.get("/api/vin/1HGBH41JXMN109186")
    assert response.status_code == 404
    assert "make or model not found" in response.json()["error"]

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_vin_decoding_api_error(mock_get, client):
    import httpx
    mock_get.side_effect = httpx.ConnectError("Connection timed out")

    # 1HG has a known WMI (Honda), so this now degrades to the offline
    # fallback decode instead of a hard 502 -- see test below for the
    # unknown-WMI case where 502 is still the right outcome.
    response = client.get("/api/vin/1HGBH41JXMN109186")
    assert response.status_code == 200
    assert response.json()["make"] == "HONDA"
    assert response.json()["decode_source"] == "offline_fallback"

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_vin_decoding_api_error_unknown_wmi_returns_502(mock_get, client):
    import httpx
    mock_get.side_effect = httpx.ConnectError("Connection timed out")

    # WVW (Volkswagen) isn't in the offline fallback table, so this must
    # still surface a clear 502 rather than silently guessing a make.
    response = client.get("/api/vin/WVWZZZ1JZXW000001")
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

def test_diagnose_gemini_enhancement(client, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    mock_response = MagicMock()
    mock_response.text = (
        "Likely a worn brake pad. Immediate risk is reduced stopping power."
    )
    mock_generate_content = AsyncMock(return_value=mock_response)

    with patch("backend.services.gemini.get_genai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = mock_generate_content
        mock_get_client.return_value = mock_client

        payload = {
            "vin": "1HGBH41JXMN109186",
            "symptoms": "Squeaking sound when braking",
            "obd_codes": "P0101",
            "tools": ["basic wrenches"],
        }
        response = client.post("/api/diagnose", json=payload)

    assert response.status_code == 200
    assert response.json()["summary"] == "Likely a worn brake pad. Immediate risk is reduced stopping power."
    mock_generate_content.assert_called_once()
    assert mock_generate_content.call_args.kwargs["model"] == "gemini-3.5-flash"

def test_diagnose_gemini_failure_falls_back_to_default_summary(client, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    with patch("backend.services.gemini.get_genai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=Exception("quota exceeded")
        )
        mock_get_client.return_value = mock_client

        payload = {
            "vin": "1HGBH41JXMN109186",
            "symptoms": "Squeaking sound when braking",
            "obd_codes": "P0101",
            "tools": ["basic wrenches"],
        }
        response = client.post("/api/diagnose", json=payload)

    assert response.status_code == 200
    assert "Misfire or other symptom detected" in response.json()["summary"]

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
    mock_decode_resp.json.return_value = {"Results": [_extended_vin_payload()]}
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
    mock_decode_resp.json.return_value = {"Results": [_extended_vin_payload()]}
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

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("backend.rag.retriever.retrieve")
def test_repair_gemini_structured_steps(mock_retrieve, mock_get, client, monkeypatch):
    from backend.services.gemini import RepairStep, RepairStepsSchema

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    mock_decode_resp = MagicMock()
    mock_decode_resp.status_code = 200
    mock_decode_resp.json.return_value = {"Results": [_extended_vin_payload()]}
    mock_get.return_value = mock_decode_resp
    mock_retrieve.return_value = []

    mock_response = MagicMock()
    mock_response.parsed = RepairStepsSchema(
        steps=[
            RepairStep(text="Disconnect the negative battery terminal.", is_torque_spec=False),
            RepairStep(text="the mounting bolt to 7.5 ft-lbs.", is_torque_spec=True),
        ]
    )
    mock_generate_content = AsyncMock(return_value=mock_response)

    with patch("backend.services.gemini.get_genai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = mock_generate_content
        mock_get_client.return_value = mock_client

        payload = {
            "vin": "1HGBH41JXMN109186",
            "symptoms": "Unknown weird noise",
            "stripe_session_id": "cs_test_123",
        }
        response = client.post("/api/repair", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["repair_steps"] == [
        "Disconnect the negative battery terminal.",
        "Torque the mounting bolt to 7.5 ft-lbs.",
    ]
    assert mock_generate_content.call_args.kwargs["model"] == "gemini-3.5-flash"
    config = mock_generate_content.call_args.kwargs["config"]
    assert config.response_schema is RepairStepsSchema

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("backend.rag.retriever.retrieve")
def test_repair_gemini_failure_falls_back_to_template(
    mock_retrieve, mock_get, client, monkeypatch
):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    mock_decode_resp = MagicMock()
    mock_decode_resp.status_code = 200
    mock_decode_resp.json.return_value = {"Results": [_extended_vin_payload()]}
    mock_get.return_value = mock_decode_resp
    mock_retrieve.return_value = []

    with patch("backend.services.gemini.get_genai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("quota exceeded"))
        mock_get_client.return_value = mock_client

        payload = {
            "vin": "1HGBH41JXMN109186",
            "symptoms": "Unknown weird noise",
            "stripe_session_id": "cs_test_123",
        }
        response = client.post("/api/repair", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "Disconnect negative battery terminal." in data["repair_steps"]

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


def test_diagnose_includes_recommended_parts_and_cost_breakdown(client):
    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "Engine shaking at idle",
        "obd_codes": ["P0301"],
        "tools": [],
        "vehicle": {"year": 2018, "make": "HONDA", "model": "CIVIC"},
    }
    response = client.post("/api/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert len(data["recommended_parts"]) > 0
    part = data["recommended_parts"][0]
    assert part["part_name"]
    tiers = {opt["tier"] for opt in part["options"]}
    assert tiers == {"OEM", "Aftermarket / Budget", "Upgrade"}
    for opt in part["options"]:
        assert opt["purchase_url"].startswith("https://")

    breakdown = data["cost_breakdown"]
    assert breakdown["parts_total"] > 0
    assert breakdown["diy_total"] == round(4.00 + breakdown["parts_total"], 2)
    assert breakdown["dealership_cost_range"][0] > breakdown["independent_shop_range"][0]


def test_diagnose_no_template_match_has_empty_parts(client):
    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "purple unicorn glitter engine",
        "obd_codes": [],
        "tools": [],
    }
    response = client.post("/api/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["recommended_parts"] == []
    assert data["cost_breakdown"]["parts_total"] == 0.0
    assert data["cost_breakdown"]["diy_total"] == 4.00


# --- VIN photo OCR (/api/vin/ocr) ---

def test_vin_ocr_rejects_unsupported_content_type(client):
    response = client.post(
        "/api/vin/ocr",
        files={"file": ("vin.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported image type" in response.json()["error"]


def test_vin_ocr_rejects_empty_file(client):
    response = client.post(
        "/api/vin/ocr",
        files={"file": ("vin.jpg", b"", "image/jpeg")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["error"].lower()


def test_vin_ocr_unavailable_without_gemini_key(client, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    response = client.post(
        "/api/vin/ocr",
        files={"file": ("vin.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert response.status_code == 503
    assert "manually" in response.json()["error"].lower()


@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_vin_ocr_success(mock_get, client, monkeypatch):
    from backend.services.gemini import VinOcrExtraction

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    vision_resp = MagicMock()
    vision_resp.parsed = VinOcrExtraction(vin="1HGBH41JXMN109186", confidence=0.95)
    mock_generate_content = AsyncMock(return_value=vision_resp)

    decode_resp = MagicMock()
    decode_resp.status_code = 200
    decode_resp.json.return_value = {"Results": [_extended_vin_payload()]}
    mock_get.return_value = decode_resp

    with patch("backend.services.gemini.get_genai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = mock_generate_content
        mock_get_client.return_value = mock_client

        response = client.post(
            "/api/vin/ocr",
            files={"file": ("vin.jpg", b"fake-image-bytes", "image/jpeg")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["vin"] == "1HGBH41JXMN109186"
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["decoded_vehicle"]["make"] == "HONDA"


def test_vin_ocr_no_readable_vin_returns_422(client, monkeypatch):
    from backend.services.gemini import VinOcrExtraction

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    vision_resp = MagicMock()
    vision_resp.parsed = VinOcrExtraction(vin="", confidence=0.0)
    mock_generate_content = AsyncMock(return_value=vision_resp)

    with patch("backend.services.gemini.get_genai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = mock_generate_content
        mock_get_client.return_value = mock_client

        response = client.post(
            "/api/vin/ocr",
            files={"file": ("vin.jpg", b"fake-image-bytes", "image/jpeg")},
        )
    assert response.status_code == 422


def test_sanitize_and_check_digit_helpers():
    from backend.routers.vin import _sanitize_vin_candidate, _vin_check_digit_valid

    assert _sanitize_vin_candidate(" 1hgb h41j-xmn109186 ") == "1HGBH41JXMN109186"
    # 1HGBH41JXMN109186 is a real, check-digit-valid Honda VIN.
    assert _vin_check_digit_valid("1HGBH41JXMN109186") is True
    assert _vin_check_digit_valid("1HGBH41JXMN109187") is False

