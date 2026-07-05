# ruff: noqa: B008 -- FastAPI's Depends(...) is meant to be called in
# argument defaults; this isn't the mutable-default-argument bug B008 flags.
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.models import DbUser
from backend.core.security import (
    create_access_token,
    create_reset_token,
    create_verify_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from backend.schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ResetPasswordRequest,
    SendVerificationResponse,
    SignupRequest,
    UpdateAccountRequest,
    UserResponse,
    VerifyEmailRequest,
)

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
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        email_verified=user.email_verified,
    )


@router.post("/signup", response_model=AuthResponse)
def signup(request: SignupRequest, db: Session = Depends(get_db)) -> AuthResponse:
    if not request.email.strip() or not request.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password are required.",
        )

    # Check if user already exists
    existing = (
        db.query(DbUser).filter(DbUser.email == request.email.strip().lower()).first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    user_id = str(uuid.uuid4())
    hashed = get_password_hash(request.password)
    user = DbUser(
        id=user_id,
        email=request.email.strip().lower(),
        hashed_password=hashed,
        display_name=request.display_name.strip() if request.display_name else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": user.id})
    return AuthResponse(token=token, user=_to_user_response(user))


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = (
        db.query(DbUser).filter(DbUser.email == request.email.strip().lower()).first()
    )
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
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


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    request: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> ForgotPasswordResponse:
    user = (
        db.query(DbUser).filter(DbUser.email == request.email.strip().lower()).first()
    )
    # Always return 200 with a generic message regardless of whether the
    # email exists -- a differing response would let callers enumerate
    # registered accounts.
    if not user:
        return ForgotPasswordResponse(
            message="If an account exists for that email, a reset link has been generated."
        )

    token = create_reset_token(user.id)
    # Dev-mode only: no email provider is configured, so the link is
    # returned in the response body instead of emailed. Replace this with
    # an actual send once a provider (Resend/Postmark/SendGrid/...) is wired
    # up, and stop returning reset_link from this endpoint.
    reset_link = f"{settings.frontend_url}/reset-password?token={token}"
    return ForgotPasswordResponse(
        message="If an account exists for that email, a reset link has been generated.",
        reset_link=reset_link,
    )


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    payload = decode_token(request.token, expected_type="reset")
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired.",
        )
    user = db.query(DbUser).filter(DbUser.id == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired.",
        )
    if not request.new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A new password is required.",
        )
    user.hashed_password = get_password_hash(request.new_password)
    db.add(user)
    db.commit()
    return {"message": "Password updated. You can now log in with your new password."}


@router.post("/send-verification", response_model=SendVerificationResponse)
def send_verification(
    current_user: DbUser = Depends(get_current_user),
) -> SendVerificationResponse:
    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already verified.",
        )
    token = create_verify_token(current_user.id)
    # Dev-mode only: see forgot_password's reset_link note.
    verify_link = f"{settings.frontend_url}/verify-email?token={token}"
    return SendVerificationResponse(
        message="Verification link generated.", verify_link=verify_link
    )


@router.post("/verify-email", response_model=UserResponse)
def verify_email(
    request: VerifyEmailRequest, db: Session = Depends(get_db)
) -> UserResponse:
    payload = decode_token(request.token, expected_type="verify")
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification link is invalid or has expired.",
        )
    user = db.query(DbUser).filter(DbUser.id == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification link is invalid or has expired.",
        )
    user.email_verified = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_user_response(user)
