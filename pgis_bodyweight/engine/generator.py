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
from pgis_bodyweight.library import load_fixed_block, load_pattern_ladder, load_squat_ladders

ENGINE_VERSION = "0.1.0"


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
            Block("warmup",   load_fixed_block("warmup.yaml")),
            Block("main",     _select_main(levels, knee_flagged)),
            Block("cooldown", load_fixed_block("cooldown.yaml")),
        ],
        glucose_check_required=(hypo_risk == HypoRisk.ELEVATED),
        preferred_window=None,
    )


def _select_main(
    levels: dict[MovementPattern, int],
    knee_flagged: bool,
) -> list[ExerciseInstance]:
    squat_standard, squat_knee_safe = load_squat_ladders()
    squat_map = squat_knee_safe if knee_flagged else squat_standard
    return [
        squat_map[levels[MovementPattern.SQUAT]],
        load_pattern_ladder("hinge.yaml")        [levels[MovementPattern.HINGE]],
        load_pattern_ladder("horizontal_push.yaml")[levels[MovementPattern.HORIZONTAL_PUSH]],
        load_pattern_ladder("pull.yaml")          [levels[MovementPattern.PULL]],
        load_pattern_ladder("core.yaml")          [levels[MovementPattern.CORE]],
        load_pattern_ladder("single_leg_balance.yaml")[levels[MovementPattern.SINGLE_LEG_BALANCE]],
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
