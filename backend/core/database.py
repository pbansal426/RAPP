import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import settings

DATABASE_URL = settings.database_url or "sqlite:///./data/rapp.db"

# SQLite won't create missing parent directories for its db file on its own.
if DATABASE_URL.startswith("sqlite:///./"):
    db_dir = os.path.dirname(DATABASE_URL.removeprefix("sqlite:///./"))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
