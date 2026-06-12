"""
Contract + persistence tests for POST /v1/glucose.

Uses the in-memory SQLite fixture from conftest.py — no network, no real DB.
"""
import uuid

from fastapi.testclient import TestClient


def _register_user(client: TestClient) -> tuple[str, dict[str, str]]:
    r = client.post(
        "/v1/auth/register",
        json={"email": f"glucose-{uuid.uuid4()}@example.com", "password": "Password123!"},
    )
    assert r.status_code == 201
    body = r.json()
    return body["user_id"], {"Authorization": f"Bearer {body['token']}"}


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


def _create_program(client: TestClient, user_id: str, headers: dict[str, str]) -> str:
    r = client.post("/v1/intake/submit", json={"user_id": user_id, "intake": CLEAN_INTAKE}, headers=headers)
    intake_id = r.json()["intake_id"]
    r = client.post(
        "/v1/programs/generate-from-intake",
        json={"user_id": user_id, "intake_id": intake_id},
        headers=headers,
    )
    return r.json()["program_id"]


def _log_session(client: TestClient, user_id: str, headers: dict[str, str], program_id: str) -> str:
    r = client.post(f"/v1/programs/{program_id}/sessions/log", json={"user_id": user_id}, headers=headers)
    assert r.status_code == 201
    return r.json()["log_id"]


# ── Happy path ────────────────────────────────────────────────────────────────

class TestGlucoseEntry:
    def test_post_returns_201(self, client):
        user_id, headers = _register_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 94.0}, headers=headers)
        assert r.status_code == 201

    def test_response_shape(self, client):
        user_id, headers = _register_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 112.5}, headers=headers)
        body = r.json()
        assert "reading_id" in body
        assert len(body["reading_id"]) == 36
        assert body["user_id"] == user_id
        assert body["value_mgdl"] == 112.5
        assert "recorded_at" in body

    def test_explicit_recorded_at_is_preserved(self, client):
        user_id, headers = _register_user(client)
        ts = "2026-06-09T08:30:00+00:00"
        r = client.post(
            "/v1/glucose",
            json={"user_id": user_id, "value_mgdl": 88.0, "recorded_at": ts},
            headers=headers,
        )
        assert r.status_code == 201
        assert "2026-06-09" in r.json()["recorded_at"]

    def test_omitted_recorded_at_defaults_to_now(self, client):
        user_id, headers = _register_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 95.0}, headers=headers)
        assert r.json()["recorded_at"] is not None

    def test_with_session_log_id(self, client):
        user_id, headers = _register_user(client)
        program_id = _create_program(client, user_id, headers)
        log_id = _log_session(client, user_id, headers, program_id)

        r = client.post(
            "/v1/glucose",
            json={"user_id": user_id, "value_mgdl": 102.0, "session_log_id": log_id},
            headers=headers,
        )
        assert r.status_code == 201

    def test_optional_notes(self, client):
        user_id, headers = _register_user(client)
        r = client.post(
            "/v1/glucose",
            json={"user_id": user_id, "value_mgdl": 78.0, "notes": "pre-breakfast"},
            headers=headers,
        )
        assert r.status_code == 201

    def test_two_readings_return_distinct_ids(self, client):
        user_id, headers = _register_user(client)
        r1 = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 90.0}, headers=headers)
        r2 = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 95.0}, headers=headers)
        assert r1.json()["reading_id"] != r2.json()["reading_id"]


# ── Error cases ───────────────────────────────────────────────────────────────

class TestGlucoseErrors:
    def test_requires_token(self, client):
        user_id, _ = _register_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 94.0})
        assert r.status_code == 401

    def test_invalid_token_returns_401(self, client):
        user_id, _ = _register_user(client)
        r = client.post(
            "/v1/glucose",
            json={"user_id": user_id, "value_mgdl": 94.0},
            headers={"Authorization": "Bearer bad-token"},
        )
        assert r.status_code == 401

    def test_wrong_token_user_returns_403(self, client):
        user_id, _ = _register_user(client)
        _, other_headers = _register_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 94.0}, headers=other_headers)
        assert r.status_code == 403

    def test_unknown_user_returns_403_when_token_user_differs(self, client):
        _, headers = _register_user(client)
        r = client.post(
            "/v1/glucose",
            json={"user_id": "00000000-0000-0000-0000-000000000000", "value_mgdl": 90.0},
            headers=headers,
        )
        assert r.status_code == 403

    def test_unknown_session_log_id_returns_404(self, client):
        user_id, headers = _register_user(client)
        r = client.post(
            "/v1/glucose",
            json={
                "user_id": user_id,
                "value_mgdl": 90.0,
                "session_log_id": "00000000-0000-0000-0000-000000000000",
            },
            headers=headers,
        )
        assert r.status_code == 404

    def test_non_positive_value_returns_422(self, client):
        user_id, headers = _register_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 0.0}, headers=headers)
        assert r.status_code == 422

    def test_negative_value_returns_422(self, client):
        user_id, headers = _register_user(client)
        r = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": -10.0}, headers=headers)
        assert r.status_code == 422
