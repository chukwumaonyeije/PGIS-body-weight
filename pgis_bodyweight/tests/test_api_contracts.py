"""
API contract tests — shape and HTTP status only.

These tests verify the API layer: correct status codes, required fields present
in responses, and that invalid input is rejected. They do NOT re-test business
logic (that lives in test_safety_invariants.py and test_contraindication_axes.py).

Runs without network access: the engine is pure and the LLM layer is absent here.
"""
import pytest
from fastapi.testclient import TestClient

from pgis_bodyweight.api.app import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

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
# POST /v1/intake — safety assessment
# ---------------------------------------------------------------------------

class TestIntakeEndpoint:
    def test_clean_intake_returns_200(self):
        r = client.post("/v1/intake", json=CLEAN_INTAKE)
        assert r.status_code == 200

    def test_clean_intake_clearance_not_required(self):
        r = client.post("/v1/intake", json=CLEAN_INTAKE)
        body = r.json()
        assert body["clearance_required"] is False
        assert body["clearance_reason"] is None

    def test_clean_intake_returns_hypo_risk(self):
        r = client.post("/v1/intake", json=CLEAN_INTAKE)
        body = r.json()
        assert body["hypo_risk"] in ("standard", "elevated")

    def test_parq_flag_sets_clearance_required(self):
        r = client.post("/v1/intake", json=PARQ_INTAKE)
        assert r.status_code == 200
        body = r.json()
        assert body["clearance_required"] is True
        assert body["clearance_reason"] is not None and len(body["clearance_reason"]) > 0

    def test_parq_flag_suppresses_hypo_risk(self):
        r = client.post("/v1/intake", json=PARQ_INTAKE)
        assert r.json()["hypo_risk"] is None

    def test_insulin_intake_returns_elevated_hypo_risk(self):
        intake = {**CLEAN_INTAKE, "medication_class": "insulin"}
        r = client.post("/v1/intake", json=intake)
        assert r.json()["hypo_risk"] == "elevated"

    def test_invalid_sex_returns_422(self):
        r = client.post("/v1/intake", json={**CLEAN_INTAKE, "sex": "unknown"})
        assert r.status_code == 422

    def test_invalid_medication_class_returns_422(self):
        r = client.post("/v1/intake", json={**CLEAN_INTAKE, "medication_class": "aspirin"})
        assert r.status_code == 422

    def test_missing_required_field_returns_422(self):
        intake = {k: v for k, v in CLEAN_INTAKE.items() if k != "age"}
        r = client.post("/v1/intake", json=intake)
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /v1/programs/generate — mesocycle generation
# ---------------------------------------------------------------------------

class TestGenerateEndpoint:
    def test_clean_intake_returns_200(self):
        r = client.post("/v1/programs/generate", json=CLEAN_INTAKE)
        assert r.status_code == 200

    def test_response_shape_top_level(self):
        r = client.post("/v1/programs/generate", json=CLEAN_INTAKE)
        body = r.json()
        assert "clearance_required" in body
        assert "clearance_reason" in body
        assert "program" in body

    def test_program_fields_present(self):
        r = client.post("/v1/programs/generate", json=CLEAN_INTAKE)
        program = r.json()["program"]
        assert "engine_version" in program
        assert "hypo_risk" in program
        assert "rules_applied" in program
        assert "weeks" in program

    def test_program_has_four_weeks(self):
        r = client.post("/v1/programs/generate", json=CLEAN_INTAKE)
        assert len(r.json()["program"]["weeks"]) == 4

    def test_week_four_is_deload(self):
        r = client.post("/v1/programs/generate", json=CLEAN_INTAKE)
        weeks = r.json()["program"]["weeks"]
        assert weeks[3]["is_deload"] is True

    def test_sessions_have_three_blocks(self):
        r = client.post("/v1/programs/generate", json=CLEAN_INTAKE)
        session = r.json()["program"]["weeks"][0]["sessions"][0]
        block_names = [b["name"] for b in session["blocks"]]
        assert block_names == ["warmup", "main", "cooldown"]

    def test_each_exercise_has_regression_and_progression(self):
        r = client.post("/v1/programs/generate", json=CLEAN_INTAKE)
        program = r.json()["program"]
        for week in program["weeks"]:
            for session in week["sessions"]:
                for block in session["blocks"]:
                    for ex in block["exercises"]:
                        assert ex["regression_alt"], f"Missing regression_alt on {ex['exercise_id']}"
                        assert ex["progression_alt"], f"Missing progression_alt on {ex['exercise_id']}"

    def test_parq_flag_returns_clearance_required_no_program(self):
        r = client.post("/v1/programs/generate", json=PARQ_INTAKE)
        assert r.status_code == 200
        body = r.json()
        assert body["clearance_required"] is True
        assert body["program"] is None

    def test_glucose_check_on_every_session_for_insulin(self):
        intake = {**CLEAN_INTAKE, "medication_class": "insulin"}
        r = client.post("/v1/programs/generate", json=intake)
        program = r.json()["program"]
        for week in program["weeks"]:
            for session in week["sessions"]:
                assert session["glucose_check_required"] is True

    def test_rules_applied_is_nonempty_list(self):
        r = client.post("/v1/programs/generate", json=CLEAN_INTAKE)
        rules = r.json()["program"]["rules_applied"]
        assert isinstance(rules, list) and len(rules) > 0

    def test_invalid_sex_returns_422(self):
        r = client.post("/v1/programs/generate", json={**CLEAN_INTAKE, "sex": "unknown"})
        assert r.status_code == 422

    def test_unreviewed_age_band_returns_422(self):
        intake = {**CLEAN_INTAKE, "age": 72}
        r = client.post("/v1/programs/generate", json=intake)
        assert r.status_code == 422
