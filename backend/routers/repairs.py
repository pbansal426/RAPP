# ruff: noqa: B008 -- FastAPI's Depends(...) is meant to be called in
# argument defaults; this isn't the mutable-default-argument bug B008 flags.
import uuid

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.models import DbRepairOutcome, DbSavedRepair, DbUser
from backend.core.security import decode_token
from backend.repair_templates import select_template
from backend.routers.auth import get_current_user
from backend.schemas import (
    OutcomeCreateRequest,
    OutcomeResponse,
    OutcomeStatsResponse,
    SavedRepairCreate,
    SavedRepairResponse,
)

router = APIRouter(prefix="/api/repairs", tags=["repairs"])
outcomes_router = APIRouter(prefix="/api/outcomes", tags=["outcomes"])


def _get_user_from_auth(authorization: str | None, db: Session) -> DbUser | None:
    """Extract and load DbUser from Bearer token if valid and present.

    Mirrors `backend/routers/repair.py`'s helper: outcome submission must
    work for anonymous single-incident purchasers too, so this can't use
    `get_current_user`'s `HTTPBearer()` dependency, which 403s when no
    Authorization header is present at all.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = decode_token(
        authorization.removeprefix("Bearer "), expected_type="access"
    )
    user_id = payload.get("sub") if payload else None
    if not user_id:
        return None
    return db.query(DbUser).filter(DbUser.id == user_id).first()


def _to_response(repair: DbSavedRepair) -> SavedRepairResponse:
    return SavedRepairResponse(
        id=repair.id,
        vin=repair.vin,
        year=repair.year,
        make=repair.make,
        model=repair.model,
        engine=repair.engine,
        powertrain=repair.powertrain,
        symptoms=repair.symptoms,
        payment_session_id=repair.payment_session_id,
        citations=repair.citations,
        saved_at=repair.saved_at.isoformat() if repair.saved_at else None,
    )


@router.post(
    "", response_model=SavedRepairResponse, status_code=status.HTTP_201_CREATED
)
def save_repair(
    request: SavedRepairCreate,
    current_user: DbUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedRepairResponse:
    repair_id = str(uuid.uuid4())
    db_repair = DbSavedRepair(
        id=repair_id,
        user_id=current_user.id,
        vin=request.vin.strip().upper(),
        year=request.year,
        make=request.make.strip().upper() if request.make else None,
        model=request.model.strip() if request.model else None,
        engine=request.engine,
        powertrain=request.powertrain,
        symptoms=request.symptoms.strip(),
        payment_session_id=request.payment_session_id,
        citations=request.citations,
    )
    db.add(db_repair)

    # Sync payment profile if custom payment is linked
    if request.payment_session_id:
        current_user.saved_payment_method = True
        current_user.last_payment_session_id = request.payment_session_id
        db.add(current_user)

    db.commit()
    db.refresh(db_repair)

    return _to_response(db_repair)


@router.get("", response_model=list[SavedRepairResponse])
def list_repairs(
    current_user: DbUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedRepairResponse]:
    db_repairs = (
        db.query(DbSavedRepair)
        .filter(DbSavedRepair.user_id == current_user.id)
        .order_by(DbSavedRepair.saved_at.desc())
        .all()
    )
    return [_to_response(r) for r in db_repairs]


@outcomes_router.post(
    "", response_model=OutcomeResponse, status_code=status.HTTP_201_CREATED
)
def submit_outcome(
    request: OutcomeCreateRequest,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> OutcomeResponse:
    user = _get_user_from_auth(authorization, db)

    obd_list: list[str] = (
        request.obd_codes
        if isinstance(request.obd_codes, list)
        else ([request.obd_codes] if request.obd_codes else [])
    )

    # Same classifier /api/repair uses to pick a template -- keeps outcome
    # categories consistent with the categories a job was actually diagnosed
    # under, rather than the client guessing its own label.
    template = select_template(request.symptoms, obd_list)
    category = template.category if template else "general"

    outcome = DbRepairOutcome(
        id=str(uuid.uuid4()),
        user_id=user.id if user else None,
        saved_repair_id=request.saved_repair_id,
        make=request.make.strip().upper(),
        model=request.model.strip(),
        year=request.year,
        category=category,
        actual_cost_usd=request.actual_cost_usd,
        actual_duration_minutes=request.actual_duration_minutes,
    )
    db.add(outcome)

    if user:
        user.completed_jobs_count = (user.completed_jobs_count or 0) + 1
        badges = list(user.skill_badges or [])
        badge_name = f"{category}_completed"
        if badge_name not in badges:
            badges.append(badge_name)
        user.skill_badges = badges

        if user.completed_jobs_count >= 10:
            user.skill_level = "Advanced"
        elif (
            user.completed_jobs_count >= 3
            and (user.skill_level or "Beginner") == "Beginner"
        ):
            user.skill_level = "Intermediate"
        db.add(user)

    db.commit()
    db.refresh(outcome)

    return OutcomeResponse(
        id=outcome.id,
        make=outcome.make,
        model=outcome.model,
        year=outcome.year,
        category=outcome.category,
        actual_cost_usd=outcome.actual_cost_usd,
        actual_duration_minutes=outcome.actual_duration_minutes,
        completed_at=outcome.completed_at.isoformat(),
    )


@outcomes_router.get("/stats", response_model=OutcomeStatsResponse)
def get_outcome_stats(
    make: str,
    model: str,
    category: str | None = None,
    db: Session = Depends(get_db),
) -> OutcomeStatsResponse:
    query = db.query(
        func.count(DbRepairOutcome.id),
        func.avg(DbRepairOutcome.actual_duration_minutes),
        func.avg(DbRepairOutcome.actual_cost_usd),
    ).filter(
        func.upper(DbRepairOutcome.make) == make.strip().upper(),
        func.lower(DbRepairOutcome.model) == model.strip().lower(),
    )
    if category:
        query = query.filter(DbRepairOutcome.category == category)

    count, avg_duration, avg_cost = query.one()

    return OutcomeStatsResponse(
        count=count or 0,
        avg_duration_minutes=round(avg_duration, 1) if avg_duration else None,
        avg_cost_usd=round(avg_cost, 2) if avg_cost else None,
    )
