"""SQLAlchemy ORM models for user accounts and saved repair guides.

This is the only place `Base`/`DbUser`/`DbSavedRepair` are defined; anything
that needs to query the database imports from here rather than redefining
the schema. Uses SQLAlchemy 2.0's `Mapped`/`mapped_column` style so instance
attributes type-check as their actual Python types under mypy strict,
rather than as `Column[...]` descriptors.
"""

from datetime import datetime

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
