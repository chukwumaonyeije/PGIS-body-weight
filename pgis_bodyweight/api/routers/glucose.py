from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pgis_bodyweight.api.schemas import GlucoseEntryRequest, GlucoseEntryResponse
from pgis_bodyweight.models.db import get_db
from pgis_bodyweight.models.tables import GlucoseReading, SessionLog, User

router = APIRouter(prefix="/v1/glucose", tags=["glucose"])


@router.post("", response_model=GlucoseEntryResponse, status_code=201)
def log_glucose(body: GlucoseEntryRequest, db: Session = Depends(get_db)) -> GlucoseEntryResponse:
    """Store a manual glucose reading against a user, optionally linked to a session log."""
    user = db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    if body.session_log_id is not None:
        log = db.get(SessionLog, body.session_log_id)
        if log is None or log.user_id != body.user_id:
            raise HTTPException(status_code=404, detail="session log not found")

    recorded_at = (
        datetime.fromisoformat(body.recorded_at)
        if body.recorded_at
        else datetime.now(timezone.utc)
    )

    reading = GlucoseReading(
        user_id=body.user_id,
        session_log_id=body.session_log_id,
        value_mgdl=body.value_mgdl,
        recorded_at=recorded_at,
        notes=body.notes,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    return GlucoseEntryResponse(
        reading_id=reading.id,
        user_id=reading.user_id,
        value_mgdl=reading.value_mgdl,
        recorded_at=reading.recorded_at.isoformat(),
    )
