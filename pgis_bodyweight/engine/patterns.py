from __future__ import annotations
from .types import (
    IntakeAssessment,
    MovementPattern,
    AgeSexBand,
    Sex,
    STS_LEVEL_THRESHOLDS,
    PUSHUP_LEVEL_THRESHOLDS,
    PUSHUP_DEFAULT_LEVEL,
)


def resolve_starting_levels(intake: IntakeAssessment) -> dict[MovementPattern, int]:
    """
    Return a starting level (1–3) for each of the six movement patterns.

    Squat level is normed by (age_band, sex) via Rikli & Jones 2013.
    Raises ValueError if the user's age/sex band has not been reviewed.
    Push level uses the coaching-derived PUSHUP_LEVEL_THRESHOLDS (REVIEW).
    Hinge, pull, core default to 1 — no validated functional test yet.
    Balance level is derived from single-leg stand time (thresholds are REVIEW).
    """
    return {
        MovementPattern.SQUAT:              _squat_level(intake),
        MovementPattern.HINGE:              1,  # conservative default — no functional test yet
        MovementPattern.HORIZONTAL_PUSH:    _push_level(intake),
        MovementPattern.PULL:               1,  # conservative default — no functional test yet
        MovementPattern.CORE:               1,  # conservative default — no functional test yet
        MovementPattern.SINGLE_LEG_BALANCE: _balance_level(intake),
    }


# ── Per-pattern level helpers ─────────────────────────────────────────────────

def _squat_level(intake: IntakeAssessment) -> int:
    band = _age_sex_band(intake)
    norms = STS_LEVEL_THRESHOLDS.get(band)
    if norms is None:
        raise ValueError(
            f"No reviewed STS norms for age band {band.age_min}–{band.age_max}, "
            f"sex={band.sex.value}. Fill the entry in STS_LEVEL_THRESHOLDS before use."
        )
    count = intake.functional_tests.sit_to_stand_count
    for upper_exclusive, level in norms.level_thresholds:
        if count < upper_exclusive:
            return level
    return norms.top_level


def _age_sex_band(intake: IntakeAssessment) -> AgeSexBand:
    age = intake.age
    norm_sex = Sex.FEMALE if intake.sex == Sex.NON_BINARY else intake.sex
    for age_min, age_max in [(60,64),(65,69),(70,74),(75,79),(80,84),(85,89),(90,99)]:
        if age_min <= age <= age_max:
            return AgeSexBand(age_min, age_max, norm_sex)
    raise ValueError(f"Age {age} is outside the supported range (60–99).")


def _push_level(intake: IntakeAssessment) -> int:
    count = intake.functional_tests.pushup_max
    for upper_exclusive, level in PUSHUP_LEVEL_THRESHOLDS:
        if count < upper_exclusive:
            return level
    return PUSHUP_DEFAULT_LEVEL


def _balance_level(intake: IntakeAssessment) -> int:
    # Thresholds confirmed by physician 2026-06-10.
    # <5 s: Vellas et al. (1997) — associated with injurious falls; floor-of-
    #   function threshold; also triggers 2-hand support in the session.
    # <10 s: Bohannon et al. (2006) mean ± SD data by decade; <10 s consistently
    #   associated with increased fall risk and all-cause mortality in older adults.
    #   Also the high-impact suppression threshold in safety.py.
    s = intake.functional_tests.single_leg_stand_s
    if s < 5.0:
        return 1
    if s < 10.0:
        return 2
    return 3
