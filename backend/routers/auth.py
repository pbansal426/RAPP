# ruff: noqa: B008 -- FastAPI's Depends(...) is meant to be called in
# argument defaults; this isn't the mutable-default-argument bug B008 flags.
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.models import DbUser
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
    return UserResponse(id=user.id, email=user.email, display_name=user.display_name)


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

    sent = await send_magic_link_email(email, magic_link)
    if sent:
        return RequestLinkResponse(message="Check your email for a sign-in link.")

    # Dev-mode fallback: see RequestLinkResponse.magic_link's docstring.
    return RequestLinkResponse(
        message="Dev mode: no email provider configured, use the link below.",
        magic_link=magic_link,
    )


@router.post("/verify-link", response_model=AuthResponse)
def verify_link(
    request: VerifyLinkRequest, db: Session = Depends(get_db)
) -> AuthResponse:
    payload = decode_token(request.token, expected_type="verify")
    if not payload or not payload.get("sub"):
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
