# ruff: noqa: B008 -- FastAPI's Depends(...) is meant to be called in
# argument defaults; this isn't the mutable-default-argument bug B008 flags.
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.models import DbChatUsage, DbGuideUnlock, DbUser
from backend.core.security import decode_token
from backend.routers.vin import decode_vin_internal
from backend.schemas import (
    RepairChatRequest,
    RepairChatResponse,
    RepairRequest,
    RepairResponse,
)
from backend.services.llm import generate_chat_reply, generate_repair_procedure

router = APIRouter()

MAX_CHAT_REPLIES = 5


def _get_user_from_auth(authorization: str | None, db: Session) -> DbUser | None:
    """Extract and load DbUser from Bearer token if valid and present."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = decode_token(
        authorization.removeprefix("Bearer "), expected_type="access"
    )
    user_id = payload.get("sub") if payload else None
    if not user_id:
        return None
    return db.query(DbUser).filter(DbUser.id == user_id).first()


def _session_unlocks_vin(db: Session, session_id: str, vin: str) -> bool:
    """Verify `session_id` is a server-recorded, completed payment for `vin`.

    Replaces trusting any non-empty client-supplied `stripe_session_id`
    string -- the payments webhook / mock success-stub are the only writers
    of `DbGuideUnlock`, so this can't be spoofed by a client sending an
    arbitrary string.
    """
    session_id = session_id.strip()
    if not session_id:
        return False
    unlock = (
        db.query(DbGuideUnlock)
        .filter(
            DbGuideUnlock.session_id == session_id,
            DbGuideUnlock.vin == vin.strip().upper(),
        )
        .first()
    )
    return unlock is not None


@router.post("/api/repair", response_model=RepairResponse)
async def repair(
    request: RepairRequest,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> RepairResponse:
    user = _get_user_from_auth(authorization, db)
    has_active_sub = user is not None and user.subscription_status == "active"
    is_unlocked = bool(request.stripe_session_id) and _session_unlocks_vin(
        db, request.stripe_session_id, request.vin
    )

    if not (has_active_sub or is_unlocked):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment Required: Active subscription or valid checkout session ID is required.",
        )

    # Prefer the client-supplied vehicle identity (YMM selector covers makes the
    # synthetic-VIN decoder does not); fall back to decoding the VIN.
    vin_meta: dict[str, Any]
    if request.vehicle and request.vehicle.make:
        vin_meta = {
            "vin": request.vin,
            "year": str(request.vehicle.year or ""),
            "make": request.vehicle.make,
            "model": request.vehicle.model or "",
            "engine": request.vehicle.engine or "",
            "drive_type": request.vehicle.drive_type or "",
            "powertrain": request.vehicle.powertrain or "",
        }
    else:
        vin_meta = await decode_vin_internal(request.vin)

    obd_list: list[str] = (
        request.obd_codes
        if isinstance(request.obd_codes, list)
        else ([request.obd_codes] if request.obd_codes else [])
    )
    tools_list: list[str] = (
        request.tools
        if isinstance(request.tools, list)
        else ([request.tools] if request.tools else [])
    )

    repair_steps, citations = await generate_repair_procedure(
        vin_meta=vin_meta,
        symptoms=request.symptoms,
        obd_codes=obd_list,
        user_tools=tools_list,
    )

    return RepairResponse(repair_steps=repair_steps, citations=citations)


@router.post("/api/repair/chat", response_model=RepairChatResponse)
async def repair_chat(
    request: RepairChatRequest,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> RepairChatResponse:
    user = _get_user_from_auth(authorization, db)
    has_active_sub = user is not None and user.subscription_status == "active"
    is_unlocked = bool(request.stripe_session_id) and _session_unlocks_vin(
        db, request.stripe_session_id, request.vin
    )

    if not (has_active_sub or is_unlocked):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment Required: Active subscription or valid checkout session ID is required.",
        )

    session_id = request.stripe_session_id.strip()
    if not session_id and user:
        session_id = f"sub_{user.id}_{request.vin}"

    # Enforce server-side rate limit per stripe_session_id
    usage = (
        db.query(DbChatUsage)
        .filter(DbChatUsage.stripe_session_id == session_id)
        .first()
    )
    if not usage:
        usage = DbChatUsage(stripe_session_id=session_id, message_count=0)
        db.add(usage)

    if usage.message_count >= MAX_CHAT_REPLIES:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Live AI chat limit ({MAX_CHAT_REPLIES} replies) exceeded for this job. Using local canned guidance.",
        )

    vin_meta: dict[str, Any]
    if request.vehicle and request.vehicle.make:
        vin_meta = {
            "year": str(request.vehicle.year or ""),
            "make": request.vehicle.make,
            "model": request.vehicle.model or "",
        }
    else:
        vin_meta = await decode_vin_internal(request.vin)

    reply = await generate_chat_reply(
        vin_meta=vin_meta,
        symptoms=request.symptoms,
        repair_steps=request.repair_steps,
        message=request.message,
    )

    if reply is not None:
        usage.message_count += 1
        usage.last_message_at = datetime.utcnow()
        db.commit()

    return RepairChatResponse(reply=reply)
