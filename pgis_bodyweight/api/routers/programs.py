from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pgis_bodyweight.api._conversion import to_engine_intake
from pgis_bodyweight.api.schemas import (
    GenerateFromIntakeRequest,
    GenerateFromIntakeResponse,
    GenerationResponse,
    IntakeRequest,
    GlucoseTrendItem,
    ProgramOut,
    ProgramProgressResponse,
    RpeTrendItem,
    SessionLogRequest,
    SessionLogResponse,
    SessionOut,
)
from pgis_bodyweight.api.security import get_current_user_id, require_matching_user
from pgis_bodyweight.engine.autoregulate import autoregulate
from pgis_bodyweight.engine.generator import generate_mesocycle
from pgis_bodyweight.engine.types import MovementPattern
from pgis_bodyweight.library import build_exercise_pattern_map
from pgis_bodyweight.models.db import get_db
from pgis_bodyweight.models.tables import (
    GeneratedProgram,
    GlucoseReading,
    IntakeSubmission,
    ProgressionState,
    SessionLog,
    User,
)

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
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> GenerateFromIntakeResponse:
    """
    Stateful generation — loads a persisted intake by intake_id, generates a
    mesocycle, and stores the result. Returns program_id for session queries.
    """
    require_matching_user(body.user_id, current_user_id)
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
def get_current_program(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> GenerateFromIntakeResponse:
    """Return the most recently generated program for a user."""
    require_matching_user(user_id, current_user_id)
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


@router.get("/{program_id}", response_model=GenerateFromIntakeResponse)
def get_program(
    program_id: str,
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> GenerateFromIntakeResponse:
    """Fetch a stored program by ID."""
    require_matching_user(user_id, current_user_id)
    record = db.get(GeneratedProgram, program_id)
    if record is None or record.user_id != user_id:
        raise HTTPException(status_code=404, detail="program not found")
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
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SessionOut:
    """
    Return the next uncompleted session in the program.

    Sessions are served from the stored program_json. A session is 'done' when
    a SessionLog row exists for that (program_id, week, day_in_week).
    """
    require_matching_user(user_id, current_user_id)
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
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SessionLogResponse:
    """Log completion of a session. Explicit week/day targets are preferred."""
    require_matching_user(body.user_id, current_user_id)
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
    if body.week is not None or body.day_in_week is not None:
        if body.week is None or body.day_in_week is None:
            raise HTTPException(status_code=422, detail="week and day_in_week must be provided together")

        target_week, target_day = body.week, body.day_in_week
        if not _program_has_session(program, target_week, target_day):
            raise HTTPException(status_code=404, detail="session not found")
        if (target_week, target_day) in completed:
            raise HTTPException(status_code=409, detail="session already logged")
    else:
        target_week, target_day = _next_open_slot(program, completed)

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


@router.get("/{program_id}/progress", response_model=ProgramProgressResponse)
def get_program_progress(
    program_id: str,
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProgramProgressResponse:
    """Return a small progress summary for the active 4-week program."""
    require_matching_user(user_id, current_user_id)
    record = db.get(GeneratedProgram, program_id)
    if record is None or record.user_id != user_id:
        raise HTTPException(status_code=404, detail="program not found")

    logs = (
        db.query(SessionLog)
        .filter(SessionLog.program_id == program_id)
        .order_by(SessionLog.completed_at.desc())
        .all()
    )
    completed_slots = {(log.week, log.day_in_week) for log in logs}
    latest_log = logs[0] if logs else None

    program = ProgramOut.model_validate(record.program_json)
    current_week, current_day = _next_open_slot(program, completed_slots)
    program_complete = current_week is None

    glucose_entries = (
        db.query(GlucoseReading)
        .filter(GlucoseReading.user_id == user_id)
        .order_by(GlucoseReading.recorded_at.desc())
        .limit(5)
        .all()
    )

    return ProgramProgressResponse(
        program_id=program_id,
        sessions_completed=len(logs),
        most_recent_session_date=latest_log.completed_at.isoformat() if latest_log else None,
        recent_rpe_trend=_recent_rpe_trend(logs),
        recent_glucose_entries=[
            GlucoseTrendItem(
                recorded_at=entry.recorded_at.isoformat(),
                value_mgdl=entry.value_mgdl,
            )
            for entry in reversed(glucose_entries)
        ],
        current_week=current_week,
        current_day=current_day,
        program_complete=program_complete,
    )


def _next_open_slot(program: ProgramOut, completed_slots: set[tuple[int, int]]) -> tuple[int | None, int | None]:
    for week in program.weeks:
        for session in week.sessions:
            if (week.week_number, session.day) not in completed_slots:
                return week.week_number, session.day
    return None, None


def _program_has_session(program: ProgramOut, target_week: int, target_day: int) -> bool:
    return any(
        week.week_number == target_week and any(session.day == target_day for session in week.sessions)
        for week in program.weeks
    )


def _recent_rpe_trend(logs: list[SessionLog]) -> list[RpeTrendItem]:
    trend: list[RpeTrendItem] = []
    for log in logs:
        rpe_data = log.per_exercise_rpe or {}
        if "overall" in rpe_data:
            rpe = float(rpe_data["overall"])
        elif rpe_data:
            values = [float(value) for value in rpe_data.values()]
            rpe = sum(values) / len(values)
        else:
            continue
        trend.append(RpeTrendItem(completed_at=log.completed_at.isoformat(), rpe=round(rpe, 1)))
        if len(trend) == 5:
            break
    return list(reversed(trend))


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
