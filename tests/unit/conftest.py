import os

# Force test mode before backend.core.config's Settings() singleton is ever
# instantiated (first import, triggered by test modules importing backend.main).
# Without this, a real GEMINI_API_KEY leaking in from a developer's local .env
# (python-dotenv's load_dotenv() walks upward from this file's directory) makes
# tests that don't explicitly mock get_genai_client silently call the live
# Gemini API instead of getting deterministic None/fallback behavior.
os.environ.setdefault("ENVIRONMENT", "test")

import pytest


# `cs_test_123` / `1HGBH41JXMN109186` is the paywall fixture pair used across
# the unit suite to represent "an already-completed checkout". Since
# POST /api/repair now verifies stripe_session_id against a server-recorded
# DbGuideUnlock row (imp.md Stage 1.3/1.4) instead of trusting any non-empty
# client-supplied string, this row must exist before those tests run.
_FIXTURE_VIN = "1HGBH41JXMN109186"
_FIXTURE_SESSION_IDS = ("cs_test_123", "cs_test_no_key", "cs_test_rate_limit_session")


@pytest.fixture(autouse=True)
def _seed_guide_unlock_fixture():
    from backend.core.database import SessionLocal, engine
    from backend.core.models import Base, DbGuideUnlock

    # Many test modules never instantiate TestClient(app), so the app's
    # lifespan (which normally runs create_all) never fires -- create the
    # tables directly here instead. No-op once they already exist.
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        for session_id in _FIXTURE_SESSION_IDS:
            if not db.query(DbGuideUnlock).filter(
                DbGuideUnlock.session_id == session_id
            ).first():
                db.add(DbGuideUnlock(session_id=session_id, vin=_FIXTURE_VIN))
        db.commit()
    yield
