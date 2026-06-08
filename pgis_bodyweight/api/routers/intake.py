from __future__ import annotations

from fastapi import APIRouter, HTTPException

from pgis_bodyweight.api._conversion import to_engine_intake
from pgis_bodyweight.api.schemas import IntakeAssessmentResponse, IntakeRequest
from pgis_bodyweight.engine.safety import check_parq, resolve_hypo_risk

router = APIRouter(prefix="/v1/intake", tags=["intake"])


@router.post("", response_model=IntakeAssessmentResponse, status_code=200)
async def assess_intake(body: IntakeRequest) -> IntakeAssessmentResponse:
    """
    Validate intake and run the safety gate.

    Returns clearance_required=True and a reason if any PAR-Q flag is present.
    Returns hypo_risk when clearance is not required so the client can surface
    pre-session glucose guidance without waiting for program generation.
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
