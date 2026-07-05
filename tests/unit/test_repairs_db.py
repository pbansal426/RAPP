import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import get_db
from backend.core.models import Base
from backend.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def _auth_headers(client, email="repairs@example.com", password="hunter2"):
    signup = client.post("/api/auth/signup", json={"email": email, "password": password})
    token = signup.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_save_repair_requires_auth(client):
    # HTTPBearer's auto_error dependency rejects a missing Authorization
    # header with 403 before our route code runs.
    response = client.post(
        "/api/repairs", json={"vin": "1HGBH41JXMN109186", "symptoms": "misfire"}
    )
    assert response.status_code == 403


def test_list_repairs_requires_auth(client):
    response = client.get("/api/repairs")
    assert response.status_code == 403


def test_save_and_list_repair(client):
    headers = _auth_headers(client)

    save_resp = client.post(
        "/api/repairs",
        json={
            "vin": "1HGBH41JXMN109186",
            "year": "2018",
            "make": "HONDA",
            "model": "CIVIC",
            "engine": "1.5L I4",
            "powertrain": "Gasoline",
            "symptoms": "Squeaking sound when braking",
            "payment_session_id": "cs_test_123",
            "citations": ["NHTSA TSB T-SB-0235-12 (http://example.com/x.pdf)"],
        },
        headers=headers,
    )
    assert save_resp.status_code == 201
    saved = save_resp.json()
    assert saved["vin"] == "1HGBH41JXMN109186"
    assert saved["make"] == "HONDA"
    assert saved["id"]
    assert saved["saved_at"]
    assert saved["citations"] == ["NHTSA TSB T-SB-0235-12 (http://example.com/x.pdf)"]

    list_resp = client.get("/api/repairs", headers=headers)
    assert list_resp.status_code == 200
    repairs = list_resp.json()
    assert len(repairs) == 1
    assert repairs[0]["vin"] == "1HGBH41JXMN109186"
    assert repairs[0]["citations"] == ["NHTSA TSB T-SB-0235-12 (http://example.com/x.pdf)"]


def test_save_repair_minimal_fields(client):
    headers = _auth_headers(client, email="minimal@example.com")

    response = client.post(
        "/api/repairs",
        json={"vin": "1HGBH41JXMN109186", "symptoms": "Unknown noise"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["year"] is None
    assert data["make"] is None


def test_repairs_are_scoped_per_user(client):
    headers_a = _auth_headers(client, email="user-a@example.com")
    headers_b = _auth_headers(client, email="user-b@example.com")

    client.post(
        "/api/repairs",
        json={"vin": "VIN_A", "symptoms": "A's issue"},
        headers=headers_a,
    )

    list_b = client.get("/api/repairs", headers=headers_b)
    assert list_b.status_code == 200
    assert list_b.json() == []

    list_a = client.get("/api/repairs", headers=headers_a)
    assert len(list_a.json()) == 1


def test_list_repairs_ordered_most_recent_first(client):
    headers = _auth_headers(client, email="order@example.com")

    client.post(
        "/api/repairs", json={"vin": "VIN_1", "symptoms": "first"}, headers=headers
    )
    client.post(
        "/api/repairs", json={"vin": "VIN_2", "symptoms": "second"}, headers=headers
    )

    repairs = client.get("/api/repairs", headers=headers).json()
    assert len(repairs) == 2
    assert repairs[0]["vin"] == "VIN_2"
    assert repairs[1]["vin"] == "VIN_1"
