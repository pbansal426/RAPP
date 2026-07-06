import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import settings

DATABASE_URL = settings.database_url or "sqlite:///./data/rapp.db"

# SQLite won't create missing parent directories for its db file on its own.
if DATABASE_URL.startswith("sqlite:///./"):
    db_dir = os.path.dirname(DATABASE_URL.removeprefix("sqlite:///./"))
    if db_dir:
        # A broken "data" symlink -- the common local-dev case being an
        # external-drive-backed data/ whose drive isn't currently plugged
        # in -- makes the makedirs() call below fail with a deeply
        # misleading `FileExistsError: 'data'` (reads like a naming
        # conflict, not "your drive isn't mounted"). Check the first path
        # segment specifically and fail with a message that actually says
        # what's wrong, before that happens.
        root_segment = Path(db_dir.split(os.sep)[0])
        if root_segment.is_symlink() and not root_segment.exists():
            target = os.readlink(root_segment)
            raise RuntimeError(
                f"'{root_segment}' is a symlink to '{target}', which isn't "
                "currently accessible. If this points at an external drive, "
                "plug it in and make sure it's mounted, then restart the backend."
            )
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
