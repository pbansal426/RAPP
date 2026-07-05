import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt

from backend.core.config import settings

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
# How long a magic sign-in link stays clickable before the user has to
# request a new one.
VERIFY_TOKEN_EXPIRE_MINUTES = 15


def _create_token(data: dict[str, Any], expire_minutes: int) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict[str, Any]) -> str:
    return _create_token({**data, "type": "access"}, ACCESS_TOKEN_EXPIRE_MINUTES)


def create_verify_token(user_id: str) -> str:
    """A short-lived, single-use token embedded in a magic sign-in link.

    Carries a `jti` so verify_link() can reject a second use of the same
    link -- without it, a forwarded/screenshotted/browser-history magic
    link would grant a fresh 7-day session every time it's replayed within
    its 15-minute window, not just once.
    """
    return _create_token(
        {"sub": user_id, "type": "verify", "jti": str(uuid.uuid4())},
        VERIFY_TOKEN_EXPIRE_MINUTES,
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any] | None:
    """Decode a JWT and verify it carries the expected `type` claim.

    Access and magic-link-verify tokens are signed with the same secret, so
    without this check a leaked, short-lived magic link could be replayed as
    a full session token.
    """
    try:
        payload: dict[str, Any] = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload
