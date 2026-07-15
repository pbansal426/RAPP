# ruff: noqa: B008 -- FastAPI's Depends(...) is meant to be called in
# argument defaults; this isn't the mutable-default-argument bug B008 flags.
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.models import DbChatUsage, DbGuideUnlock, DbUser
from backend.core.security import decode_token
from backend.routers.diagnose import check_high_risk
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


def check_text_high_risk(text: str) -> tuple[bool, str | None, str | None]:
    """Scan arbitrary text (e.g. a retrieved TSB) for high-risk categories."""
    t = text.lower()

    # 1. SRS / Airbag
    airbag_kws = ["airbag", "srs", "pretensioner", "clockspring", "side curtain"]
    if any(kw in t for kw in airbag_kws):
        return (
            True,
            "Airbag/SRS",
            "DANGER: SRS / Airbag systems are explosive and safety-critical. Professional service is highly recommended.",
        )

    # 2. EV Battery / High-Voltage
    ev_kws = [
        "ev battery",
        "hybrid battery",
        "high voltage",
        "hv battery",
        "traction battery",
        "lithium",
    ]
    if any(kw in t for kw in ev_kws):
        return (
            True,
            "EV Battery",
            "DANGER: High-voltage EV/hybrid battery systems carry lethal voltage. Professional service is highly recommended.",
        )

    # 3. Pressurized Fuel Line
    fuel_kws = [
        "fuel line",
        "fuel rail",
        "pressurized fuel",
        "high pressure fuel",
        "fuel leak",
    ]
    if any(kw in t for kw in fuel_kws):
        return (
            True,
            "Fuel Line",
            "DANGER: Pressurized fuel lines are highly flammable and run under extreme pressure. Professional service is highly recommended.",
        )

    return False, None, None


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

    # Stage 1.5 Safety Check: symptoms/OBD codes
    is_high_risk, _high_risk_system, warning_msg = check_high_risk(
        request.symptoms, obd_list
    )

    if not is_high_risk:
        # Check retrieved TSBs for safety-critical text
        user_query = f"{request.symptoms} " + " ".join(obd_list)
        user_query = user_query.strip()
        from backend.services.rag import retrieve

        results = retrieve(query=user_query, vin_meta=vin_meta, k=5)
        if results:
            for doc in results:
                has_risk, _sys_name, msg = check_text_high_risk(doc.get("text", ""))
                if has_risk:
                    is_high_risk = True
                    warning_msg = msg
                    break

    if is_high_risk:
        return RepairResponse(
            repair_steps=[],
            citations=[],
            is_blocked_safety=True,
            warning_message=warning_msg,
        )

    skill_level = "Beginner"
    if user and user.skill_level:
        skill_level = user.skill_level
    elif request.skill_level:
        skill_level = request.skill_level

    repair_steps, citations = await generate_repair_procedure(
        vin_meta=vin_meta,
        symptoms=request.symptoms,
        obd_codes=obd_list,
        user_tools=tools_list,
        skill_level=skill_level,
    )

    return RepairResponse(
        repair_steps=repair_steps,
        citations=citations,
        is_blocked_safety=False,
        warning_message=None,
    )


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
