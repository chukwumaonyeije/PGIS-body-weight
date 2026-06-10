"""
SQLAlchemy ORM table definitions.

Health data (intake_json, per_exercise_rpe) is treated as sensitive. Encryption
at rest is delegated to the infrastructure layer (Railway encrypts disks). Do not
log raw intake or glucose values.

Design notes:
- Sessions are served from generated_programs.program_json at query time.
  Materializing a sessions table is a Phase 2 optimization once query patterns
  are known.
- GlucoseReading / ReadinessSnapshot reuse the existing PGIS pipeline.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgis_bodyweight.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    intakes: Mapped[list[IntakeSubmission]] = relationship(back_populates="user")
    programs: Mapped[list[GeneratedProgram]] = relationship(back_populates="user")
    session_logs: Mapped[list[SessionLog]] = relationship(back_populates="user")
    progression_states: Mapped[list[ProgressionState]] = relationship(back_populates="user")
    glucose_readings: Mapped[list[GlucoseReading]] = relationship(back_populates="user")


class IntakeSubmission(Base):
    __tablename__ = "intake_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    intake_json: Mapped[dict] = mapped_column(JSON, nullable=False)    # sensitive — do not log
    clearance_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    hypo_risk: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="intakes")
    programs: Mapped[list[GeneratedProgram]] = relationship(back_populates="intake")


class GeneratedProgram(Base):
    __tablename__ = "generated_programs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    intake_id: Mapped[str] = mapped_column(String(36), ForeignKey("intake_submissions.id"), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    hypo_risk: Mapped[str] = mapped_column(String(32), nullable=False)
    rules_applied: Mapped[list] = mapped_column(JSON, nullable=False)
    program_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="programs")
    intake: Mapped[IntakeSubmission] = relationship(back_populates="programs")
    session_logs: Mapped[list[SessionLog]] = relationship(back_populates="program")


class SessionLog(Base):
    __tablename__ = "session_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    program_id: Mapped[str] = mapped_column(String(36), ForeignKey("generated_programs.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    week: Mapped[int] = mapped_column(nullable=False)
    day_in_week: Mapped[int] = mapped_column(nullable=False)
    per_exercise_rpe: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {exercise_id: rpe}
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    program: Mapped[GeneratedProgram] = relationship(back_populates="session_logs")
    user: Mapped[User] = relationship(back_populates="session_logs")


class ProgressionState(Base):
    """
    Tracks the current exercise level per movement pattern per user.

    Updated after each logged session by the autoregulation engine.
    One row per (user_id, pattern) — enforced by the unique constraint.
    """
    __tablename__ = "progression_states"
    __table_args__ = (UniqueConstraint("user_id", "pattern", name="uq_progression_user_pattern"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    pattern: Mapped[str] = mapped_column(String(32), nullable=False)   # MovementPattern value
    current_level: Mapped[int] = mapped_column(Integer, nullable=False)
    last_changed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="progression_states")


class GlucoseReading(Base):
    """
    Manual glucose entry for Phase 1.

    Stored in mg/dL. CGM time-series data (Phase 2) will go through the
    existing PGIS pipeline and not duplicate this table.
    Value is treated as sensitive — do not log raw values.
    """
    __tablename__ = "glucose_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    session_log_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("session_logs.id"), nullable=True)
    value_mgdl: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="glucose_readings")
    session_log: Mapped[SessionLog | None] = relationship()
