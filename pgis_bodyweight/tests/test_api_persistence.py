"""
Persistence tests — verify the stateful API endpoints round-trip correctly
through the database and enforce bearer-token ownership.
"""
import uuid

from fastapi.testclient import TestClient

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

PARQ_INTAKE = {**CLEAN_INTAKE, "parq_flags": ["chest_pain_with_exertion"]}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(client: TestClient) -> str:
    r = client.post("/v1/users")
    assert r.status_code == 201
    return r.json()["user_id"]


def _register_user(client: TestClient) -> tuple[str, dict[str, str]]:
    r = client.post(
        "/v1/auth/register",
        json={"email": f"test-{uuid.uuid4()}@example.com", "password": "Password123!"},
    )
    assert r.status_code == 201
    body = r.json()
    return body["user_id"], {"Authorization": f"Bearer {body['token']}"}


def _submit_intake(
    client: TestClient,
    user_id: str,
    headers: dict[str, str],
    intake: dict = CLEAN_INTAKE,
) -> dict:
    r = client.post(
        "/v1/intake/submit",
        json={"user_id": user_id, "intake": intake},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()


def _generate_program(
    client: TestClient,
    user_id: str,
    headers: dict[str, str],
    intake_id: str,
) -> dict:
    r = client.post(
        "/v1/programs/generate-from-intake",
        json={"user_id": user_id, "intake_id": intake_id},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class TestUsers:
    def test_create_user_returns_user_id(self, client):
        r = client.post("/v1/users")
        assert r.status_code == 201
        body = r.json()
        assert "user_id" in body
        assert len(body["user_id"]) == 36  # UUID

    def test_two_creates_return_distinct_ids(self, client):
        id1 = _create_user(client)
        id2 = _create_user(client)
        assert id1 != id2

    def test_delete_user_returns_204(self, client):
        user_id, headers = _register_user(client)
        r = client.delete(f"/v1/users/{user_id}", headers=headers)
        assert r.status_code == 204

    def test_delete_user_requires_token(self, client):
        user_id = _create_user(client)
        r = client.delete(f"/v1/users/{user_id}")
        assert r.status_code == 401

    def test_delete_user_rejects_wrong_token_user(self, client):
        user_id, _ = _register_user(client)
        _, other_headers = _register_user(client)
        r = client.delete(f"/v1/users/{user_id}", headers=other_headers)
        assert r.status_code == 403

    def test_delete_nonexistent_user_returns_403_when_token_subject_differs(self, client):
        _, headers = _register_user(client)
        r = client.delete("/v1/users/00000000-0000-0000-0000-000000000000", headers=headers)
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Auth boundaries
# ---------------------------------------------------------------------------

class TestAuthBoundaries:
    def test_submit_requires_token(self, client):
        user_id, _ = _register_user(client)
        r = client.post("/v1/intake/submit", json={"user_id": user_id, "intake": CLEAN_INTAKE})
        assert r.status_code == 401

    def test_submit_rejects_invalid_token(self, client):
        user_id, _ = _register_user(client)
        r = client.post(
            "/v1/intake/submit",
            json={"user_id": user_id, "intake": CLEAN_INTAKE},
            headers={"Authorization": "Bearer not-a-valid-token"},
        )
        assert r.status_code == 401

    def test_submit_rejects_wrong_token_user(self, client):
        user_id, _ = _register_user(client)
        _, other_headers = _register_user(client)
        r = client.post(
            "/v1/intake/submit",
            json={"user_id": user_id, "intake": CLEAN_INTAKE},
            headers=other_headers,
        )
        assert r.status_code == 403

    def test_current_program_requires_token(self, client):
        user_id, _ = _register_user(client)
        r = client.get("/v1/programs/current", params={"user_id": user_id})
        assert r.status_code == 401

    def test_current_program_rejects_wrong_token_user(self, client):
        user_id, _ = _register_user(client)
        _, other_headers = _register_user(client)
        r = client.get("/v1/programs/current", params={"user_id": user_id}, headers=other_headers)
        assert r.status_code == 403

    def test_static_intake_assessment_stays_public(self, client):
        r = client.post("/v1/intake", json=CLEAN_INTAKE)
        assert r.status_code == 200

    def test_stateless_generation_stays_public(self, client):
        r = client.post("/v1/programs/generate", json=CLEAN_INTAKE)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Intake submission
# ---------------------------------------------------------------------------

class TestIntakeSubmit:
    def test_submit_returns_intake_id(self, client):
        user_id, headers = _register_user(client)
        body = _submit_intake(client, user_id, headers)
        assert "intake_id" in body
        assert len(body["intake_id"]) == 36

    def test_submit_clean_intake_no_clearance(self, client):
        user_id, headers = _register_user(client)
        body = _submit_intake(client, user_id, headers)
        assert body["clearance_required"] is False
        assert body["hypo_risk"] == "standard"

    def test_submit_parq_intake_clearance_required(self, client):
        user_id, headers = _register_user(client)
        body = _submit_intake(client, user_id, headers, PARQ_INTAKE)
        assert body["clearance_required"] is True
        assert body["hypo_risk"] is None

    def test_submit_insulin_sets_elevated_hypo_risk(self, client):
        user_id, headers = _register_user(client)
        intake = {**CLEAN_INTAKE, "medication_class": "insulin"}
        body = _submit_intake(client, user_id, headers, intake)
        assert body["hypo_risk"] == "elevated"

    def test_submit_unknown_user_returns_403_before_lookup_when_token_user_differs(self, client):
        _, headers = _register_user(client)
        r = client.post(
            "/v1/intake/submit",
            json={
                "user_id": "00000000-0000-0000-0000-000000000000",
                "intake": CLEAN_INTAKE,
            },
            headers=headers,
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Generate from intake
# ---------------------------------------------------------------------------

class TestGenerateFromIntake:
    def test_generate_returns_program_id(self, client):
        user_id, headers = _register_user(client)
        intake_id = _submit_intake(client, user_id, headers)["intake_id"]
        body = _generate_program(client, user_id, headers, intake_id)
        assert "program_id" in body
        assert len(body["program_id"]) == 36

    def test_generate_returns_full_program(self, client):
        user_id, headers = _register_user(client)
        intake_id = _submit_intake(client, user_id, headers)["intake_id"]
        body = _generate_program(client, user_id, headers, intake_id)
        assert body["program"] is not None
        assert len(body["program"]["weeks"]) == 4

    def test_generate_parq_intake_returns_no_program(self, client):
        user_id, headers = _register_user(client)
        intake_id = _submit_intake(client, user_id, headers, PARQ_INTAKE)["intake_id"]
        body = _generate_program(client, user_id, headers, intake_id)
        assert body["clearance_required"] is True
        assert body["program"] is None

    def test_generate_wrong_user_returns_404(self, client):
        user_id, headers = _register_user(client)
        other_user_id, other_headers = _register_user(client)
        intake_id = _submit_intake(client, user_id, headers)["intake_id"]
        r = client.post(
            "/v1/programs/generate-from-intake",
            json={"user_id": other_user_id, "intake_id": intake_id},
            headers=other_headers,
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Current program
# ---------------------------------------------------------------------------

class TestCurrentProgram:
    def test_get_current_returns_latest_program(self, client):
        user_id, headers = _register_user(client)
        intake_id = _submit_intake(client, user_id, headers)["intake_id"]
        program_id = _generate_program(client, user_id, headers, intake_id)["program_id"]

        r = client.get("/v1/programs/current", params={"user_id": user_id}, headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["program_id"] == program_id

    def test_no_program_returns_404(self, client):
        user_id, headers = _register_user(client)
        r = client.get("/v1/programs/current", params={"user_id": user_id}, headers=headers)
        assert r.status_code == 404

    def test_unknown_user_returns_403_when_token_user_differs(self, client):
        _, headers = _register_user(client)
        r = client.get(
            "/v1/programs/current",
            params={"user_id": "00000000-0000-0000-0000-000000000000"},
            headers=headers,
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Next session
# ---------------------------------------------------------------------------

class TestNextSession:
    def test_next_session_is_week1_day1_initially(self, client):
        user_id, headers = _register_user(client)
        intake_id = _submit_intake(client, user_id, headers)["intake_id"]
        program_id = _generate_program(client, user_id, headers, intake_id)["program_id"]

        r = client.get(
            f"/v1/programs/{program_id}/sessions/next",
            params={"user_id": user_id},
            headers=headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["week"] == 1
        assert body["day"] == 1

    def test_next_session_advances_after_log(self, client):
        user_id, headers = _register_user(client)
        intake_id = _submit_intake(client, user_id, headers)["intake_id"]
        program_id = _generate_program(client, user_id, headers, intake_id)["program_id"]

        client.post(f"/v1/programs/{program_id}/sessions/log", json={"user_id": user_id}, headers=headers)

        r = client.get(
            f"/v1/programs/{program_id}/sessions/next",
            params={"user_id": user_id},
            headers=headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert (body["week"], body["day"]) != (1, 1)

    def test_unknown_program_returns_404(self, client):
        user_id, headers = _register_user(client)
        r = client.get(
            "/v1/programs/00000000/sessions/next",
            params={"user_id": user_id},
            headers=headers,
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Session logging
# ---------------------------------------------------------------------------

class TestSessionLog:
    def test_log_session_returns_201(self, client):
        user_id, headers = _register_user(client)
        intake_id = _submit_intake(client, user_id, headers)["intake_id"]
        program_id = _generate_program(client, user_id, headers, intake_id)["program_id"]

        r = client.post(f"/v1/programs/{program_id}/sessions/log", json={"user_id": user_id}, headers=headers)
        assert r.status_code == 201

    def test_log_response_shape(self, client):
        user_id, headers = _register_user(client)
        intake_id = _submit_intake(client, user_id, headers)["intake_id"]
        program_id = _generate_program(client, user_id, headers, intake_id)["program_id"]

        r = client.post(
            f"/v1/programs/{program_id}/sessions/log",
            json={
                "user_id": user_id,
                "per_exercise_rpe": {"wall_pushup": 5.0},
                "notes": "felt good",
            },
            headers=headers,
        )
        body = r.json()
        assert body["log_id"]
        assert body["program_id"] == program_id
        assert body["week"] == 1
        assert body["day_in_week"] == 1

    def test_log_all_sessions_then_409(self, client):
        user_id, headers = _register_user(client)
        intake = {**CLEAN_INTAKE, "days_per_week": 1}
        intake_id = _submit_intake(client, user_id, headers, intake)["intake_id"]
        program_id = _generate_program(client, user_id, headers, intake_id)["program_id"]

        for _ in range(4):  # 4 weeks × 1 day = 4 sessions
            r = client.post(f"/v1/programs/{program_id}/sessions/log", json={"user_id": user_id}, headers=headers)
            assert r.status_code == 201

        r = client.post(f"/v1/programs/{program_id}/sessions/log", json={"user_id": user_id}, headers=headers)
        assert r.status_code == 409
