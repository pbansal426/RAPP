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


def _request_and_extract_token(client, email: str) -> str:
    """No RESEND_API_KEY is set in tests, so request-link always returns the
    magic link directly (dev-mode) instead of emailing it."""
    response = client.post("/api/auth/request-link", json={"email": email})
    assert response.status_code == 200
    magic_link = response.json()["magic_link"]
    assert magic_link
    return magic_link.split("token=")[1]


def test_request_link_creates_account_on_first_request(client):
    response = client.post(
        "/api/auth/request-link",
        json={"email": "New@Example.com", "display_name": "New"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["magic_link"]
    assert "token=" in data["magic_link"]


def test_request_link_rejects_invalid_email(client):
    response = client.post("/api/auth/request-link", json={"email": "not-an-email"})
    assert response.status_code == 422


def test_verify_link_returns_token_and_user(client):
    token = _request_and_extract_token(client, "verify@example.com")
    response = client.post("/api/auth/verify-link", json={"token": token})
    assert response.status_code == 200
    data = response.json()
    assert data["token"]
    assert data["user"]["email"] == "verify@example.com"


def test_verify_link_same_email_reuses_existing_account(client):
    token1 = _request_and_extract_token(client, "same@example.com")
    user1 = client.post("/api/auth/verify-link", json={"token": token1}).json()["user"]

    token2 = _request_and_extract_token(client, "Same@Example.com")
    user2 = client.post("/api/auth/verify-link", json={"token": token2}).json()["user"]

    assert user1["id"] == user2["id"]


def test_verify_link_invalid_token_returns_401(client):
    response = client.post("/api/auth/verify-link", json={"token": "not-a-real-token"})
    assert response.status_code == 401


def test_verify_link_rejects_an_access_token(client):
    # Tokens are scoped by a `type` claim -- an access token must not work
    # as a magic-link-verify token even though both are signed with the
    # same secret.
    token = _request_and_extract_token(client, "scoped@example.com")
    access_token = client.post("/api/auth/verify-link", json={"token": token}).json()["token"]

    response = client.post("/api/auth/verify-link", json={"token": access_token})
    assert response.status_code == 401


def test_me_with_valid_token(client):
    token = _request_and_extract_token(client, "me@example.com")
    access_token = client.post("/api/auth/verify-link", json={"token": token}).json()["token"]

    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
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


def test_me_rejects_a_verify_token(client):
    # The inverse of test_verify_link_rejects_an_access_token: a magic-link
    # token must not work as a session token either.
    verify_token = _request_and_extract_token(client, "scoped2@example.com")
    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {verify_token}"}
    )
    assert response.status_code == 401


def test_update_display_name(client):
    token = _request_and_extract_token(client, "update@example.com")
    access_token = client.post("/api/auth/verify-link", json={"token": token}).json()["token"]

    response = client.patch(
        "/api/auth/me",
        json={"display_name": "Updated Name"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "Updated Name"
