from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


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


@dataclass
class FunctionalTests:
    sit_to_stand_count: int    # reps in 30 s; drives squat starting level
    pushup_max: int            # wall/incline max reps; drives push starting level
    single_leg_stand_s: float  # seconds, eyes open; gates balance progression


@dataclass
class IntakeAssessment:
    age: int
    parq_flags: list[str]           # any entry → route to clearance, no program
    medication_class: MedicationClass
    joint_flags: list[JointFlag]
    functional_tests: FunctionalTests
    days_per_week: int
    minutes_per_session: int
    equipment: list[EquipmentItem] = field(default_factory=list)


# Medications that cause exercise-induced hypoglycemia (PRD §5, §7 Step 1)
HYPO_RISK_MEDICATIONS: frozenset[MedicationClass] = frozenset({
    MedicationClass.INSULIN,
    MedicationClass.SULFONYLUREA,
    MedicationClass.MEGLITINIDE,
})

# Sit-to-stand count thresholds → squat starting level (PRD §7 Step 2)
# Each tuple: (count_exclusive_upper_bound, level)
STS_LEVEL_THRESHOLDS: list[tuple[int, int]] = [
    (8, 1),   # <8  → level 1: chair-assisted sit-to-stand
    (15, 2),  # 8–14 → level 2: box squat
]
STS_DEFAULT_LEVEL: int = 3  # 15+ → level 3: bodyweight squat

# Push-up max thresholds → horizontal push starting level (PRD §7 Step 2)
PUSHUP_LEVEL_THRESHOLDS: list[tuple[int, int]] = [
    (6, 1),   # 0–5  → level 1: wall push-up
    (13, 2),  # 6–12 → level 2: incline / counter push-up
]
PUSHUP_DEFAULT_LEVEL: int = 3  # 13+ → level 3: knee → full push-up progression

# Exercise IDs contraindicated when JointFlag.KNEE is set (PRD §7 Step 3)
# REVIEW: confirm this list against the exercise library when library/ is seeded
DEEP_KNEE_DOMINANT_EXERCISE_IDS: frozenset[str] = frozenset({
    "bodyweight_squat",
    "jump_squat",
    "deep_lunge",
    "bulgarian_split_squat",
    "pistol_squat",
})

# Required substitutes when knee flag is active (CLAUDE.md §Engine rules #2)
KNEE_FLAG_SQUAT_SUBSTITUTES: list[str] = ["box_squat", "glute_bridge"]


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
    engine_version: str   # stamped at generation time for auditability
    rules_applied: list[str]  # human-readable list of rules used; auditable by clinician
    hypo_risk: HypoRisk


@dataclass
class GenerationResult:
    clearance_required: bool
    clearance_reason: str | None
    program: Program | None  # None when clearance_required is True
