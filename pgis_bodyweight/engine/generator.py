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
from pgis_bodyweight.library import (
    load_fixed_block,
    load_squat_ladders,
    load_hinge_ladders,
    load_push_ladders,
    load_pull_ladders,
    load_core_ladders,
    load_balance_ladders,
)

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
    joint_flags = frozenset(intake.joint_flags)

    # Step 5 — build program
    weeks = _build_mesocycle(intake, starting_levels, hypo_risk, joint_flags)
    rules = _collect_rules(hypo_risk, joint_flags, is_impact_suppressed(intake))

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
    joint_flags: frozenset[JointFlag],
) -> list[Week]:
    return [
        Week(
            week_number=w,
            sessions=[
                _build_session(w, d, levels, hypo_risk, joint_flags)
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
    joint_flags: frozenset[JointFlag],
) -> Session:
    return Session(
        week=week,
        day=day,
        blocks=[
            Block("warmup",   load_fixed_block("warmup.yaml")),
            Block("main",     _select_main(levels, joint_flags)),
            Block("cooldown", load_fixed_block("cooldown.yaml")),
        ],
        glucose_check_required=(hypo_risk == HypoRisk.ELEVATED),
        preferred_window=None,
    )


def _select_main(
    levels: dict[MovementPattern, int],
    joint_flags: frozenset[JointFlag],
) -> list[ExerciseInstance]:
    squat_std, squat_knee     = load_squat_ladders()
    hinge_std, hinge_lb       = load_hinge_ladders()
    push_std, push_sh, push_wr = load_push_ladders()
    pull_std, pull_sh         = load_pull_ladders()
    core_std, core_lb         = load_core_ladders()
    balance_std, balance_hip  = load_balance_ladders()

    squat_map   = squat_knee  if JointFlag.KNEE        in joint_flags else squat_std
    hinge_map   = hinge_lb    if JointFlag.LOWER_BACK  in joint_flags else hinge_std
    push_map    = (push_wr    if JointFlag.WRIST        in joint_flags
                  else push_sh if JointFlag.SHOULDER    in joint_flags
                  else push_std)
    pull_map    = pull_sh     if JointFlag.SHOULDER    in joint_flags else pull_std
    core_map    = core_lb     if JointFlag.LOWER_BACK  in joint_flags else core_std
    balance_map = balance_hip if JointFlag.HIP         in joint_flags else balance_std

    return [
        squat_map  [levels[MovementPattern.SQUAT]],
        hinge_map  [levels[MovementPattern.HINGE]],
        push_map   [levels[MovementPattern.HORIZONTAL_PUSH]],
        pull_map   [levels[MovementPattern.PULL]],
        core_map   [levels[MovementPattern.CORE]],
        balance_map[levels[MovementPattern.SINGLE_LEG_BALANCE]],
    ]


def _collect_rules(
    hypo_risk: HypoRisk,
    joint_flags: frozenset[JointFlag],
    impact_suppressed: bool,
) -> list[str]:
    rules = ["parq_gate_checked", "per_pattern_starting_levels"]
    if hypo_risk == HypoRisk.ELEVATED:
        rules.append("hypo_risk_elevated_glucose_check_all_sessions")
    if JointFlag.KNEE in joint_flags:
        rules.append("knee_flag_deep_flexion_exclusion")
        rules.append("knee_flag_high_impact_exclusion")
        rules.append("knee_flag_squat_substitution")
    if JointFlag.LOWER_BACK in joint_flags:
        rules.append("lower_back_flag_hinge_substitution")
        rules.append("lower_back_flag_core_restriction")
    if JointFlag.HIP in joint_flags:
        rules.append("hip_flag_balance_progression_cap")
    if JointFlag.SHOULDER in joint_flags:
        rules.append("shoulder_flag_push_modification")
        rules.append("shoulder_flag_pull_band_only")
    if JointFlag.WRIST in joint_flags:
        rules.append("wrist_flag_push_band_only")
    if impact_suppressed:
        rules.append("high_impact_suppressed_phase1_default")
    return rules
