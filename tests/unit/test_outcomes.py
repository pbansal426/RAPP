import pytest
from fastapi.testclient import TestClient

from backend.core.security import create_access_token
from backend.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    from backend.core.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Distinctive make used across this module so cleanup can't touch real data
# or another test module's fixture rows in the shared dev sqlite DB.
_MAKE = "ZZOUTCOMETESTMAKE"
_MODEL = "ZZOutcomeTestModel"


@pytest.fixture(autouse=True)
def _cleanup_outcomes(db_session):
    from backend.core.models import DbRepairOutcome

    yield
    db_session.query(DbRepairOutcome).filter(
        DbRepairOutcome.make == _MAKE.upper()
    ).delete()
    db_session.commit()


def test_submit_outcome_derives_category_from_symptoms(client):
    response = client.post(
        "/api/outcomes",
        json={
            "vin": "1HGBH41JXMN109186",
            "make": _MAKE,
            "model": _MODEL,
            "year": "2018",
            "symptoms": "grinding noise when braking, squealing rotor",
            "actual_cost_usd": 145.50,
            "actual_duration_minutes": 90,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "brakes"
    assert body["make"] == _MAKE.upper()
    assert body["actual_cost_usd"] == 145.50
    assert body["actual_duration_minutes"] == 90


def test_submit_outcome_falls_back_to_general_category(client):
    response = client.post(
        "/api/outcomes",
        json={
            "vin": "1HGBH41JXMN109186",
            "make": _MAKE,
            "model": _MODEL,
            "symptoms": "car makes a weird noise sometimes",
            "actual_cost_usd": 20,
            "actual_duration_minutes": 15,
        },
    )
    assert response.status_code == 201
    assert response.json()["category"] == "general"


def test_submit_outcome_works_without_auth(client):
    """Anonymous single-incident purchasers must be able to submit an outcome."""
    response = client.post(
        "/api/outcomes",
        json={
            "vin": "1HGBH41JXMN109186",
            "make": _MAKE,
            "model": _MODEL,
            "symptoms": "brake pads worn",
            "actual_cost_usd": 60,
            "actual_duration_minutes": 45,
        },
    )
    assert response.status_code == 201


def test_submit_outcome_attaches_user_id_from_bearer_token(client, db_session):
    from backend.core.models import DbRepairOutcome, DbUser

    user = (
        db_session.query(DbUser)
        .filter(DbUser.email == "outcome-test@example.com")
        .first()
    )
    if not user:
        import uuid

        user = DbUser(id=str(uuid.uuid4()), email="outcome-test@example.com")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token(data={"sub": user.id})
    response = client.post(
        "/api/outcomes",
        json={
            "vin": "1HGBH41JXMN109186",
            "make": _MAKE,
            "model": _MODEL,
            "symptoms": "brake squeal",
            "actual_cost_usd": 60,
            "actual_duration_minutes": 45,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    outcome_id = response.json()["id"]
    saved = (
        db_session.query(DbRepairOutcome)
        .filter(DbRepairOutcome.id == outcome_id)
        .first()
    )
    assert saved is not None
    assert saved.user_id == user.id


def test_outcome_stats_returns_zero_for_unknown_vehicle(client):
    response = client.get(
        "/api/outcomes/stats", params={"make": "ZZNOSUCHMAKE", "model": "ZZNoSuchModel"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["avg_duration_minutes"] is None
    assert body["avg_cost_usd"] is None


def test_outcome_stats_aggregates_case_insensitively(client):
    for cost, duration in [(100.0, 60), (200.0, 90), (150.0, 75)]:
        r = client.post(
            "/api/outcomes",
            json={
                "vin": "1HGBH41JXMN109186",
                "make": _MAKE.lower(),
                "model": _MODEL.upper(),
                "symptoms": "brake grinding",
                "actual_cost_usd": cost,
                "actual_duration_minutes": duration,
            },
        )
        assert r.status_code == 201

    response = client.get(
        "/api/outcomes/stats", params={"make": _MAKE, "model": _MODEL.lower()}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert body["avg_duration_minutes"] == 75.0
    assert body["avg_cost_usd"] == 150.0


def test_outcome_stats_filters_by_category(client):
    client.post(
        "/api/outcomes",
        json={
            "vin": "1HGBH41JXMN109186",
            "make": _MAKE,
            "model": _MODEL,
            "symptoms": "brake grinding",
            "actual_cost_usd": 100,
            "actual_duration_minutes": 60,
        },
    )
    client.post(
        "/api/outcomes",
        json={
            "vin": "1HGBH41JXMN109186",
            "make": _MAKE,
            "model": _MODEL,
            "symptoms": "misfire rough idle",
            "actual_cost_usd": 300,
            "actual_duration_minutes": 120,
        },
    )

    response = client.get(
        "/api/outcomes/stats",
        params={"make": _MAKE, "model": _MODEL, "category": "brakes"},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
