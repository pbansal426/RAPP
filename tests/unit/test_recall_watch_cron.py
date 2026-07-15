import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.models import Base, DbRecallAlertSent, DbSavedRepair, DbUser
from backend.schemas import RecallInfo, RecallsResponse
from backend.scripts import recall_watch_cron


@pytest.fixture
def db_session(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(recall_watch_cron, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(recall_watch_cron, "engine", engine)
    # Zero the sleep so the test doesn't actually wait between vehicles.
    monkeypatch.setattr(recall_watch_cron, "_LOOKUP_DELAY_SECONDS", 0)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_user_with_saved_repair(
    db_session, vin: str, make: str, model: str, year: str
) -> DbUser:
    user = DbUser(id=str(uuid.uuid4()), email=f"{vin.lower()}@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    db_session.add(
        DbSavedRepair(
            id=str(uuid.uuid4()),
            user_id=user.id,
            vin=vin,
            year=year,
            make=make,
            model=model,
            symptoms="test symptoms",
        )
    )
    db_session.commit()
    return user


def test_recall_watch_sends_alert_for_new_open_recall(db_session, monkeypatch):
    user = _seed_user_with_saved_repair(
        db_session, "1HGCM82633A123456", "Honda", "Accord", "2015"
    )

    async def fake_get_open_recalls(make, model, year):
        return RecallsResponse(
            open_recalls=[
                RecallInfo(
                    campaign_number="15V123000",
                    component="AIR BAGS",
                    summary="Airbag inflator may rupture.",
                    consequence="Injury risk.",
                    remedy="Dealers will replace the inflator free of charge.",
                    report_received_date="2015-05-01",
                )
            ],
            count=1,
        )

    sent_calls = []

    async def fake_send_recall_alert_email(to_email, vehicle_desc, recalls):
        sent_calls.append((to_email, vehicle_desc, recalls))
        return True

    monkeypatch.setattr(recall_watch_cron, "get_open_recalls", fake_get_open_recalls)
    monkeypatch.setattr(
        recall_watch_cron, "send_recall_alert_email", fake_send_recall_alert_email
    )

    import asyncio

    asyncio.run(recall_watch_cron._run())

    assert len(sent_calls) == 1
    assert sent_calls[0][0] == user.email
    assert "Accord" in sent_calls[0][1]

    sent_rows = db_session.query(DbRecallAlertSent).all()
    assert len(sent_rows) == 1
    assert sent_rows[0].campaign_number == "15V123000"


def test_recall_watch_does_not_resend_already_alerted_recall(db_session, monkeypatch):
    _seed_user_with_saved_repair(db_session, "1HGCM82633A654321", "Toyota", "Camry", "2018")

    call_count = {"n": 0}

    async def fake_get_open_recalls(make, model, year):
        call_count["n"] += 1
        return RecallsResponse(
            open_recalls=[
                RecallInfo(
                    campaign_number="18V456000",
                    component="FUEL SYSTEM",
                    summary="Fuel pump may fail.",
                    consequence="Stall risk.",
                    remedy="Dealers will replace the fuel pump free of charge.",
                    report_received_date="2018-01-01",
                )
            ],
            count=1,
        )

    sent_calls = []

    async def fake_send_recall_alert_email(to_email, vehicle_desc, recalls):
        sent_calls.append(to_email)
        return True

    monkeypatch.setattr(recall_watch_cron, "get_open_recalls", fake_get_open_recalls)
    monkeypatch.setattr(
        recall_watch_cron, "send_recall_alert_email", fake_send_recall_alert_email
    )

    import asyncio

    asyncio.run(recall_watch_cron._run())
    assert len(sent_calls) == 1

    # Second run: same open recall, already alerted -- must not re-send.
    asyncio.run(recall_watch_cron._run())
    assert len(sent_calls) == 1
    assert call_count["n"] == 2  # NHTSA is still queried each run


def test_recall_watch_no_saved_vehicles_is_a_noop(db_session, monkeypatch):
    calls = []

    async def fake_get_open_recalls(make, model, year):
        calls.append((make, model, year))
        return RecallsResponse(open_recalls=[], count=0)

    monkeypatch.setattr(recall_watch_cron, "get_open_recalls", fake_get_open_recalls)

    import asyncio

    asyncio.run(recall_watch_cron._run())
    assert calls == []
