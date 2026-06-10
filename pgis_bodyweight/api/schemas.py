"""
Request and response Pydantic models for the PGIS Body Weight API.

The engine uses Python dataclasses; these models handle HTTP serialization and
validation. Response models carry model_config = ConfigDict(from_attributes=True)
so they can be built directly from engine dataclass instances.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from pgis_bodyweight.engine.types import (
    EquipmentItem,
    JointFlag,
    MedicationClass,
    Sex,
)


# ── Request models ────────────────────────────────────────────────────────────

class FunctionalTestsIn(BaseModel):
    sit_to_stand_count: int
    pushup_max: int
    single_leg_stand_s: float


class IntakeRequest(BaseModel):
    age: int
    sex: Sex
    parq_flags: list[str] = []
    medication_class: MedicationClass
    joint_flags: list[JointFlag] = []
    functional_tests: FunctionalTestsIn
    days_per_week: int
    minutes_per_session: int
    fall_risk: bool = False
    equipment: list[EquipmentItem] = []
    goals: list[str] = []


# ── Response models ───────────────────────────────────────────────────────────

class IntakeAssessmentResponse(BaseModel):
    clearance_required: bool
    clearance_reason: str | None
    hypo_risk: str | None  # None when clearance_required is True


class ExerciseInstanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exercise_id: str
    sets: int
    reps_or_time: str
    rest_s: int
    target_rpe: float
    regression_alt: str
    progression_alt: str


class BlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    exercises: list[ExerciseInstanceOut]


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    week: int
    day: int
    blocks: list[BlockOut]
    glucose_check_required: bool
    preferred_window: str | None


class WeekOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    week_number: int
    sessions: list[SessionOut]
    is_deload: bool


class ProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    engine_version: str
    hypo_risk: str
    rules_applied: list[str]
    weeks: list[WeekOut]


class GenerationResponse(BaseModel):
    clearance_required: bool
    clearance_reason: str | None
    program: ProgramOut | None


# ── Stateful request/response models ─────────────────────────────────────────

class UserResponse(BaseModel):
    user_id: str


class IntakeSubmitRequest(BaseModel):
    user_id: str
    intake: IntakeRequest


class IntakeSubmitResponse(BaseModel):
    intake_id: str
    clearance_required: bool
    clearance_reason: str | None
    hypo_risk: str | None


class GenerateFromIntakeRequest(BaseModel):
    user_id: str
    intake_id: str


class GenerateFromIntakeResponse(BaseModel):
    program_id: str
    clearance_required: bool
    clearance_reason: str | None
    program: ProgramOut | None


class SessionLogRequest(BaseModel):
    user_id: str
    per_exercise_rpe: dict[str, float] | None = None
    notes: str | None = None
    started_at: str | None = None   # ISO 8601
    finished_at: str | None = None  # ISO 8601


class SessionLogResponse(BaseModel):
    log_id: str
    program_id: str
    week: int
    day_in_week: int
    level_changes: dict[str, int] = {}  # pattern → new level; empty when no RPE submitted


class CoachingResponse(BaseModel):
    coaching_text: str | None


class GlucoseEntryRequest(BaseModel):
    user_id: str
    value_mgdl: float = Field(..., gt=0)
    recorded_at: str | None = None   # ISO 8601; defaults to server time when omitted
    session_log_id: str | None = None
    notes: str | None = None


class GlucoseEntryResponse(BaseModel):
    reading_id: str
    user_id: str
    value_mgdl: float
    recorded_at: str
