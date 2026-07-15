"""SQLAlchemy ORM models for user accounts and saved repair guides.

This is the only place `Base`/`DbUser`/`DbSavedRepair` are defined; anything
that needs to query the database imports from here rather than redefining
the schema. Uses SQLAlchemy 2.0's `Mapped`/`mapped_column` style so instance
attributes type-check as their actual Python types under mypy strict,
rather than as `Column[...]` descriptors.
"""

import secrets
import string
from datetime import datetime

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

_REFERRAL_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _random_referral_code() -> str:
    # Python-side default (rather than a DB server_default) so it fires for
    # any DbUser insert that doesn't explicitly set referral_code -- e.g.
    # test fixtures constructing a DbUser directly -- without those callers
    # needing to know this column exists. Real signups
    # (backend/routers/auth.py) always pass an explicit, DB-verified-unique
    # code instead of relying on this; collision odds here are negligible
    # but not verified against the DB the way that path is.
    return "".join(secrets.choice(_REFERRAL_CODE_ALPHABET) for _ in range(8))


class Base(DeclarativeBase):
    pass


class DbUser(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)  # UUID string
    email: Mapped[str] = mapped_column(unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(default=None)
    saved_payment_method: Mapped[bool] = mapped_column(default=False)
    last_payment_session_id: Mapped[str | None] = mapped_column(default=None)
    subscription_status: Mapped[str] = mapped_column(
        default="free"
    )  # "free", "active", "cancelled", "expired"
    mor_customer_id: Mapped[str | None] = mapped_column(default=None)
    mor_subscription_id: Mapped[str | None] = mapped_column(default=None)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(default=None)
    skill_level: Mapped[str] = mapped_column(
        default="Beginner"
    )  # "Beginner", "Intermediate", "Advanced"
    completed_jobs_count: Mapped[int] = mapped_column(default=0)
    skill_badges: Mapped[list[str] | None] = mapped_column(
        JSON, default=list
    )  # e.g., ["brakes_101", "electrical_basics"]
    # Referral program (`imp.md` Stage 3.3). `referral_code` is generated
    # once at signup and never changes -- it's the code this user shares.
    # `referred_by_code` records which code (if any) this user signed up
    # under, kept even after the code is looked up so the relationship is
    # auditable without a join. `referral_credits` is a simple integer
    # ledger: each credit redeems for one free single-incident guide unlock
    # (see `DbGuideUnlock` / `POST /api/auth/redeem-referral-credit`) rather
    # than a cash reward, so redemption never touches the payment provider.
    referral_code: Mapped[str] = mapped_column(
        unique=True, index=True, default=_random_referral_code
    )
    referred_by_code: Mapped[str | None] = mapped_column(default=None)
    referral_credits: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    repairs: Mapped[list["DbSavedRepair"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class DbSavedRepair(Base):
    __tablename__ = "saved_repairs"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)  # UUID string
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    vin: Mapped[str]
    year: Mapped[str | None] = mapped_column(default=None)
    make: Mapped[str | None] = mapped_column(default=None)
    model: Mapped[str | None] = mapped_column(default=None)
    engine: Mapped[str | None] = mapped_column(default=None)
    powertrain: Mapped[str | None] = mapped_column(default=None)
    symptoms: Mapped[str]
    payment_session_id: Mapped[str | None] = mapped_column(default=None)
    # The citations returned by /api/repair at save time -- lets a saved
    # guide show its provenance later without re-calling /api/repair (which
    # could return different citations on a re-fetch, e.g. after new TSB
    # ingestion for this vehicle) or silently losing that context entirely.
    citations: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    saved_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["DbUser"] = relationship(back_populates="repairs")


class UsedVerifyToken(Base):
    """Marks a magic-link verify token's `jti` as already consumed.

    Enforces single-use: without this, a forwarded/screenshotted/browser-
    history magic link could be replayed any number of times within its
    15-minute expiry window, each replay minting a fresh 7-day session.
    """

    __tablename__ = "used_verify_tokens"

    jti: Mapped[str] = mapped_column(primary_key=True)
    used_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class DbChatUsage(Base):
    """Tracks server-side AI chat usage per payment session / job unlock.

    Enforces the hard 5-reply cap on live LLM queries per job (`imp.md` Stage 1.1).
    Once `message_count >= 5`, `POST /api/repair/chat` returns HTTP 429.
    """

    __tablename__ = "chat_usages"

    stripe_session_id: Mapped[str] = mapped_column(primary_key=True, index=True)
    message_count: Mapped[int] = mapped_column(default=0)
    last_message_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class DbRepairOutcome(Base):
    """A user-submitted "what actually happened" record for a completed job.

    Powers two things (`imp.md` Stage 2.1/2.2): the aggregation query behind
    `GET /api/outcomes/stats` (the "214 Corolla owners completed this, avg
    45 min" social-proof badge on `/results`), and, longer-term, per-vehicle
    difficulty calibration. `user_id`/`saved_repair_id` are nullable because
    a completed job can be marked done while logged out -- unlike
    `DbSavedRepair`, this table's whole purpose is capturing that outcome
    data even from anonymous single-incident purchasers.
    """

    __tablename__ = "repair_outcomes"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)  # UUID string
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, default=None
    )
    saved_repair_id: Mapped[str | None] = mapped_column(
        ForeignKey("saved_repairs.id"), nullable=True, default=None
    )
    make: Mapped[str] = mapped_column(index=True)
    model: Mapped[str] = mapped_column(index=True)
    year: Mapped[str | None] = mapped_column(default=None)
    category: Mapped[str] = mapped_column(index=True)
    actual_cost_usd: Mapped[float]
    actual_duration_minutes: Mapped[int]
    completed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class DbGuideUnlock(Base):
    """Server-side proof that a checkout session paid to unlock a VIN's guide.

    Written by the payments webhook (live Polar checkouts) and the mock
    success-stub (dev/test checkouts) when a single-incident purchase
    completes. `POST /api/repair` / `/api/repair/chat` check this instead of
    trusting any non-empty client-supplied `stripe_session_id` string -- that
    was the "coupling unlocks exclusively to ephemeral client localStorage"
    flaw `imp.md` Stage 1.3/1.4 calls out. Deliberately not folded into
    `DbSavedRepair`: that table requires a non-null `user_id` and `symptoms`
    for the user-facing garage feature, but a checkout can complete while
    logged out and before any guide has been generated to save.
    """

    __tablename__ = "guide_unlocks"

    session_id: Mapped[str] = mapped_column(primary_key=True, index=True)
    vin: Mapped[str] = mapped_column(index=True)
    user_id: Mapped[str | None] = mapped_column(default=None)
    price_type: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class DbRecallAlertSent(Base):
    """Dedup record for the daily recall-watch cron (`imp.md` Stage 3.3).

    `backend/scripts/recall_watch_cron.py` queries NHTSA's live recall API
    for every VIN in `DbSavedRepair` once a day. Without this table it would
    re-email the same open recall to the same owner every single run for as
    long as that recall stays open (recalls can stay open for years). The
    composite primary key (`vin`, `campaign_number`) means "have we ever
    alerted this VIN about this specific NHTSA campaign" -- a natural
    dedup key that needs no extra bookkeeping.
    """

    __tablename__ = "recall_alerts_sent"

    vin: Mapped[str] = mapped_column(primary_key=True, index=True)
    campaign_number: Mapped[str] = mapped_column(primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
