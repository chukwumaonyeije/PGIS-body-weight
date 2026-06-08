from __future__ import annotations
from .types import IntakeAssessment, HypoRisk, JointFlag, HYPO_RISK_MEDICATIONS

# REVIEW: clinical value needed — single-leg stand threshold (seconds) below which
# high-impact exercises are suppressed independent of other triggers.
# Using 10.0 s as a working placeholder; physician must confirm.
_BALANCE_IMPACT_THRESHOLD_S: float = 10.0


def check_parq(intake: IntakeAssessment) -> tuple[bool, str | None]:
    """Return (clearance_required, reason). Any PAR-Q flag routes to clearance."""
    if intake.parq_flags:
        reason = f"PAR-Q flags present: {', '.join(intake.parq_flags)}"
        return True, reason
    return False, None


def resolve_hypo_risk(intake: IntakeAssessment) -> HypoRisk:
    """Return ELEVATED for insulin/sulfonylurea/meglitinide; STANDARD otherwise."""
    if intake.medication_class in HYPO_RISK_MEDICATIONS:
        return HypoRisk.ELEVATED
    return HypoRisk.STANDARD


def is_impact_suppressed(intake: IntakeAssessment) -> bool:
    """
    Return True when high-impact exercises must be excluded from the program.

    Triggers (any one is sufficient):
      - JointFlag.KNEE: knee trouble implies impact restriction — you do not
        prescribe jumping to a patient who reports knee problems.
      - fall_risk: explicit self-reported or clinician-flagged fall risk.
      - low balance score: single-leg stand below _BALANCE_IMPACT_THRESHOLD_S.
        REVIEW: threshold value is a working placeholder — physician must confirm.

    Phase 1 default: impact is suppressed for everyone. Impact is earned through
    progression, not a starting state. The individual trigger checks are encoded
    here now so they remain enforced when Phase 2 unlocks impact for qualifying
    users — remove only the final `return True` at that time, not the trigger code.
    """
    if JointFlag.KNEE in intake.joint_flags:
        return True
    if intake.fall_risk:
        return True
    if intake.functional_tests.single_leg_stand_s < _BALANCE_IMPACT_THRESHOLD_S:
        return True
    return True  # Phase 1: impact off for everyone — remove this line in Phase 2
