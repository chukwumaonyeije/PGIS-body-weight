"""Convert API request models to engine dataclasses."""
from __future__ import annotations

from pgis_bodyweight.api.schemas import IntakeRequest
from pgis_bodyweight.engine.types import FunctionalTests, IntakeAssessment


def to_engine_intake(req: IntakeRequest) -> IntakeAssessment:
    return IntakeAssessment(
        age=req.age,
        sex=req.sex,
        parq_flags=req.parq_flags,
        medication_class=req.medication_class,
        joint_flags=list(req.joint_flags),
        functional_tests=FunctionalTests(
            sit_to_stand_count=req.functional_tests.sit_to_stand_count,
            pushup_max=req.functional_tests.pushup_max,
            single_leg_stand_s=req.functional_tests.single_leg_stand_s,
        ),
        days_per_week=req.days_per_week,
        minutes_per_session=req.minutes_per_session,
        fall_risk=req.fall_risk,
        equipment=list(req.equipment),
        goals=list(req.goals),
    )
