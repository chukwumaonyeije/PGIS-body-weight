"""
Database engine + session factory.

DATABASE_URL is read from the environment.
  - Production (Railway): postgresql://user:pass@host:port/db
  - Local dev (default): sqlite:///./pgis_bodyweight.db
  - Tests: overridden via the get_db dependency override in conftest.py

create_tables() is called at app startup for dev/test. Alembic migrations are
used for production schema management (to be added before first Railway deploy).
"""
from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from pgis_bodyweight.models.base import Base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./pgis_bodyweight.db")

# SQLite needs check_same_thread=False for use across FastAPI threads.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
