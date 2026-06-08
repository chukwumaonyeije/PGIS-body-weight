from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple


# ── Enumerations ──────────────────────────────────────────────────────────────

class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    # REVIEW: the intake form should handle non-binary and prefer-not-to-say
    # responses. Rikli & Jones norms are binary (male/female); when this is
    # resolved, apply the FEMALE (lower-threshold) set as the conservative default.


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
    equipment: list[EquipmentItem] = field(default_factory=list)


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
# How boundaries are set for reviewed bands:
#   level-2/3 boundary — anchored to the Rikli & Jones lower bound of the "normal"
#     (average) range for that band and sex. This is a cited value.
#   level-1/2 boundary — a sub-classification within the Rikli & Jones "below average"
#     range, intended to identify scores where chair assistance is likely needed.
#     This sub-boundary is implementer judgment and is marked REVIEW on each entry.
#
# Reference: Rikli & Jones, "Senior Fitness Test Manual," 2nd ed.,
#            Human Kinetics, 2013, Table 7 (30-Second Chair Stand normative data).
STS_LEVEL_THRESHOLDS: dict[AgeSexBand, STSBandNorms | None] = {

    # 60–64 — primary target cohort
    # Rikli & Jones 2013 normal range: men 14–19, women 12–17
    # Below average: men ≤13, women ≤11
    AgeSexBand(60, 64, Sex.MALE): STSBandNorms(
        level_thresholds=(
            (10, 1),  # REVIEW: clinical value needed — <10 → level 1 (chair-assisted);
                      # this lower sub-band within below-average (≤13) is implementer
                      # judgment; no Rikli & Jones value distinguishes it
            (14, 2),  # anchored: Rikli & Jones 2013 — below-average upper bound for
                      # men 60–64 is ≤13; score ≥14 = lower bound of normal range
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 2013 Table 7 (level-2/3 boundary); "
            "level-1/2 boundary is implementer judgment — REVIEW"
        ),
    ),
    AgeSexBand(60, 64, Sex.FEMALE): STSBandNorms(
        level_thresholds=(
            (8, 1),   # REVIEW: clinical value needed — <8 → level 1 (chair-assisted);
                      # this lower sub-band within below-average (≤11) is implementer
                      # judgment; no Rikli & Jones value distinguishes it
            (12, 2),  # anchored: Rikli & Jones 2013 — below-average upper bound for
                      # women 60–64 is ≤11; score ≥12 = lower bound of normal range
        ),
        top_level=3,
        citation=(
            "Rikli & Jones 2013 Table 7 (level-2/3 boundary); "
            "level-1/2 boundary is implementer judgment — REVIEW"
        ),
    ),

    # 65–69 — REVIEW: clinical value needed — fill from Rikli & Jones 2013 Table 7
    AgeSexBand(65, 69, Sex.MALE): None,
    AgeSexBand(65, 69, Sex.FEMALE): None,

    # 70–74 — REVIEW: clinical value needed — fill from Rikli & Jones 2013 Table 7
    AgeSexBand(70, 74, Sex.MALE): None,
    AgeSexBand(70, 74, Sex.FEMALE): None,

    # 75–79 — REVIEW: clinical value needed — fill from Rikli & Jones 2013 Table 7
    AgeSexBand(75, 79, Sex.MALE): None,
    AgeSexBand(75, 79, Sex.FEMALE): None,

    # 80–84 — REVIEW: clinical value needed — fill from Rikli & Jones 2013 Table 7
    AgeSexBand(80, 84, Sex.MALE): None,
    AgeSexBand(80, 84, Sex.FEMALE): None,

    # 85–89 — REVIEW: clinical value needed — fill from Rikli & Jones 2013 Table 7
    AgeSexBand(85, 89, Sex.MALE): None,
    AgeSexBand(85, 89, Sex.FEMALE): None,

    # 90+ — REVIEW: clinical value needed — fill from Rikli & Jones 2013 Table 7
    AgeSexBand(90, 99, Sex.MALE): None,
    AgeSexBand(90, 99, Sex.FEMALE): None,
}


# REVIEW: clinical value needed — these cutoffs are coaching-derived approximations
# from PRD §7 Step 2 ("e.g." language). They are NOT from a clinical normative
# reference and have no citation in exercise-science literature.
# ACSM push-up norms (ACSM's Guidelines for Exercise Testing and Prescription,
# 11th ed.) apply to full standard push-ups, not to the wall→incline→knee regression
# ladder used here and cannot be mapped to these thresholds.
# A physician must confirm these values before clinical use.
# Each tuple: (rep_count_exclusive_upper_bound, level)
PUSHUP_LEVEL_THRESHOLDS: list[tuple[int, int]] = [
    (6, 1),   # REVIEW: clinical value needed — 0–5 → level 1 (wall push-up)
    (13, 2),  # REVIEW: clinical value needed — 6–12 → level 2 (incline / counter)
]
PUSHUP_DEFAULT_LEVEL: int = 3  # REVIEW: clinical value needed — ≥13 → level 3 (knee → full)


# Contraindication axis 1 — deep knee flexion / compressive load.
# Basis: excessive patellofemoral compressive force and/or range-of-motion demand
# that is unsafe for symptomatic knee OA, post-surgical knees, or significant
# patellofemoral pain syndrome. Triggered by JointFlag.KNEE.
# REVIEW: clinical value needed — list is implementer-generated.
# A physician must confirm: (a) which specific knee conditions trigger this axis,
# (b) the flexion-depth criterion that qualifies as "deep" (e.g., past 90°?),
# (c) whether deep_lunge requires a depth qualifier or is categorically excluded.
DEEP_KNEE_FLEXION_EXERCISE_IDS: frozenset[str] = frozenset({
    "bodyweight_squat",
    "deep_lunge",             # REVIEW: "deep" is undefined — depth criterion needed
    "bulgarian_split_squat",
    "pistol_squat",
})

# Contraindication axis 2 — high impact / ground-reaction force.
# Basis: peak ground-reaction forces that stress the lower extremity independent
# of range of motion. Relevant for osteoporosis, joint replacement, acute bone
# stress, and poorly controlled hypertension during exercise.
# REVIEW: clinical value needed — list is implementer-generated.
# Open design question: should JointFlag.KNEE trigger this axis automatically,
# or should high-impact be a separate intake flag? Many knee-OA patients also
# cannot tolerate impact, but the reasons are distinct. Physician decision required.
# A physician must also confirm: (a) which clinical conditions trigger this axis,
# (b) what other exercises belong here once library/ is seeded.
HIGH_IMPACT_EXERCISE_IDS: frozenset[str] = frozenset({
    "jump_squat",
    # REVIEW: clinical value needed — add other plyometric/impact exercises
    # (box jumps, plyometric lunges, bounding) once library/ is seeded
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
