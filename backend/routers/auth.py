# ruff: noqa: B008 -- FastAPI's Depends(...) is meant to be called in
# argument defaults; this isn't the mutable-default-argument bug B008 flags.
import time
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.models import DbUser, UsedVerifyToken
from backend.core.security import create_access_token, create_verify_token, decode_token
from backend.schemas import (
    AuthResponse,
    RequestLinkRequest,
    RequestLinkResponse,
    UpdateAccountRequest,
    UserResponse,
    VerifyLinkRequest,
)
from backend.services.email import send_magic_link_email

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()
logger = structlog.get_logger()

# Per-email cooldown for /request-link -- in-memory only (resets on
# restart, which is fine: its job is to blunt rapid-fire spam/enumeration
# within a single server's uptime, not to be a durable record). Keyed by
# the normalized email, value is the monotonic time of the last request.
_REQUEST_LINK_COOLDOWN_SECONDS = 20.0
_last_request_at: dict[str, float] = {}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> DbUser:
    token = credentials.credentials
    payload = decode_token(token, expected_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(DbUser).filter(DbUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _to_user_response(user: DbUser) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        subscription_status=user.subscription_status,
    )


@router.post("/request-link", response_model=RequestLinkResponse)
async def request_link(
    request: RequestLinkRequest, db: Session = Depends(get_db)
) -> RequestLinkResponse:
    email = request.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid email is required.",
        )

    now = time.monotonic()
    last = _last_request_at.get(email)
    if last is not None and now - last < _REQUEST_LINK_COOLDOWN_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait a moment before requesting another sign-in link.",
        )
    _last_request_at[email] = now

    # Magic-link auth unifies signup and login: the first request for an
    # email creates the account, every later request just signs it in.
    user = db.query(DbUser).filter(DbUser.email == email).first()
    if not user:
        user = DbUser(
            id=str(uuid.uuid4()),
            email=email,
            display_name=request.display_name.strip() if request.display_name else None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_verify_token(user.id)
    magic_link = f"{settings.frontend_url}/verify-email?token={token}"

    # Dev-mode fallback (returning the link in the response) is ONLY safe
    # when no email provider is configured at all. If RESEND_API_KEY *is*
    # set but a real send still fails -- e.g. Resend's sandbox mode only
    # delivers to the account's own email until a domain is verified, so
    # every other address 4xxs -- that must NOT fall through to leaking the
    # link back to the caller. Anyone could otherwise submit a victim's
    # email and get their live sign-in link handed back directly. A real
    # send failure just gets logged for an operator to notice.
    if not settings.resend_api_key:
        return RequestLinkResponse(
            message="Dev mode: no email provider configured, use the link below.",
            magic_link=magic_link,
        )

    sent = await send_magic_link_email(email, magic_link)
    if not sent:
        logger.warning("magic_link_send_failed", email=email)
    # Always return the same message regardless of send success -- a
    # differing response would let callers enumerate registered accounts
    # or probe which addresses Resend will actually deliver to.
    return RequestLinkResponse(message="Check your email for a sign-in link.")


@router.post("/verify-link", response_model=AuthResponse)
def verify_link(
    request: VerifyLinkRequest, db: Session = Depends(get_db)
) -> AuthResponse:
    payload = decode_token(request.token, expected_type="verify")
    jti = payload.get("jti") if payload else None
    if not payload or not payload.get("sub") or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This sign-in link is invalid or has expired.",
        )
    user = db.query(DbUser).filter(DbUser.id == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This sign-in link is invalid or has expired.",
        )

    # Enforce single-use: the unique jti primary key rejects a second
    # insert for the same token, including two near-simultaneous replays.
    db.add(UsedVerifyToken(jti=jti))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This sign-in link has already been used. Request a new one.",
        ) from None

    token = create_access_token(data={"sub": user.id})
    return AuthResponse(token=token, user=_to_user_response(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: DbUser = Depends(get_current_user)) -> UserResponse:
    return _to_user_response(current_user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    request: UpdateAccountRequest,
    current_user: DbUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    if request.display_name is not None:
        current_user.display_name = request.display_name.strip() or None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _to_user_response(current_user)
