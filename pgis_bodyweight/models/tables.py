"""
SQLAlchemy ORM table definitions.

Health data (intake_json, per_exercise_rpe) is treated as sensitive. Encryption
at rest is delegated to the infrastructure layer (Railway encrypts disks). Do not
log raw intake or glucose values.

Design notes:
- Sessions are served from generated_programs.program_json at query time.
  Materializing a sessions table is a Phase 2 optimization once query patterns
  are known.
- ProgressionState is added when autoregulation logic is built (Phase 2).
- GlucoseReading / ReadinessSnapshot reuse the existing PGIS pipeline.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
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
