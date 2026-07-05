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


def test_signup_returns_token_and_user(client):
    response = client.post(
        "/api/auth/signup",
        json={"email": "New@Example.com", "password": "hunter2", "display_name": "New"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token"]
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["display_name"] == "New"
    assert data["user"]["id"]


def test_signup_requires_email_and_password(client):
    response = client.post(
        "/api/auth/signup", json={"email": "", "password": "hunter2"}
    )
    assert response.status_code == 422

    response = client.post(
        "/api/auth/signup", json={"email": "a@b.com", "password": ""}
    )
    assert response.status_code == 422


def test_signup_duplicate_email_returns_400(client):
    payload = {"email": "dupe@example.com", "password": "hunter2"}
    first = client.post("/api/auth/signup", json=payload)
    assert first.status_code == 200

    second = client.post("/api/auth/signup", json=payload)
    assert second.status_code == 400


def test_signup_email_is_case_insensitive_for_duplicates(client):
    client.post("/api/auth/signup", json={"email": "Case@Example.com", "password": "x"})
    second = client.post(
        "/api/auth/signup", json={"email": "case@example.com", "password": "y"}
    )
    assert second.status_code == 400


def test_login_success(client):
    client.post(
        "/api/auth/signup", json={"email": "login@example.com", "password": "hunter2"}
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "hunter2"},
    )
    assert response.status_code == 200
    assert response.json()["token"]


def test_login_wrong_password_returns_401(client):
    client.post(
        "/api/auth/signup", json={"email": "login2@example.com", "password": "hunter2"}
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "login2@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_unknown_email_returns_401(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert response.status_code == 401


def test_me_with_valid_token(client):
    signup = client.post(
        "/api/auth/signup", json={"email": "me@example.com", "password": "hunter2"}
    )
    token = signup.json()["token"]

    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_me_without_token_returns_403(client):
    # HTTPBearer's own auto_error dependency rejects a missing Authorization
    # header before our code runs; an invalid/expired token still gets a 401
    # from get_current_user itself (see test_me_with_invalid_token_returns_401).
    response = client.get("/api/auth/me")
    assert response.status_code == 403


def test_me_with_invalid_token_returns_401(client):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_password_is_hashed_not_stored_in_plaintext():
    from backend.core.security import get_password_hash, verify_password

    hashed = get_password_hash("hunter2")
    assert "hunter2" not in hashed
    assert verify_password("hunter2", hashed) is True
    assert verify_password("wrong", hashed) is False
