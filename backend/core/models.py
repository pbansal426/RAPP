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
