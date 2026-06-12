"""
Coaching endpoint — returns optional prose for a specific session.

This endpoint always returns 200. coaching_text is null when the coaching
service is unavailable, slow, or errors — the program is never affected.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pgis_bodyweight.api.schemas import CoachingResponse, ProgramOut, SessionOut
from pgis_bodyweight.api.security import get_current_user_id, require_matching_user
from pgis_bodyweight.coaching import generate_coaching
from pgis_bodyweight.models.db import get_db
from pgis_bodyweight.models.tables import GeneratedProgram

router = APIRouter(prefix="/v1/programs", tags=["coaching"])


@router.get(
    "/{program_id}/sessions/{week}/{day}/coaching",
    response_model=CoachingResponse,
)
async def get_session_coaching(
    program_id: str,
    week: int,
    day: int,
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CoachingResponse:
    require_matching_user(user_id, current_user_id)
    record = db.get(GeneratedProgram, program_id)
    if record is None or record.user_id != user_id:
        raise HTTPException(status_code=404, detail="program not found")

    program = ProgramOut.model_validate(record.program_json)

    target: SessionOut | None = None
    for w in program.weeks:
        if w.week_number == week:
            for s in w.sessions:
                if s.day == day:
                    target = s
                    break

    if target is None:
        raise HTTPException(status_code=404, detail="session not found")

    context = {
        "program": {
            "hypo_risk": program.hypo_risk,
            "rules_applied": program.rules_applied,
            "engine_version": program.engine_version,
        },
        "session": target.model_dump(),
    }

    coaching_text = await generate_coaching(context)
    return CoachingResponse(coaching_text=coaching_text)
