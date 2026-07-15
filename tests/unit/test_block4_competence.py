import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.core.database import SessionLocal, get_db
from backend.core.models import DbRepairOutcome, DbUser
from backend.main import app
from backend.routers.auth import get_current_user


@pytest.fixture
def db_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session: Session) -> DbUser:
    user = (
        db_session.query(DbUser).filter(DbUser.id == "test-user-block4").first()
    )
    if not user:
        user = DbUser(
            id="test-user-block4",
            email="block4@example.com",
            display_name="Block4 Tester",
            subscription_status="active",
            skill_level="Beginner",
            completed_jobs_count=0,
            skill_badges=[],
        )
        db_session.add(user)
    else:
        user.skill_level = "Beginner"
        user.completed_jobs_count = 0
        user.skill_badges = []
        db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(autouse=True)
def _cleanup_block4(db_session: Session):
    yield
    db_session.query(DbRepairOutcome).filter(
        DbRepairOutcome.user_id == "test-user-block4"
    ).delete()
    db_session.query(DbUser).filter(DbUser.id == "test-user-block4").delete()
    db_session.commit()


from backend.core.security import create_access_token


@pytest.fixture
def auth_client(test_user: DbUser, db_session: Session) -> TestClient:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    token = create_access_token({"sub": test_user.id})
    with TestClient(app) as client:
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client
    app.dependency_overrides.clear()


def test_update_skill_level(
    auth_client: TestClient, test_user: DbUser, db_session: Session
):
    response = auth_client.patch("/api/auth/me", json={"skill_level": "Advanced"})
    assert response.status_code == 200
    data = response.json()
    assert data["skill_level"] == "Advanced"

    db_session.refresh(test_user)
    assert test_user.skill_level == "Advanced"


def test_user_skill_leveling(
    auth_client: TestClient, test_user: DbUser, db_session: Session
):
    # Submit 1st outcome (brakes)
    res1 = auth_client.post(
        "/api/outcomes",
        json={
            "vin": "1HGBH41JXMN109186",
            "make": "TOYOTA",
            "model": "CAMRY",
            "year": "2021",
            "symptoms": "Squealing brakes when stopping",
            "actual_cost_usd": 120.0,
            "actual_duration_minutes": 90,
        },
    )
    assert res1.status_code == 201
    db_session.refresh(test_user)
    assert test_user.completed_jobs_count == 1
    assert "brakes_completed" in test_user.skill_badges
    assert test_user.skill_level == "Beginner"

    # Submit 2nd and 3rd outcomes
    for i in range(2):
        auth_client.post(
            "/api/outcomes",
            json={
                "vin": "1HGBH41JXMN109186",
                "make": "TOYOTA",
                "model": "CAMRY",
                "year": "2021",
                "symptoms": "Oil change needed",
                "actual_cost_usd": 40.0,
                "actual_duration_minutes": 30,
            },
        )
    db_session.refresh(test_user)
    assert test_user.completed_jobs_count == 3
    assert test_user.skill_level == "Intermediate"

    # Submit 7 more outcomes to reach 10
    for i in range(7):
        auth_client.post(
            "/api/outcomes",
            json={
                "vin": "1HGBH41JXMN109186",
                "make": "TOYOTA",
                "model": "CAMRY",
                "year": "2021",
                "symptoms": "General checkup",
                "actual_cost_usd": 50.0,
                "actual_duration_minutes": 45,
            },
        )
    db_session.refresh(test_user)
    assert test_user.completed_jobs_count == 10
    assert test_user.skill_level == "Advanced"


@pytest.mark.asyncio
async def test_call_gemini_repair_steps_skill_prompts(monkeypatch):
    from backend.services.gemini import (
        RepairStep,
        RepairStepsSchema,
        call_gemini_repair_steps,
    )

    captured_configs = []

    class DummyClient:
        class aio:
            class models:
                @staticmethod
                async def generate_content(model, contents, config):
                    captured_configs.append(config)
                    return type(
                        "DummyResponse",
                        (),
                        {
                            "parsed": RepairStepsSchema(
                                steps=[
                                    RepairStep(
                                        text="Disconnect battery", is_torque_spec=False
                                    ),
                                    RepairStep(text="10 ft-lbs", is_torque_spec=True),
                                ]
                            )
                        },
                    )()

    monkeypatch.setattr(
        "backend.services.gemini.get_genai_client", lambda: DummyClient()
    )

    steps_beg = await call_gemini_repair_steps("Prompt", skill_level="Beginner")
    assert steps_beg == ["Disconnect battery", "Torque 10 ft-lbs"]
    assert "[POINT OF NO RETURN]" in captured_configs[0].system_instruction
    assert "Beginner DIYer" in captured_configs[0].system_instruction

    await call_gemini_repair_steps("Prompt", skill_level="Advanced")
    assert "Advanced technician" in captured_configs[1].system_instruction

