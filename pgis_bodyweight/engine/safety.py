from __future__ import annotations
from .types import IntakeAssessment, HypoRisk


def check_parq(intake: IntakeAssessment) -> tuple[bool, str | None]:
    """Return (clearance_required, reason). Any parq_flag → (True, reason)."""
    raise NotImplementedError


def resolve_hypo_risk(intake: IntakeAssessment) -> HypoRisk:
    """Return ELEVATED for insulin/sulfonylurea/meglitinide; STANDARD otherwise."""
    raise NotImplementedError
