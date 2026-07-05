# ruff: noqa: B008 -- FastAPI's Depends(...) is meant to be called in
# argument defaults; this isn't the mutable-default-argument bug B008 flags.
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.models import DbSavedRepair, DbUser
from backend.routers.auth import get_current_user
from backend.schemas import SavedRepairCreate, SavedRepairResponse

router = APIRouter(prefix="/api/repairs", tags=["repairs"])


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
