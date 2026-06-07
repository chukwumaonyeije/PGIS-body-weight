from __future__ import annotations
from .types import IntakeAssessment, MovementPattern


def resolve_starting_levels(intake: IntakeAssessment) -> dict[MovementPattern, int]:
    """
    Return a starting level (1–3) for each of the six movement patterns.

    Squat level is determined by sit_to_stand_count (PRD §7 Step 2).
    Push level is determined by pushup_max (PRD §7 Step 2).
    All six patterns must be present in the returned dict.
    """
    raise NotImplementedError
