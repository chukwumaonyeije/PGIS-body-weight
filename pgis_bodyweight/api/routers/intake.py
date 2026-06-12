from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pgis_bodyweight.api._conversion import to_engine_intake
from pgis_bodyweight.api.schemas import (
    IntakeAssessmentResponse,
    IntakeRequest,
    IntakeSubmitRequest,
    IntakeSubmitResponse,
)
from pgis_bodyweight.api.security import get_current_user_id, require_matching_user
from pgis_bodyweight.engine.safety import check_parq, resolve_hypo_risk
from pgis_bodyweight.models.db import get_db
from pgis_bodyweight.models.tables import IntakeSubmission, User

router = APIRouter(prefix="/v1/intake", tags=["intake"])


@router.post("", response_model=IntakeAssessmentResponse, status_code=200)
def assess_intake(body: IntakeRequest) -> IntakeAssessmentResponse:
    """
    Stateless safety assessment — validates intake and runs the PAR-Q gate.
    Does not persist. Use POST /v1/intake/submit to save against a user_id.
    """
    try:
        intake = to_engine_intake(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    clearance_required, clearance_reason = check_parq(intake)
    hypo_risk = None if clearance_required else resolve_hypo_risk(intake).value

    return IntakeAssessmentResponse(
        clearance_required=clearance_required,
        clearance_reason=clearance_reason,
        hypo_risk=hypo_risk,
    )


@router.post("/submit", response_model=IntakeSubmitResponse, status_code=201)
def submit_intake(
    body: IntakeSubmitRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> IntakeSubmitResponse:
    """
    Stateful intake submission — persists against user_id, returns intake_id.
    Pass intake_id to POST /v1/programs/generate to generate a program.
    """
    require_matching_user(body.user_id, current_user_id)
    user = db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    try:
        intake = to_engine_intake(body.intake)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    clearance_required, clearance_reason = check_parq(intake)
    hypo_risk = None if clearance_required else resolve_hypo_risk(intake).value

    submission = IntakeSubmission(
        user_id=body.user_id,
        intake_json=body.intake.model_dump(mode="json"),
        clearance_required=clearance_required,
        hypo_risk=hypo_risk,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return IntakeSubmitResponse(
        intake_id=submission.id,
        clearance_required=clearance_required,
        clearance_reason=clearance_reason,
        hypo_risk=hypo_risk,
    )
