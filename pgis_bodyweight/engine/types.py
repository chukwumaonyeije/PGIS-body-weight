from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple


# ── Enumerations ──────────────────────────────────────────────────────────────

class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    # Non-binary / prefer-not-to-say: apply FEMALE norms in patterns.py as the
    # conservative default. Rikli & Jones norms are sex-referenced for
    # physiological reasons; female norms have the lower threshold and are the
    # safer choice when sex is not specified. A future intake version may let
    # the user select which norm set applies.


class MedicationClass(str, Enum):
    INSULIN = "insulin"
    SULFONYLUREA = "sulfonylurea"
    MEGLITINIDE = "meglitinide"
    METFORMIN_ONLY = "metformin_only"
    NONE = "none"
    OTHER = "other"


class JointFlag(str, Enum):
    KNEE = "knee"
    SHOULDER = "shoulder"
    LOWER_BACK = "lower_back"
    WRIST = "wrist"
    HIP = "hip"


class MovementPattern(str, Enum):
    SQUAT = "squat"
    HINGE = "hinge"
    HORIZONTAL_PUSH = "horizontal_push"
    PULL = "pull"
    CORE = "core"
    SINGLE_LEG_BALANCE = "single_leg_balance"


class HypoRisk(str, Enum):
    ELEVATED = "elevated"
    STANDARD = "standard"


class EquipmentItem(str, Enum):
    NONE = "none"
    CHAIR = "chair"
    BAND = "band"
    PULLUP_BAR = "pullup_bar"


# ── Helpers for per-band normative tables ─────────────────────────────────────

class AgeSexBand(NamedTuple):
    """Hashable lookup key for age-band/sex normative tables."""
    age_min: int   # inclusive lower bound of age band
    age_max: int   # inclusive upper bound of age band
    sex: Sex


@dataclass(frozen=True)
class STSBandNorms:
    """
    30-Second Chair Stand Test programming thresholds for one age/sex band.

    level_thresholds: ascending tuple of (exclusive_upper_bound, level) pairs.
      A score < the first bound gets its paired level.
      A score in [prev_bound, bound) gets its paired level.
      A score >= the last bound gets top_level.

    Use None for the whole dict entry (not this class) when a band is unreviewed.
    The engine must raise if it encounters a None entry for the user's band.
    """
    level_thresholds: tuple[tuple[int, int], ...]
    top_level: int
    citation: str  # source for each specific numeric value in this entry


# ── Intake data ───────────────────────────────────────────────────────────────

@dataclass
class FunctionalTests:
    sit_to_stand_count: int    # reps in 30 s; drives squat starting level via STS_LEVEL_THRESHOLDS
    pushup_max: int            # wall/incline max reps; drives push starting level via PUSHUP_LEVEL_THRESHOLDS
    single_leg_stand_s: float  # seconds, eyes open; gates balance progression


@dataclass
class IntakeAssessment:
    age: int
    sex: Sex                          # required: STS thresholds are keyed by (age_band, sex)
    parq_flags: list[str]             # any entry → route to clearance, no program
    medication_class: MedicationClass
    joint_flags: list[JointFlag]
    functional_tests: FunctionalTests
    days_per_week: int
    minutes_per_session: int
    fall_risk: bool = False           # self-reported or clinician-flagged; suppresses high-impact
    equipment: list[EquipmentItem] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)


# ── Clinical constants ────────────────────────────────────────────────────────

# Source: ADA Standards of Care 2024, Section 5 (Physical Activity); Colberg et al.
# "Physical Activity/Exercise and Diabetes," Diabetes Care 2016 (ACSM/ADA joint
# position statement). Insulin, sulfonylureas, and meglitinides stimulate insulin
# secretion independent of glucose concentration; aerobic exercise amplifies the
# drop and can precipitate hypoglycemia. Metformin, DPP-4i, GLP-1 RA, and SGLT2i
# do not carry this profile and are correctly excluded. Backed by clinical consensus.
HYPO_RISK_MEDICATIONS: frozenset[MedicationClass] = frozenset({
    MedicationClass.INSULIN,
    MedicationClass.SULFONYLUREA,
    MedicationClass.MEGLITINIDE,
})


# 30-Second Chair Stand Test (30CST) programming thresholds, keyed by (age_band, sex).
#
# Reviewed entries are STSBandNorms instances. Unreviewed entries are None.
# The engine must raise ValueError (not silently fall back) when it encounters None.
#
# How boundaries are set:
#   level-2/3 boundary — lower bound of the Rikli & Jones (1999) normal range for
#     that band and sex (≈ 25th percentile). This is the cited value.
#     NOTE: These are the 1999 normative ranges, NOT the 2013 single independence
#     cut-point. The 2013 paper (Table 7) produces a different construct. Verify
#     level-2/3 values against the physical copy of Rikli & Jones 1999 before use.
#   level-1/2 boundary — ceil(lower_bound × 0.6); identifies scores where chair
#     assistance is likely needed. Scaling rule: physician-set 2026-06-10.
#     Rationale: fixed offset (−4) is too permissive for the oldest/weakest bands,
#     which is the opposite of where fall-risk caution is most needed.
#
# Reference: Rikli RE, Jones CJ. Development and validation of criterion-referenced
#   clinically relevant fitness standards for maintaining physical independence in
#   later years. Gerontologist. 2013;53(2):255-267. (Normative ranges: 1999 edition.)
STS_LEVEL_THRESHOLDS: dict[AgeSexBand, STSBandNorms | None] = {

    # 60–64 — primary target cohort
    # Normal range lower bound (Rikli & Jones 1999): men ≥14, women ≥12
    AgeSexBand(60, 64, Sex.MALE): STSBandNorms(
        level_thresholds=(
            (9, 1),   # <9  → level 1 (chair-assisted); ceil(14 × 0.6) = 9
            (14, 2),  # <14 → level 2; ≥14 = lower bound of normal range
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(14 × 0.6) = 9, physician-set 2026-06-10"
        ),
    ),
    AgeSexBand(60, 64, Sex.FEMALE): STSBandNorms(
        level_thresholds=(
            (8, 1),   # <8  → level 1 (chair-assisted); ceil(12 × 0.6) = 8
            (12, 2),  # <12 → level 2; ≥12 = lower bound of normal range
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(12 × 0.6) = 8, physician-set 2026-06-10"
        ),
    ),

    # 65–69 — normal range lower bound: men ≥12, women ≥11
    AgeSexBand(65, 69, Sex.MALE): STSBandNorms(
        level_thresholds=(
            (8, 1),   # ceil(12 × 0.6) = 8
            (12, 2),
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(12 × 0.6) = 8, physician-set 2026-06-10"
        ),
    ),
    AgeSexBand(65, 69, Sex.FEMALE): STSBandNorms(
        level_thresholds=(
            (7, 1),   # ceil(11 × 0.6) = 7
            (11, 2),
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(11 × 0.6) = 7, physician-set 2026-06-10"
        ),
    ),

    # 70–74 — normal range lower bound: men ≥12, women ≥10
    AgeSexBand(70, 74, Sex.MALE): STSBandNorms(
        level_thresholds=(
            (8, 1),   # ceil(12 × 0.6) = 8
            (12, 2),
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(12 × 0.6) = 8, physician-set 2026-06-10"
        ),
    ),
    AgeSexBand(70, 74, Sex.FEMALE): STSBandNorms(
        level_thresholds=(
            (6, 1),   # ceil(10 × 0.6) = 6
            (10, 2),
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(10 × 0.6) = 6, physician-set 2026-06-10"
        ),
    ),

    # 75–79 — normal range lower bound: men ≥11, women ≥10
    AgeSexBand(75, 79, Sex.MALE): STSBandNorms(
        level_thresholds=(
            (7, 1),   # ceil(11 × 0.6) = 7
            (11, 2),
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(11 × 0.6) = 7, physician-set 2026-06-10"
        ),
    ),
    AgeSexBand(75, 79, Sex.FEMALE): STSBandNorms(
        level_thresholds=(
            (6, 1),   # ceil(10 × 0.6) = 6
            (10, 2),
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(10 × 0.6) = 6, physician-set 2026-06-10"
        ),
    ),

    # 80–84 — normal range lower bound: men ≥10, women ≥9
    AgeSexBand(80, 84, Sex.MALE): STSBandNorms(
        level_thresholds=(
            (6, 1),   # ceil(10 × 0.6) = 6
            (10, 2),
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(10 × 0.6) = 6, physician-set 2026-06-10"
        ),
    ),
    AgeSexBand(80, 84, Sex.FEMALE): STSBandNorms(
        level_thresholds=(
            (6, 1),   # ceil(9 × 0.6) = 6
            (9, 2),
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(9 × 0.6) = 6, physician-set 2026-06-10"
        ),
    ),

    # 85–89 — normal range lower bound: men ≥8, women ≥8
    AgeSexBand(85, 89, Sex.MALE): STSBandNorms(
        level_thresholds=(
            (5, 1),   # ceil(8 × 0.6) = 5
            (8, 2),
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(8 × 0.6) = 5, physician-set 2026-06-10"
        ),
    ),
    AgeSexBand(85, 89, Sex.FEMALE): STSBandNorms(
        level_thresholds=(
            (5, 1),   # ceil(8 × 0.6) = 5
            (8, 2),
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(8 × 0.6) = 5, physician-set 2026-06-10"
        ),
    ),

    # 90–99 — normal range lower bound: men ≥7, women ≥6
    # Note: Rikli & Jones 1999 female 90–94 lower bound is 4 (small-n artifact,
    # n=88). Floored to 6 by physician decision 2026-06-10 as 4 is clinically
    # too permissive for fall-risk caution in this band.
    AgeSexBand(90, 99, Sex.MALE): STSBandNorms(
        level_thresholds=(
            (5, 1),   # ceil(7 × 0.6) = 5
            (7, 2),
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound (level-2/3); "
            "level-1/2: ceil(7 × 0.6) = 5, physician-set 2026-06-10"
        ),
    ),
    AgeSexBand(90, 99, Sex.FEMALE): STSBandNorms(
        level_thresholds=(
            (4, 1),   # ceil(6 × 0.6) = 4
            (6, 2),   # floored from published 4 to 6 — physician decision 2026-06-10
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 1999 normative range lower bound floored 4→6 "
            "(small-n artifact, n=88); physician decision 2026-06-10"
        ),
    ),
}


# Push-up entry-level screen. These are capacity thresholds, not normative cut-points.
# ACSM push-up norms apply to full standard push-ups and cannot map to this
# wall → incline → knee-pushup regression ladder. No exercise-science citation
# exists for this specific ladder. Thresholds confirmed by physician 2026-06-10.
# Each tuple: (rep_count_exclusive_upper_bound, level)
PUSHUP_LEVEL_THRESHOLDS: list[tuple[int, int]] = [
    (6, 1),   # 0–5 reps → level 1 (wall push-up)
    (13, 2),  # 6–12 reps → level 2 (incline / counter)
]
PUSHUP_DEFAULT_LEVEL: int = 3  # ≥13 reps → level 3 (knee push-up entry)


# Contraindication axis 1 — deep knee flexion / compressive load.
# Basis: excessive patellofemoral compressive force at flexion past 90°.
# Triggered by JointFlag.KNEE (symptomatic knee OA, post-surgical knee,
# significant patellofemoral pain syndrome).
# Depth criterion: past 90° flexion (physician decision 2026-06-10).
# "deep_lunge" is depth-qualified, not categorically excluded — it is on this
# list because the standard execution goes well past 90°. The substitute
# (box_squat) is the depth-limited variant and is the safe replacement.
DEEP_KNEE_FLEXION_EXERCISE_IDS: frozenset[str] = frozenset({
    "bodyweight_squat",
    "deep_lunge",
    "bulgarian_split_squat",
    "pistol_squat",
})

# Contraindication axis 2 — high impact / ground-reaction force.
# Basis: peak ground-reaction forces that stress the lower extremity independent
# of range of motion. Relevant for osteoporosis, joint replacement, acute bone
# stress, and poorly controlled hypertension during exercise.
# JointFlag.KNEE auto-triggers this axis (physician decision 2026-06-10): you do
# not prescribe jumping to a patient who reports knee trouble. Fall risk and low
# balance score also trigger it independently (see safety.py).
# Expand this set as plyometric exercises are added to library/.
HIGH_IMPACT_EXERCISE_IDS: frozenset[str] = frozenset({
    "jump_squat",
})

# Source: CLAUDE.md §Engine rules ("substitutes the box-squat/glute-bridge regression").
# Product-mandated by the physician-owner; not drawn from an exercise-medicine guideline.
# Clinical confirmation that this pair is appropriate for the target population
# (60-year-old adult with T2D, possible knee OA) is assumed but not formally documented.
KNEE_FLAG_SQUAT_SUBSTITUTES: list[str] = ["box_squat", "glute_bridge"]


# ── Program and session output types ─────────────────────────────────────────

@dataclass
class ExerciseInstance:
    exercise_id: str
    sets: int
    reps_or_time: str
    rest_s: int
    target_rpe: float
    regression_alt: str   # exercise_id — must never be empty (CLAUDE.md invariant)
    progression_alt: str  # exercise_id — must never be empty (CLAUDE.md invariant)


@dataclass
class Block:
    name: str  # "warmup" | "main" | "cooldown" | "walk"
    exercises: list[ExerciseInstance]


@dataclass
class Session:
    week: int
    day: int
    blocks: list[Block]
    glucose_check_required: bool  # True for every session when hypo_risk=elevated
    preferred_window: str | None  # post-meal window tag when available


@dataclass
class Week:
    week_number: int
    sessions: list[Session]
    is_deload: bool = False


@dataclass
class Program:
    weeks: list[Week]
    engine_version: str        # stamped at generation time for auditability
    rules_applied: list[str]   # auditable by clinician; never produce unexplained output
    hypo_risk: HypoRisk


@dataclass
class GenerationResult:
    clearance_required: bool
    clearance_reason: str | None
    program: Program | None   # None when clearance_required is True
