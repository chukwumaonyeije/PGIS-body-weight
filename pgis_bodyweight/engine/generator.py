from __future__ import annotations
from .types import IntakeAssessment, GenerationResult

ENGINE_VERSION = "0.1.0"


def generate_mesocycle(intake: IntakeAssessment) -> GenerationResult:
    """
    Generate a 4-week mesocycle from a completed intake.

    Pure: no network, no DB, no file I/O, no randomness, no clock reads.
    Same input always produces the same output.

    Steps (PRD §7):
    1. Safety gate — PAR-Q flags → clearance_required, no program
    2. Per-pattern starting levels from functional tests
    3. Dose from constraints (days/week × minutes/session)
    4. Glycemic layer — hypo_risk branch, glucose-check prompts, preferred windows
    5. Assemble 4-week mesocycle with deload
    """
    raise NotImplementedError
