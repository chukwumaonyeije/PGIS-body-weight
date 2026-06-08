"""
Shared pytest fixtures.

The `client` fixture overrides the FastAPI get_db dependency to use an
in-memory SQLite database. This means persistence tests run without a real
PostgreSQL instance, and each test session gets a fresh schema.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from pgis_bodyweight.api.app import app
from pgis_bodyweight.models.base import Base
from pgis_bodyweight.models.db import get_db

_TEST_DATABASE_URL = "sqlite://"  # in-memory

_engine = create_engine(
    _TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def _override_get_db():
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def _create_test_schema():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
