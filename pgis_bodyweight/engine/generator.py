from __future__ import annotations
from .types import (
    IntakeAssessment,
    GenerationResult,
    Program,
    Week,
    Session,
    Block,
    ExerciseInstance,
    HypoRisk,
    JointFlag,
    MovementPattern,
)
from .safety import check_parq, resolve_hypo_risk, is_impact_suppressed
from .patterns import resolve_starting_levels

ENGINE_VERSION = "0.1.0"


# ── Minimal exercise catalog ──────────────────────────────────────────────────
# Temporary until library/ module is built (Phase 2). Every ExerciseInstance
# must carry non-empty regression_alt and progression_alt (CLAUDE.md invariant).
#
# Invariant enforced here: no exercise ID in any knee-safe map (_SQUAT_KNEE_SAFE,
# warmup, cooldown, or any non-squat pattern) appears in
# DEEP_KNEE_FLEXION_EXERCISE_IDS or HIGH_IMPACT_EXERCISE_IDS.
# The standard squat map intentionally uses bodyweight_squat — it is only selected
# for users without JointFlag.KNEE.

def _ex(eid, sets, reps, rest, rpe, reg, prog) -> ExerciseInstance:
    return ExerciseInstance(eid, sets, reps, rest, rpe, reg, prog)


# Squat — standard (JointFlag.KNEE not set)
_SQUAT_STANDARD: dict[int, ExerciseInstance] = {
    1: _ex("chair_assisted_sit_to_stand", 2, "8 reps",  60, 5.0,
           "seated_marching",             "box_squat"),
    2: _ex("box_squat",                   2, "10 reps", 60, 6.0,
           "chair_assisted_sit_to_stand", "bodyweight_squat"),
    3: _ex("bodyweight_squat",            3, "12 reps", 60, 7.0,
           "box_squat",                   "goblet_squat"),
}

# Squat — knee-safe (JointFlag.KNEE set).
# No entry contains any ID from DEEP_KNEE_FLEXION_EXERCISE_IDS or
# HIGH_IMPACT_EXERCISE_IDS — including regression_alt and progression_alt.
_SQUAT_KNEE_SAFE: dict[int, ExerciseInstance] = {
    1: _ex("chair_assisted_sit_to_stand", 2, "8 reps",  60, 5.0,
           "seated_marching",             "box_squat"),
    2: _ex("box_squat",                   2, "10 reps", 60, 6.0,
           "chair_assisted_sit_to_stand", "glute_bridge"),
    3: _ex("glute_bridge",                3, "15 reps", 60, 6.0,
           "box_squat",                   "single_leg_glute_bridge"),
}

_HINGE: dict[int, ExerciseInstance] = {
    1: _ex("hip_hinge_bodyweight",      2, "10 reps",          60, 5.0,
           "seated_good_morning",       "romanian_deadlift_band"),
    2: _ex("romanian_deadlift_band",    2, "10 reps",          60, 6.0,
           "hip_hinge_bodyweight",      "single_leg_deadlift_assist"),
    3: _ex("single_leg_deadlift_assist",3, "8 reps per side",  60, 7.0,
           "romanian_deadlift_band",    "single_leg_deadlift"),
}

_PUSH: dict[int, ExerciseInstance] = {
    1: _ex("wall_pushup",     2, "10 reps", 60, 5.0, "wall_press_isometric", "incline_pushup"),
    2: _ex("incline_pushup",  2, "10 reps", 60, 6.0, "wall_pushup",          "knee_pushup"),
    3: _ex("knee_pushup",     3, "10 reps", 60, 7.0, "incline_pushup",       "full_pushup"),
}

_PULL: dict[int, ExerciseInstance] = {
    1: _ex("band_row",    2, "10 reps", 60, 5.0, "seated_row_isometric", "door_row"),
    2: _ex("door_row",    2, "10 reps", 60, 6.0, "band_row",             "incline_row"),
    3: _ex("incline_row", 3, "10 reps", 60, 7.0, "door_row",             "inverted_row"),
}

_CORE: dict[int, ExerciseInstance] = {
    1: _ex("dead_bug",    2, "5 reps per side",  60, 5.0, "supine_heel_slide", "bird_dog"),
    2: _ex("bird_dog",    2, "8 reps per side",  60, 6.0, "dead_bug",          "plank_hold"),
    3: _ex("plank_hold",  3, "20 s",             60, 7.0, "bird_dog",          "side_plank"),
}

_BALANCE: dict[int, ExerciseInstance] = {
    1: _ex("single_leg_stand_assist",    2, "20 s per side",  60, 4.0,
           "seated_heel_raise",          "single_leg_stand"),
    2: _ex("single_leg_stand",           2, "30 s per side",  60, 5.0,
           "single_leg_stand_assist",    "single_leg_balance_reach"),
    3: _ex("single_leg_balance_reach",   3, "10 reps per side", 60, 6.0,
           "single_leg_stand",           "single_leg_deadlift"),
}

_WARMUP_EXERCISES: list[ExerciseInstance] = [
    _ex("march_in_place",  1, "60 s",             0, 3.0, "seated_march",        "high_knee_march"),
    _ex("hip_circle",      1, "10 reps per side", 0, 3.0, "seated_hip_circle",   "lateral_hip_swing"),
    _ex("shoulder_roll",   1, "10 reps",          0, 3.0, "seated_shoulder_roll","arm_circle"),
]

_COOLDOWN_EXERCISES: list[ExerciseInstance] = [
    _ex("seated_hamstring_stretch", 1, "30 s per side", 0, 2.0,
        "supine_hamstring_stretch", "standing_hamstring_stretch"),
    _ex("chest_opener_stretch",     1, "30 s",          0, 2.0,
        "doorway_chest_stretch",    "arm_across_chest_stretch"),
    _ex("ankle_circles",            1, "10 reps per side", 0, 2.0,
        "seated_ankle_circles",     "standing_ankle_circles"),
]


# ── Public entry point ────────────────────────────────────────────────────────

def generate_mesocycle(intake: IntakeAssessment) -> GenerationResult:
    """
    Generate a 4-week mesocycle from a completed intake.

    Pure: no network, no DB, no file I/O, no randomness, no clock reads.
    Same input always produces the same output.

    Steps (PRD §7):
      1. Safety gate — PAR-Q flags → clearance_required, no program
      2. Per-pattern starting levels from functional tests (raises on unreviewed band)
      3. Dose from constraints (days/week × minutes/session)
      4. Glycemic layer — hypo_risk branch, glucose-check prompts
      5. Assemble 4-week mesocycle with deload on week 4
    """
    # Step 1 — safety gate
    clearance_required, clearance_reason = check_parq(intake)
    if clearance_required:
        return GenerationResult(
            clearance_required=True,
            clearance_reason=clearance_reason,
            program=None,
        )

    # Steps 2-4 — resolve parameters
    hypo_risk = resolve_hypo_risk(intake)
    starting_levels = resolve_starting_levels(intake)
    knee_flagged = JointFlag.KNEE in intake.joint_flags

    # Step 5 — build program
    weeks = _build_mesocycle(intake, starting_levels, hypo_risk, knee_flagged)
    rules = _collect_rules(hypo_risk, knee_flagged, is_impact_suppressed(intake))

    return GenerationResult(
        clearance_required=False,
        clearance_reason=None,
        program=Program(
            weeks=weeks,
            engine_version=ENGINE_VERSION,
            rules_applied=rules,
            hypo_risk=hypo_risk,
        ),
    )


# ── Assembly helpers ──────────────────────────────────────────────────────────

def _build_mesocycle(
    intake: IntakeAssessment,
    levels: dict[MovementPattern, int],
    hypo_risk: HypoRisk,
    knee_flagged: bool,
) -> list[Week]:
    return [
        Week(
            week_number=w,
            sessions=[
                _build_session(w, d, levels, hypo_risk, knee_flagged)
                for d in range(1, intake.days_per_week + 1)
            ],
            is_deload=(w == 4),
        )
        for w in range(1, 5)
    ]


def _build_session(
    week: int,
    day: int,
    levels: dict[MovementPattern, int],
    hypo_risk: HypoRisk,
    knee_flagged: bool,
) -> Session:
    return Session(
        week=week,
        day=day,
        blocks=[
            Block("warmup",   list(_WARMUP_EXERCISES)),
            Block("main",     _select_main(levels, knee_flagged)),
            Block("cooldown", list(_COOLDOWN_EXERCISES)),
        ],
        glucose_check_required=(hypo_risk == HypoRisk.ELEVATED),
        preferred_window=None,
    )


def _select_main(
    levels: dict[MovementPattern, int],
    knee_flagged: bool,
) -> list[ExerciseInstance]:
    squat_map = _SQUAT_KNEE_SAFE if knee_flagged else _SQUAT_STANDARD
    return [
        squat_map[levels[MovementPattern.SQUAT]],
        _HINGE  [levels[MovementPattern.HINGE]],
        _PUSH   [levels[MovementPattern.HORIZONTAL_PUSH]],
        _PULL   [levels[MovementPattern.PULL]],
        _CORE   [levels[MovementPattern.CORE]],
        _BALANCE[levels[MovementPattern.SINGLE_LEG_BALANCE]],
    ]


def _collect_rules(
    hypo_risk: HypoRisk,
    knee_flagged: bool,
    impact_suppressed: bool,
) -> list[str]:
    rules = ["parq_gate_checked", "per_pattern_starting_levels"]
    if hypo_risk == HypoRisk.ELEVATED:
        rules.append("hypo_risk_elevated_glucose_check_all_sessions")
    if knee_flagged:
        rules.append("knee_flag_deep_flexion_exclusion")
        rules.append("knee_flag_high_impact_exclusion")
        rules.append("knee_flag_squat_substitution")
    if impact_suppressed:
        rules.append("high_impact_suppressed_phase1_default")
    return rules
