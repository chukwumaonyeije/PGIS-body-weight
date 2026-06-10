"""
Contract + persistence tests for POST /v1/glucose.

Uses the in-memory SQLite fixture from conftest.py — no network, no real DB.
"""
import pytest
from fastapi.testclient import TestClient


def _create_user(client: TestClient) -> str:
    r = client.post("/v1/users")
    assert r.status_code == 201
    return r.json()["user_id"]


CLEAN_INTAKE = {
    "age": 60,
    "sex": "male",
    "parq_flags": [],
    "medication_class": "metformin_only",
    "joint_flags": [],
    "functional_tests": {
        "sit_to_stand_count": 12,
        "pushup_max": 8,
        "single_leg_stand_s": 15.0,
    },
    "days_per_week": 3,
    "minutes_per_session": 20,
}


def _create_program(client: TestClient, user_id: str) -> str:
    r = client.post("/v1/intake/submit", json={"user_id": user_id, "intake": CLEAN_INTAKE})
    intake_id = r.json()["intake_id"]
    r = client.post("/v1/programs/generate-from-intake", json={"user_id": user_id, "intake_id": intake_id})
    return r.json()["program_id"]


def _log_session(client: TestClient, user_id: str, program_id: str) -> str:
    r = client.post(f"/v1/programs/{program_id}/sessions/log", json={"user_id": user_id})
    assert r.status_code == 201
    return r.json()["log_id"]


# ── Happy path ────────────────────────────────────────────────────────────────

class TestGlucoseEntry:
    def test_post_returns_201(self, client):
        user_id = _create_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 94.0})
        assert r.status_code == 201

    def test_response_shape(self, client):
        user_id = _create_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 112.5})
        body = r.json()
        assert "reading_id" in body
        assert len(body["reading_id"]) == 36
        assert body["user_id"] == user_id
        assert body["value_mgdl"] == 112.5
        assert "recorded_at" in body

    def test_explicit_recorded_at_is_preserved(self, client):
        user_id = _create_user(client)
        ts = "2026-06-09T08:30:00+00:00"
        r = client.post("/v1/glucose", json={
            "user_id": user_id,
            "value_mgdl": 88.0,
            "recorded_at": ts,
        })
        assert r.status_code == 201
        # Returned timestamp should match the submitted one (may differ in format)
        assert "2026-06-09" in r.json()["recorded_at"]

    def test_omitted_recorded_at_defaults_to_now(self, client):
        user_id = _create_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 95.0})
        assert r.json()["recorded_at"] is not None

    def test_with_session_log_id(self, client):
        user_id = _create_user(client)
        program_id = _create_program(client, user_id)
        log_id = _log_session(client, user_id, program_id)

        r = client.post("/v1/glucose", json={
            "user_id": user_id,
            "value_mgdl": 102.0,
            "session_log_id": log_id,
        })
        assert r.status_code == 201

    def test_optional_notes(self, client):
        user_id = _create_user(client)
        r = client.post("/v1/glucose", json={
            "user_id": user_id,
            "value_mgdl": 78.0,
            "notes": "pre-breakfast",
        })
        assert r.status_code == 201

    def test_two_readings_return_distinct_ids(self, client):
        user_id = _create_user(client)
        r1 = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 90.0})
        r2 = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 95.0})
        assert r1.json()["reading_id"] != r2.json()["reading_id"]


# ── Error cases ───────────────────────────────────────────────────────────────

class TestGlucoseErrors:
    def test_unknown_user_returns_404(self, client):
        r = client.post("/v1/glucose", json={
            "user_id": "00000000-0000-0000-0000-000000000000",
            "value_mgdl": 90.0,
        })
        assert r.status_code == 404

    def test_unknown_session_log_id_returns_404(self, client):
        user_id = _create_user(client)
        r = client.post("/v1/glucose", json={
            "user_id": user_id,
            "value_mgdl": 90.0,
            "session_log_id": "00000000-0000-0000-0000-000000000000",
        })
        assert r.status_code == 404

    def test_non_positive_value_returns_422(self, client):
        user_id = _create_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 0.0})
        assert r.status_code == 422

    def test_negative_value_returns_422(self, client):
        user_id = _create_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": -10.0})
        assert r.status_code == 422
