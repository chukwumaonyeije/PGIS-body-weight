"""
Safety-invariant tests for the program-generation engine.

Written RED first (TDD). Every class here encodes a guarantee from
CLAUDE.md §Engine rules that must never break — not even under refactor.

Run: pytest
All tests must fail (NotImplementedError) until the engine is implemented.
"""
import pytest

from pgis_bodyweight.engine.types import (
    IntakeAssessment,
    FunctionalTests,
    MedicationClass,
    JointFlag,
    HypoRisk,
    MovementPattern,
    DEEP_KNEE_DOMINANT_EXERCISE_IDS,
)
from pgis_bodyweight.engine.generator import generate_mesocycle
from pgis_bodyweight.engine.safety import check_parq, resolve_hypo_risk
from pgis_bodyweight.engine.patterns import resolve_starting_levels


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_intake(**overrides) -> IntakeAssessment:
    """Minimal intake with no flags and mid-range functional scores."""
    defaults = dict(
        age=60,
        parq_flags=[],
        medication_class=MedicationClass.METFORMIN_ONLY,
        joint_flags=[],
        functional_tests=FunctionalTests(
            sit_to_stand_count=10,
            pushup_max=8,
            single_leg_stand_s=10.0,
        ),
        days_per_week=3,
        minutes_per_session=20,
    )
    defaults.update(overrides)
    return IntakeAssessment(**defaults)


def _all_exercise_ids(result) -> set[str]:
    ids: set[str] = set()
    for week in result.program.weeks:
        for session in week.sessions:
            for block in session.blocks:
                for ex in block.exercises:
                    ids.add(ex.exercise_id)
    return ids


def _all_sessions(result) -> list:
    return [s for week in result.program.weeks for s in week.sessions]


# ---------------------------------------------------------------------------
# Invariant 1 — PAR-Q gate (CLAUDE.md: "A red-flag intake NEVER yields a program")
# ---------------------------------------------------------------------------

class TestParqGate:
    def test_single_red_flag_yields_no_program(self):
        intake = _clean_intake(parq_flags=["chest_pain_with_exertion"])
        result = generate_mesocycle(intake)
        assert result.clearance_required is True
        assert result.program is None

    def test_multiple_red_flags_yields_no_program(self):
        intake = _clean_intake(parq_flags=["recent_cardiac_event", "uncontrolled_dizziness"])
        result = generate_mesocycle(intake)
        assert result.clearance_required is True
        assert result.program is None

    def test_red_flag_result_carries_reason(self):
        intake = _clean_intake(parq_flags=["bone_joint_condition"])
        result = generate_mesocycle(intake)
        assert result.clearance_reason is not None and len(result.clearance_reason) > 0

    def test_clean_intake_yields_program(self):
        intake = _clean_intake()
        result = generate_mesocycle(intake)
        assert result.clearance_required is False
        assert result.program is not None

    def test_check_parq_returns_true_for_flag(self):
        intake = _clean_intake(parq_flags=["chest_pain_with_exertion"])
        required, reason = check_parq(intake)
        assert required is True
        assert reason is not None and len(reason) > 0

    def test_check_parq_returns_false_for_clean(self):
        intake = _clean_intake()
        required, reason = check_parq(intake)
        assert required is False
        assert reason is None


# ---------------------------------------------------------------------------
# Invariant 2 — Knee flag substitution
# (CLAUDE.md: "A knee flag NEVER yields deep/loaded knee-dominant movements;
#  it substitutes the box-squat/glute-bridge regression")
# ---------------------------------------------------------------------------

class TestKneeFlag:
    def test_knee_flag_excludes_contraindicated_exercises(self):
        intake = _clean_intake(joint_flags=[JointFlag.KNEE])
        result = generate_mesocycle(intake)
        assert result.program is not None

        prescribed = _all_exercise_ids(result)
        forbidden = DEEP_KNEE_DOMINANT_EXERCISE_IDS & prescribed
        assert forbidden == set(), (
            f"Knee-flagged program contains contraindicated exercises: {forbidden}"
        )

    def test_knee_flag_substitutes_box_squat_or_glute_bridge(self):
        intake = _clean_intake(joint_flags=[JointFlag.KNEE])
        result = generate_mesocycle(intake)
        assert result.program is not None

        prescribed = _all_exercise_ids(result)
        assert prescribed & {"box_squat", "glute_bridge"}, (
            "Knee-flagged program must include box_squat or glute_bridge as the squat substitute"
        )

    def test_no_knee_flag_allows_full_squat_at_level_3(self):
        """Level-3 squat (sit_to_stand ≥15) without a knee flag must prescribe a real squat."""
        intake = _clean_intake(
            joint_flags=[],
            functional_tests=FunctionalTests(
                sit_to_stand_count=16,
                pushup_max=8,
                single_leg_stand_s=10.0,
            ),
        )
        result = generate_mesocycle(intake)
        assert result.program is not None
        prescribed = _all_exercise_ids(result)
        assert prescribed & {"bodyweight_squat", "goblet_squat"}, (
            "Level-3 squat + no knee flag must yield a full squat pattern exercise"
        )


# ---------------------------------------------------------------------------
# Invariant 3 — Hypo-risk medication branch
# (CLAUDE.md: "Insulin / sulfonylurea / meglitinide ALWAYS sets hypo_risk=elevated
#  and attaches a pre-session glucose-check prompt to every session")
# ---------------------------------------------------------------------------

class TestHypoRiskBranch:
    @pytest.mark.parametrize("med", [
        MedicationClass.INSULIN,
        MedicationClass.SULFONYLUREA,
        MedicationClass.MEGLITINIDE,
    ])
    def test_hypo_meds_set_elevated_risk_on_program(self, med):
        result = generate_mesocycle(_clean_intake(medication_class=med))
        assert result.program is not None
        assert result.program.hypo_risk == HypoRisk.ELEVATED, (
            f"{med.value} must set program.hypo_risk = ELEVATED"
        )

    @pytest.mark.parametrize("med", [
        MedicationClass.INSULIN,
        MedicationClass.SULFONYLUREA,
        MedicationClass.MEGLITINIDE,
    ])
    def test_hypo_meds_require_glucose_check_on_every_session(self, med):
        result = generate_mesocycle(_clean_intake(medication_class=med))
        assert result.program is not None

        sessions = _all_sessions(result)
        assert sessions, "Program must contain at least one session"

        missing = [s for s in sessions if not s.glucose_check_required]
        assert missing == [], (
            f"{med.value}: {len(missing)} session(s) missing glucose_check_required=True"
        )

    @pytest.mark.parametrize("med", [
        MedicationClass.METFORMIN_ONLY,
        MedicationClass.NONE,
        MedicationClass.OTHER,
    ])
    def test_non_hypo_meds_set_standard_risk(self, med):
        result = generate_mesocycle(_clean_intake(medication_class=med))
        assert result.program is not None
        assert result.program.hypo_risk == HypoRisk.STANDARD

    def test_resolve_hypo_risk_elevated_for_insulin(self):
        intake = _clean_intake(medication_class=MedicationClass.INSULIN)
        assert resolve_hypo_risk(intake) == HypoRisk.ELEVATED

    def test_resolve_hypo_risk_elevated_for_sulfonylurea(self):
        intake = _clean_intake(medication_class=MedicationClass.SULFONYLUREA)
        assert resolve_hypo_risk(intake) == HypoRisk.ELEVATED

    def test_resolve_hypo_risk_elevated_for_meglitinide(self):
        intake = _clean_intake(medication_class=MedicationClass.MEGLITINIDE)
        assert resolve_hypo_risk(intake) == HypoRisk.ELEVATED

    def test_resolve_hypo_risk_standard_for_metformin(self):
        intake = _clean_intake(medication_class=MedicationClass.METFORMIN_ONLY)
        assert resolve_hypo_risk(intake) == HypoRisk.STANDARD


# ---------------------------------------------------------------------------
# Invariant 4 — Per-pattern starting levels from functional tests
# (CLAUDE.md: "Starting levels are set PER MOVEMENT PATTERN from the functional
#  tests — never a single global beginner/intermediate toggle")
# ---------------------------------------------------------------------------

class TestPerPatternStartingLevel:
    def test_all_six_patterns_present(self):
        levels = resolve_starting_levels(_clean_intake())
        for pattern in MovementPattern:
            assert pattern in levels, f"Missing starting level for {pattern}"

    def test_squat_level_1_for_low_sts(self):
        intake = _clean_intake(
            functional_tests=FunctionalTests(sit_to_stand_count=5, pushup_max=8, single_leg_stand_s=10.0)
        )
        assert resolve_starting_levels(intake)[MovementPattern.SQUAT] == 1

    def test_squat_level_2_for_mid_sts(self):
        intake = _clean_intake(
            functional_tests=FunctionalTests(sit_to_stand_count=10, pushup_max=8, single_leg_stand_s=10.0)
        )
        assert resolve_starting_levels(intake)[MovementPattern.SQUAT] == 2

    def test_squat_level_3_for_high_sts(self):
        intake = _clean_intake(
            functional_tests=FunctionalTests(sit_to_stand_count=15, pushup_max=8, single_leg_stand_s=10.0)
        )
        assert resolve_starting_levels(intake)[MovementPattern.SQUAT] == 3

    def test_push_level_1_for_low_pushup(self):
        intake = _clean_intake(
            functional_tests=FunctionalTests(sit_to_stand_count=10, pushup_max=3, single_leg_stand_s=10.0)
        )
        assert resolve_starting_levels(intake)[MovementPattern.HORIZONTAL_PUSH] == 1

    def test_push_level_2_for_mid_pushup(self):
        intake = _clean_intake(
            functional_tests=FunctionalTests(sit_to_stand_count=10, pushup_max=9, single_leg_stand_s=10.0)
        )
        assert resolve_starting_levels(intake)[MovementPattern.HORIZONTAL_PUSH] == 2

    def test_push_level_3_for_high_pushup(self):
        intake = _clean_intake(
            functional_tests=FunctionalTests(sit_to_stand_count=10, pushup_max=15, single_leg_stand_s=10.0)
        )
        assert resolve_starting_levels(intake)[MovementPattern.HORIZONTAL_PUSH] == 3

    def test_squat_and_push_levels_are_independent(self):
        """High squat + low push must not produce the same level for both patterns."""
        intake = _clean_intake(
            functional_tests=FunctionalTests(
                sit_to_stand_count=16,  # → squat level 3
                pushup_max=3,           # → push level 1
                single_leg_stand_s=8.0,
            )
        )
        levels = resolve_starting_levels(intake)
        assert levels[MovementPattern.SQUAT] != levels[MovementPattern.HORIZONTAL_PUSH], (
            "Squat and push levels must be set independently; "
            "a high STS + low pushup user must not receive the same level for both"
        )

    def test_squat_level_reflects_sts_not_pushup(self):
        high_sts = _clean_intake(
            functional_tests=FunctionalTests(sit_to_stand_count=16, pushup_max=3, single_leg_stand_s=8.0)
        )
        low_sts = _clean_intake(
            functional_tests=FunctionalTests(sit_to_stand_count=5, pushup_max=3, single_leg_stand_s=8.0)
        )
        high_levels = resolve_starting_levels(high_sts)
        low_levels = resolve_starting_levels(low_sts)
        assert high_levels[MovementPattern.SQUAT] > low_levels[MovementPattern.SQUAT]
        assert high_levels[MovementPattern.HORIZONTAL_PUSH] == low_levels[MovementPattern.HORIZONTAL_PUSH]


# ---------------------------------------------------------------------------
# Invariant 5 — Every prescribed exercise carries regression and progression
# (CLAUDE.md: "Every prescribed exercise carries an inline regression
#  and progression alternate")
# ---------------------------------------------------------------------------

class TestExerciseAlternates:
    def test_every_exercise_has_nonempty_regression_alt(self):
        result = generate_mesocycle(_clean_intake())
        assert result.program is not None
        for week in result.program.weeks:
            for session in week.sessions:
                for block in session.blocks:
                    for ex in block.exercises:
                        assert ex.regression_alt, (
                            f"Exercise {ex.exercise_id!r} (week {week.week_number}, "
                            f"day {session.day}, block {block.name!r}) is missing regression_alt"
                        )

    def test_every_exercise_has_nonempty_progression_alt(self):
        result = generate_mesocycle(_clean_intake())
        assert result.program is not None
        for week in result.program.weeks:
            for session in week.sessions:
                for block in session.blocks:
                    for ex in block.exercises:
                        assert ex.progression_alt, (
                            f"Exercise {ex.exercise_id!r} (week {week.week_number}, "
                            f"day {session.day}, block {block.name!r}) is missing progression_alt"
                        )

    def test_regression_and_progression_are_distinct(self):
        result = generate_mesocycle(_clean_intake())
        assert result.program is not None
        for week in result.program.weeks:
            for session in week.sessions:
                for block in session.blocks:
                    for ex in block.exercises:
                        assert ex.regression_alt != ex.progression_alt, (
                            f"Exercise {ex.exercise_id!r}: regression_alt == progression_alt "
                            f"({ex.regression_alt!r}); they must be different exercises"
                        )


# ---------------------------------------------------------------------------
# Invariant 6 — Determinism (CLAUDE.md: "Same input → same output, always")
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_identical_intake_produces_identical_program(self):
        intake = _clean_intake()
        assert generate_mesocycle(intake) == generate_mesocycle(intake)

    def test_different_intake_may_produce_different_program(self):
        low = _clean_intake(functional_tests=FunctionalTests(5, 3, 8.0))
        high = _clean_intake(functional_tests=FunctionalTests(16, 15, 12.0))
        assert generate_mesocycle(low) != generate_mesocycle(high)


# ---------------------------------------------------------------------------
# Invariant 7 — Auditability (CLAUDE.md: "The engine stamps every generated
#  program with engine_version and the rules applied")
# ---------------------------------------------------------------------------

class TestAuditability:
    def test_program_carries_engine_version(self):
        result = generate_mesocycle(_clean_intake())
        assert result.program is not None
        assert result.program.engine_version, "Every program must carry a non-empty engine_version"

    def test_program_records_rules_applied(self):
        result = generate_mesocycle(_clean_intake())
        assert result.program is not None
        assert isinstance(result.program.rules_applied, list)
        assert len(result.program.rules_applied) > 0, (
            "Program must record at least one rule in rules_applied for clinician auditability"
        )

    def test_red_flag_program_has_no_engine_version(self):
        """Clearance-routed results have no program, so no engine_version to check."""
        result = generate_mesocycle(_clean_intake(parq_flags=["recent_cardiac_event"]))
        assert result.program is None
