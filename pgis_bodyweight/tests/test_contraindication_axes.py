"""
Safety invariants for the two contraindication axes: deep knee flexion and high impact.

These tests are the SPEC for what "green" must mean. They encode clinical intent,
not just current behavior. Do not loosen an assertion to make a test pass — if a
test fails, the engine is wrong, not the test.

Design (decided at the product level):
  - DEEP_KNEE_FLEXION and HIGH_IMPACT are SEPARATE axes with different trigger sets.
  - JointFlag.KNEE IMPLIES impact restriction (you do not prescribe jumping to a
    patient who reports knee trouble), so the knee guarantee covers BOTH lists.
  - HIGH_IMPACT is also restricted by its own triggers, independent of any knee
    flag: fall risk, low balance score, and — for this deconditioned beginner
    population — the default. Impact is EARNED through progression, not a starting
    state. In Phase 1 nothing high-impact appears in anyone's program; the axis
    still must be correct because impact unlocks for advanced users later.
"""

import pytest

from pgis_bodyweight.engine.types import (
    IntakeAssessment,
    FunctionalTests,
    MedicationClass,
    JointFlag,
    Sex,
    DEEP_KNEE_FLEXION_EXERCISE_IDS,
    HIGH_IMPACT_EXERCISE_IDS,
    KNEE_FLAG_SQUAT_SUBSTITUTES,
)
from pgis_bodyweight.engine.generator import generate_mesocycle


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_intake(**overrides) -> IntakeAssessment:
    """
    Build a safe, valid baseline intake that produces a program (no PAR-Q flags,
    no hypo-risk meds), then apply overrides. Keeps each test to the one variable
    it is actually exercising.

    Functional-test fields (sit_to_stand_count, pushup_max, balance_seconds) may
    be passed as flat kwargs; they are assembled into FunctionalTests internally.
    """
    sit_to_stand = overrides.pop("sit_to_stand_count", 15)
    pushup       = overrides.pop("pushup_max", 10)
    balance      = overrides.pop("balance_seconds", 20.0)

    base: dict = dict(
        age=60,
        sex=Sex.MALE,
        parq_flags=[],
        medication_class=MedicationClass.NONE,
        joint_flags=[],
        functional_tests=FunctionalTests(
            sit_to_stand_count=sit_to_stand,
            pushup_max=pushup,
            single_leg_stand_s=balance,
        ),
        fall_risk=False,
        days_per_week=3,
        minutes_per_session=20,
        equipment=[],
        goals=["glucose_control"],
    )
    base.update(overrides)
    return IntakeAssessment(**base)


def all_exercise_ids(result) -> set:
    """
    Flatten every exercise ID in a generated program, including regression and
    progression alternates. An alternate that swaps a contraindicated movement
    back in would defeat the safety rule, so alternates count.
    Returns an empty set when no program was generated.
    """
    if result.program is None:
        return set()
    ids: set[str] = set()
    for week in result.program.weeks:
        for session in week.sessions:
            for block in session.blocks:
                for inst in block.exercises:
                    ids.add(inst.exercise_id)
                    if inst.regression_alt:
                        ids.add(inst.regression_alt)
                    if inst.progression_alt:
                        ids.add(inst.progression_alt)
    return ids


# ---------------------------------------------------------------------------
# Axis 1: knee flag — covers BOTH contraindication lists + substitution
# ---------------------------------------------------------------------------

class TestKneeFlag:
    """
    JointFlag.KNEE must:
      (a) exclude every deep-knee-flexion exercise,
      (b) ALSO exclude every high-impact exercise (knee implies impact restriction),
      (c) still produce a usable squat pattern via the box-squat/glute-bridge
          substitute — the rule removes risk, it does not remove the movement
          pattern entirely.
    """

    def test_no_deep_knee_flexion_when_knee_flagged(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.KNEE]))
        produced = all_exercise_ids(result)
        assert produced.isdisjoint(DEEP_KNEE_FLEXION_EXERCISE_IDS), (
            "Knee flag must exclude all deep-knee-flexion exercises; found "
            f"{produced & DEEP_KNEE_FLEXION_EXERCISE_IDS}"
        )

    def test_no_high_impact_when_knee_flagged(self):
        # Knee implies impact restriction — this assertion makes the two axes
        # coupled in the safe direction.
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.KNEE]))
        produced = all_exercise_ids(result)
        assert produced.isdisjoint(HIGH_IMPACT_EXERCISE_IDS), (
            "Knee flag must also exclude high-impact exercises; found "
            f"{produced & HIGH_IMPACT_EXERCISE_IDS}"
        )

    def test_substitute_squat_present_when_knee_flagged(self):
        # The squat pattern must survive in a knee-safe form, or the user loses
        # lower-body work entirely. At least one mandated substitute must appear.
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.KNEE]))
        produced = all_exercise_ids(result)
        assert produced & set(KNEE_FLAG_SQUAT_SUBSTITUTES), (
            "Knee flag must substitute a knee-safe squat (box_squat/glute_bridge); "
            "none present"
        )


# ---------------------------------------------------------------------------
# Axis 2: high impact — standalone guarantee, independent of any knee flag
# ---------------------------------------------------------------------------

class TestHighImpactRestriction:
    """
    HIGH_IMPACT must be suppressed by its OWN triggers, with no knee flag set, so
    the axis cannot silently break when advanced users are later allowed to unlock
    impact. Each trigger is asserted in isolation.
    """

    def test_impact_off_by_default_for_beginner_population(self):
        # Phase 1: nobody starts with impact. A clean baseline intake — no knee
        # flag, no fall risk — must still contain zero high-impact exercises.
        result = generate_mesocycle(make_intake())
        produced = all_exercise_ids(result)
        assert produced.isdisjoint(HIGH_IMPACT_EXERCISE_IDS), (
            "Impact must be off by default for the beginner population; found "
            f"{produced & HIGH_IMPACT_EXERCISE_IDS}"
        )

    def test_impact_off_when_fall_risk(self):
        result = generate_mesocycle(make_intake(fall_risk=True))
        produced = all_exercise_ids(result)
        assert produced.isdisjoint(HIGH_IMPACT_EXERCISE_IDS), (
            "Fall risk must exclude high-impact exercises independent of knee flag"
        )

    def test_impact_off_when_balance_below_cutoff(self):
        # The exact cutoff is a REVIEW placeholder (physician must confirm).
        # 3.0 s is well below any reasonable threshold; this asserts the rule
        # fires, not the specific cutoff value.
        result = generate_mesocycle(make_intake(balance_seconds=3.0))
        produced = all_exercise_ids(result)
        assert produced.isdisjoint(HIGH_IMPACT_EXERCISE_IDS), (
            "Low balance score must exclude high-impact exercises independent of "
            "knee flag"
        )

    @pytest.mark.parametrize("triggers", [
        dict(fall_risk=True),
        dict(balance_seconds=3.0),
        dict(joint_flags=[JointFlag.KNEE]),
    ])
    def test_impact_suppressed_by_any_single_trigger(self, triggers):
        # Belt-and-suspenders: any one trigger alone is sufficient to suppress
        # impact. Guards against a future refactor that requires triggers to
        # combine before the rule fires.
        result = generate_mesocycle(make_intake(**triggers))
        produced = all_exercise_ids(result)
        assert produced.isdisjoint(HIGH_IMPACT_EXERCISE_IDS)


# ---------------------------------------------------------------------------
# Lower-back flag — hinge substitution and core restriction
# ---------------------------------------------------------------------------

class TestLowerBackFlag:
    """
    JointFlag.LOWER_BACK must:
      (a) exclude single-leg deadlift variants from the hinge pattern,
      (b) restrict the core pattern to dead_bug and bird_dog (no plank).
    """

    def test_no_single_leg_deadlift_assist_when_lower_back_flagged(self):
        # single_leg_deadlift_assist is the standard hinge L3 primary exercise —
        # must not appear in any position when lower_back is flagged.
        # single_leg_deadlift (unassisted) may appear as the standard balance
        # track's progression_alt; that's the HIP flag's concern, not LOWER_BACK.
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.LOWER_BACK]))
        produced = all_exercise_ids(result)
        assert "single_leg_deadlift_assist" not in produced, (
            "Lower-back flag must exclude single-leg deadlift from hinge pattern; "
            "found single_leg_deadlift_assist"
        )

    def test_no_plank_when_lower_back_flagged(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.LOWER_BACK]))
        produced = all_exercise_ids(result)
        excluded = {"plank_hold", "side_plank"}
        assert produced.isdisjoint(excluded), (
            "Lower-back flag must restrict core to dead_bug/bird_dog; found "
            f"{produced & excluded}"
        )

    def test_hinge_pattern_present_when_lower_back_flagged(self):
        """The hinge pattern must survive via the bilateral-only track."""
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.LOWER_BACK]))
        produced = all_exercise_ids(result)
        bilateral_hinge = {
            "hip_hinge_bodyweight", "romanian_deadlift_band",
            "good_morning_band", "sumo_deadlift_band",
        }
        assert produced & bilateral_hinge, (
            "Lower-back flag must substitute a bilateral hinge; none present"
        )

    def test_rules_applied_records_lower_back_decisions(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.LOWER_BACK]))
        assert result.program is not None
        rules = result.program.rules_applied
        assert "lower_back_flag_hinge_substitution" in rules
        assert "lower_back_flag_core_restriction" in rules


# ---------------------------------------------------------------------------
# Hip flag — balance progression cap
# ---------------------------------------------------------------------------

class TestHipFlag:
    """
    JointFlag.HIP must cap the balance pattern so single_leg_deadlift does not
    appear as a progression target.
    """

    def test_single_leg_deadlift_excluded_when_hip_flagged(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.HIP]))
        produced = all_exercise_ids(result)
        assert "single_leg_deadlift" not in produced, (
            "Hip flag must exclude single_leg_deadlift from the balance pattern"
        )

    def test_balance_pattern_present_when_hip_flagged(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.HIP]))
        produced = all_exercise_ids(result)
        balance_exercises = {
            "single_leg_stand_assist", "single_leg_stand", "single_leg_balance_reach",
        }
        assert produced & balance_exercises, (
            "Hip flag must preserve the balance pattern"
        )

    def test_rules_applied_records_hip_cap(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.HIP]))
        assert result.program is not None
        assert "hip_flag_balance_progression_cap" in result.program.rules_applied


# ---------------------------------------------------------------------------
# Shoulder flag — push modification and band-only pull
# ---------------------------------------------------------------------------

class TestShoulderFlag:
    """
    JointFlag.SHOULDER must:
      (a) exclude full_pushup from the push pattern,
      (b) restrict pull to band-only exercises (no inverted_row, door_row).
    """

    def test_full_pushup_excluded_when_shoulder_flagged(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.SHOULDER]))
        produced = all_exercise_ids(result)
        assert "full_pushup" not in produced, (
            "Shoulder flag must exclude full_pushup from the push pattern"
        )

    def test_inverted_row_excluded_when_shoulder_flagged(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.SHOULDER]))
        produced = all_exercise_ids(result)
        assert "inverted_row" not in produced, (
            "Shoulder flag must exclude inverted_row from the pull pattern"
        )

    def test_push_pattern_present_when_shoulder_flagged(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.SHOULDER]))
        produced = all_exercise_ids(result)
        safe_push = {"wall_pushup", "incline_pushup", "knee_pushup"}
        assert produced & safe_push, (
            "Shoulder flag must preserve the push pattern with safe alternatives"
        )

    def test_pull_is_band_only_when_shoulder_flagged(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.SHOULDER]))
        produced = all_exercise_ids(result)
        non_band_pull = {"door_row", "incline_row", "inverted_row"}
        assert produced.isdisjoint(non_band_pull), (
            "Shoulder flag: pull must be band-only; found non-band exercises: "
            f"{produced & non_band_pull}"
        )

    def test_rules_applied_records_shoulder_decisions(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.SHOULDER]))
        assert result.program is not None
        rules = result.program.rules_applied
        assert "shoulder_flag_push_modification" in rules
        assert "shoulder_flag_pull_band_only" in rules


# ---------------------------------------------------------------------------
# Wrist flag — band-only push
# ---------------------------------------------------------------------------

class TestWristFlag:
    """
    JointFlag.WRIST must replace the push pattern with band-only exercises
    (no floor hand-bearing or wrist-extension loading).
    """

    def test_floor_push_exercises_excluded_when_wrist_flagged(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.WRIST]))
        produced = all_exercise_ids(result)
        floor_push = {"wall_pushup", "incline_pushup", "knee_pushup", "full_pushup"}
        assert produced.isdisjoint(floor_push), (
            "Wrist flag must replace push track with band-only; found floor exercises: "
            f"{produced & floor_push}"
        )

    def test_band_push_present_when_wrist_flagged(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.WRIST]))
        produced = all_exercise_ids(result)
        band_push = {"band_wall_press", "band_chest_press", "band_chest_press_narrow"}
        assert produced & band_push, (
            "Wrist flag must include band-only push alternatives"
        )

    def test_rules_applied_records_wrist_decision(self):
        result = generate_mesocycle(make_intake(joint_flags=[JointFlag.WRIST]))
        assert result.program is not None
        assert "wrist_flag_push_band_only" in result.program.rules_applied
