import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import Any

import jwt

from backend.core.config import settings

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
RESET_TOKEN_EXPIRE_MINUTES = 60
VERIFY_TOKEN_EXPIRE_MINUTES = 60 * 24


def get_password_hash(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    hash_b64 = base64.b64encode(hashed).decode("utf-8")
    return f"{salt_b64}${hash_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt_b64, hash_b64 = hashed_password.split("$")
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected_hash = base64.b64decode(hash_b64.encode("utf-8"))
        hashed = hashlib.scrypt(plain_password.encode(), salt=salt, n=16384, r=8, p=1)
        # Constant-time comparison -- a plain == leaks timing information
        # about how many leading bytes matched, which can be used to brute
        # force the hash byte-by-byte.
        return hmac.compare_digest(hashed, expected_hash)
    except Exception:
        return False


def _create_token(data: dict[str, Any], expire_minutes: int) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict[str, Any]) -> str:
    return _create_token({**data, "type": "access"}, ACCESS_TOKEN_EXPIRE_MINUTES)


def create_reset_token(user_id: str) -> str:
    return _create_token({"sub": user_id, "type": "reset"}, RESET_TOKEN_EXPIRE_MINUTES)


def create_verify_token(user_id: str) -> str:
    return _create_token({"sub": user_id, "type": "verify"}, VERIFY_TOKEN_EXPIRE_MINUTES)


def decode_token(token: str, expected_type: str) -> dict[str, Any] | None:
    """Decode a JWT and verify it carries the expected `type` claim.

    Access, password-reset, and email-verify tokens are all signed with the
    same secret, so without this check a leaked/short-lived reset or verify
    token could be replayed as a full session token.
    """
    try:
        payload: dict[str, Any] = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload
