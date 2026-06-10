from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pgis_bodyweight.api._conversion import to_engine_intake
from pgis_bodyweight.api.schemas import (
    GenerateFromIntakeRequest,
    GenerateFromIntakeResponse,
    GenerationResponse,
    IntakeRequest,
    ProgramOut,
    SessionLogRequest,
    SessionLogResponse,
    SessionOut,
)
from pgis_bodyweight.engine.autoregulate import autoregulate
from pgis_bodyweight.engine.generator import generate_mesocycle
from pgis_bodyweight.engine.types import MovementPattern
from pgis_bodyweight.library import build_exercise_pattern_map
from pgis_bodyweight.models.db import get_db
from pgis_bodyweight.models.tables import GeneratedProgram, IntakeSubmission, ProgressionState, SessionLog, User

router = APIRouter(prefix="/v1/programs", tags=["programs"])


@router.post("/generate", response_model=GenerationResponse, status_code=200)
def generate_program(body: IntakeRequest) -> GenerationResponse:
    """
    Stateless generation — accepts full intake inline, returns program.
    Does not persist. Use POST /v1/programs/generate-from-intake to persist.
    """
    try:
        intake = to_engine_intake(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        result = generate_mesocycle(intake)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    program_out = ProgramOut.model_validate(result.program) if result.program else None
    return GenerationResponse(
        clearance_required=result.clearance_required,
        clearance_reason=result.clearance_reason,
        program=program_out,
    )


@router.post("/generate-from-intake", response_model=GenerateFromIntakeResponse, status_code=201)
def generate_from_intake(
    body: GenerateFromIntakeRequest,
    db: Session = Depends(get_db),
) -> GenerateFromIntakeResponse:
    """
    Stateful generation — loads a persisted intake by intake_id, generates a
    mesocycle, and stores the result. Returns program_id for session queries.
    """
    user = db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    submission = db.get(IntakeSubmission, body.intake_id)
    if submission is None or submission.user_id != body.user_id:
        raise HTTPException(status_code=404, detail="intake not found")

    if submission.clearance_required:
        return GenerateFromIntakeResponse(
            program_id="",
            clearance_required=True,
            clearance_reason=None,
            program=None,
        )

    intake_data = IntakeRequest.model_validate(submission.intake_json)
    try:
        intake = to_engine_intake(intake_data)
        result = generate_mesocycle(intake)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    program_out = ProgramOut.model_validate(result.program) if result.program else None

    record = GeneratedProgram(
        user_id=body.user_id,
        intake_id=body.intake_id,
        engine_version=result.program.engine_version,
        hypo_risk=result.program.hypo_risk.value,
        rules_applied=result.program.rules_applied,
        program_json=program_out.model_dump() if program_out else {},
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return GenerateFromIntakeResponse(
        program_id=record.id,
        clearance_required=False,
        clearance_reason=None,
        program=program_out,
    )


@router.get("/current", response_model=GenerateFromIntakeResponse)
def get_current_program(user_id: str, db: Session = Depends(get_db)) -> GenerateFromIntakeResponse:
    """Return the most recently generated program for a user."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    record = (
        db.query(GeneratedProgram)
        .filter(GeneratedProgram.user_id == user_id)
        .order_by(GeneratedProgram.created_at.desc())
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="no program found for user")

    program_out = ProgramOut.model_validate(record.program_json)
    return GenerateFromIntakeResponse(
        program_id=record.id,
        clearance_required=False,
        clearance_reason=None,
        program=program_out,
    )


@router.get("/{program_id}/sessions/next", response_model=SessionOut)
def get_next_session(
    program_id: str,
    user_id: str,
    db: Session = Depends(get_db),
) -> SessionOut:
    """
    Return the next uncompleted session in the program.

    Sessions are served from the stored program_json. A session is 'done' when
    a SessionLog row exists for that (program_id, week, day_in_week).
    """
    record = db.get(GeneratedProgram, program_id)
    if record is None or record.user_id != user_id:
        raise HTTPException(status_code=404, detail="program not found")

    completed = {
        (log.week, log.day_in_week)
        for log in db.query(SessionLog)
        .filter(SessionLog.program_id == program_id)
        .all()
    }

    program = ProgramOut.model_validate(record.program_json)
    for week in program.weeks:
        for session in week.sessions:
            if (week.week_number, session.day) not in completed:
                return session

    raise HTTPException(status_code=404, detail="all sessions completed")


@router.post("/{program_id}/sessions/log", response_model=SessionLogResponse, status_code=201)
def log_session(
    program_id: str,
    body: SessionLogRequest,
    db: Session = Depends(get_db),
) -> SessionLogResponse:
    """Log completion of a session. week and day are inferred from the next uncompleted slot."""
    record = db.get(GeneratedProgram, program_id)
    if record is None or record.user_id != body.user_id:
        raise HTTPException(status_code=404, detail="program not found")

    completed = {
        (log.week, log.day_in_week)
        for log in db.query(SessionLog)
        .filter(SessionLog.program_id == program_id)
        .all()
    }

    program = ProgramOut.model_validate(record.program_json)
    target_week, target_day = None, None
    for week in program.weeks:
        for session in week.sessions:
            if (week.week_number, session.day) not in completed:
                target_week = week.week_number
                target_day = session.day
                break
        if target_week is not None:
            break

    if target_week is None:
        raise HTTPException(status_code=409, detail="all sessions already logged")

    from datetime import datetime, timezone

    def _parse_dt(s: str | None):
        return datetime.fromisoformat(s) if s else None

    log = SessionLog(
        program_id=program_id,
        user_id=body.user_id,
        week=target_week,
        day_in_week=target_day,
        per_exercise_rpe=body.per_exercise_rpe,
        notes=body.notes,
        started_at=_parse_dt(body.started_at),
        finished_at=_parse_dt(body.finished_at),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    level_changes: dict[str, int] = {}
    if body.per_exercise_rpe:
        level_changes = _apply_autoregulation(body.user_id, body.per_exercise_rpe, db)

    return SessionLogResponse(
        log_id=log.id,
        program_id=program_id,
        week=target_week,
        day_in_week=target_day,
        level_changes=level_changes,
    )


def _apply_autoregulation(
    user_id: str,
    per_exercise_rpe: dict[str, float],
    db: Session,
) -> dict[str, int]:
    """
    Load current ProgressionState for the user, run autoregulate(), persist changes.
    Returns a dict of pattern → new_level for patterns that changed.
    """
    existing: dict[MovementPattern, ProgressionState] = {
        MovementPattern(row.pattern): row
        for row in db.query(ProgressionState).filter(ProgressionState.user_id == user_id).all()
    }
    current_levels: dict[MovementPattern, int] = {
        p: (existing[p].current_level if p in existing else 1)
        for p in MovementPattern
    }

    exercise_pattern_map = build_exercise_pattern_map()
    new_levels = autoregulate(per_exercise_rpe, current_levels, exercise_pattern_map)

    changes: dict[str, int] = {}
    for pattern, new_level in new_levels.items():
        if new_level != current_levels[pattern]:
            changes[pattern.value] = new_level
            if pattern in existing:
                existing[pattern].current_level = new_level
            else:
                db.add(ProgressionState(
                    user_id=user_id,
                    pattern=pattern.value,
                    current_level=new_level,
                ))

    if changes:
        db.commit()

    return changes
