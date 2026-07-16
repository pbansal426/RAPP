"""Daily recall-watch cron (`imp.md` Stage 3.3).

Walks every saved vehicle in `DbSavedRepair`, checks NHTSA's live recall
API (via `backend/services/nhtsa_safety.py`) for open recalls, and emails
the owning user (via Resend, `backend/services/email.py`) for any recall
this VIN hasn't already been alerted about (`DbRecallAlertSent`).

Deliberately vehicle-keyed on (make, model, year) rather than VIN for the
NHTSA lookup -- `recallsByVehicle` only accepts those three, and campaigns
apply to the whole model-year, not an individual VIN -- but dedup and the
outbound email are still per-VIN/per-user, since two owners of the same
model-year must each get notified independently.

Run manually:
    uv run python -m backend.scripts.recall_watch_cron

Schedule daily via cron/launchd, e.g.:
    0 8 * * * cd /path/to/RAPP && uv run python -m backend.scripts.recall_watch_cron
"""

from __future__ import annotations

import asyncio
import sys

import structlog

from backend.core.database import SessionLocal, engine
from backend.core.models import Base, DbRecallAlertSent, DbSavedRepair, DbUser
from backend.services.email import send_recall_alert_email
from backend.services.nhtsa_safety import get_open_recalls

logger = structlog.get_logger()

# Small delay between distinct (make, model, year) lookups -- NHTSA is a
# free public API with no published rate limit, but this script runs
# unattended and isn't latency-sensitive, so there's no reason to hammer it.
_LOOKUP_DELAY_SECONDS = 0.25


async def _run() -> None:
    # Safe to call even if the app server already created these tables --
    # create_all() only creates what's missing. Matters because this script
    # is meant to run standalone via cron, potentially before the app has
    # ever started on a given host.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        saved_repairs = (
            db.query(DbSavedRepair)
            .filter(DbSavedRepair.make.isnot(None))
            .filter(DbSavedRepair.model.isnot(None))
            .filter(DbSavedRepair.year.isnot(None))
            .all()
        )
        if not saved_repairs:
            logger.info("recall_watch_no_saved_vehicles")
            return

        # Group VINs by the (make, model, year) tuple NHTSA's recall API
        # actually accepts, so each distinct vehicle is only queried once
        # even if several users saved the same make/model/year.
        by_vehicle: dict[tuple[str, str, str], list[DbSavedRepair]] = {}
        for repair in saved_repairs:
            key = (repair.make or "", repair.model or "", repair.year or "")
            by_vehicle.setdefault(key, []).append(repair)

        alerts_sent = 0
        for (make, model, year), repairs in by_vehicle.items():
            recalls_response = await get_open_recalls(make, model, year)
            if recalls_response.count == 0:
                await asyncio.sleep(_LOOKUP_DELAY_SECONDS)
                continue

            for repair in repairs:
                vin = repair.vin.strip().upper()
                already_sent = {
                    row.campaign_number
                    for row in db.query(DbRecallAlertSent)
                    .filter(DbRecallAlertSent.vin == vin)
                    .all()
                }
                new_recalls = [
                    r
                    for r in recalls_response.open_recalls
                    if r.campaign_number not in already_sent
                ]
                if not new_recalls:
                    continue

                user = (
                    db.query(DbUser).filter(DbUser.id == repair.user_id).first()
                    if repair.user_id
                    else None
                )
                if user is None:
                    # No email address to notify -- still record the recalls
                    # as "sent" so a future user attached to this VIN isn't
                    # silently skipped, and so we don't retry every day.
                    for r in new_recalls:
                        db.add(
                            DbRecallAlertSent(
                                vin=vin, campaign_number=r.campaign_number
                            )
                        )
                    db.commit()
                    continue

                vehicle_desc = f"{year} {make} {model}".strip()
                sent = await send_recall_alert_email(
                    user.email,
                    vehicle_desc,
                    [
                        {
                            "component": r.component,
                            "summary": r.summary,
                            "remedy": r.remedy,
                        }
                        for r in new_recalls
                    ],
                )
                if sent:
                    alerts_sent += 1
                else:
                    logger.warning(
                        "recall_watch_email_send_failed", vin=vin, email=user.email
                    )

                # Mark as sent regardless of email success -- a persistent
                # Resend outage shouldn't turn into an infinite daily retry
                # storm for the same recall; failures are already logged
                # above for an operator to notice and re-run manually.
                for r in new_recalls:
                    db.add(
                        DbRecallAlertSent(vin=vin, campaign_number=r.campaign_number)
                    )
                db.commit()

            await asyncio.sleep(_LOOKUP_DELAY_SECONDS)

        logger.info(
            "recall_watch_complete",
            vehicles_checked=len(by_vehicle),
            alerts_sent=alerts_sent,
        )
    finally:
        db.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
    sys.exit(0)
