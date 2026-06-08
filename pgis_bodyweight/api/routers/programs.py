from __future__ import annotations

from fastapi import APIRouter, HTTPException

from pgis_bodyweight.api._conversion import to_engine_intake
from pgis_bodyweight.api.schemas import GenerationResponse, IntakeRequest, ProgramOut
from pgis_bodyweight.engine.generator import generate_mesocycle

router = APIRouter(prefix="/v1/programs", tags=["programs"])


@router.post("/generate", response_model=GenerationResponse, status_code=200)
async def generate_program(body: IntakeRequest) -> GenerationResponse:
    """
    Generate a 4-week mesocycle from the submitted intake.

    Returns clearance_required=True and program=null when a PAR-Q flag is
    present. Returns the full program otherwise.

    Stateless in Phase 1 — accepts the full intake in the request body.
    Persistence via POST /v1/intake + user session is added in Phase 2.
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
