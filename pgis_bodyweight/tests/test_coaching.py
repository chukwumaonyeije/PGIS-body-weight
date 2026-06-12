"""
Tests for the coaching endpoint and narrator module.

Per CLAUDE.md: verify the app behaves correctly when coaching returns nothing,
errors, or is slow — not the prose itself. No real Anthropic API calls.
"""
from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

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


def _register_user(client: TestClient) -> tuple[str, dict[str, str]]:
    r = client.post(
        "/v1/auth/register",
        json={"email": f"coach-{uuid.uuid4()}@example.com", "password": "Password123!"},
    )
    assert r.status_code == 201
    body = r.json()
    return body["user_id"], {"Authorization": f"Bearer {body['token']}"}


def _create_program(client: TestClient, user_id: str, headers: dict[str, str]) -> tuple[str, int, int]:
    """Returns (program_id, first_week_number, first_day)."""
    r = client.post("/v1/intake/submit", json={"user_id": user_id, "intake": CLEAN_INTAKE}, headers=headers)
    assert r.status_code == 201
    intake_id = r.json()["intake_id"]

    r = client.post(
        "/v1/programs/generate-from-intake",
        json={"user_id": user_id, "intake_id": intake_id},
        headers=headers,
    )
    assert r.status_code in (200, 201)
    program_id = r.json()["program_id"]
    program = r.json()["program"]
    first_week = program["weeks"][0]["week_number"]
    first_day = program["weeks"][0]["sessions"][0]["day"]
    return program_id, first_week, first_day


# ── Endpoint contract tests ───────────────────────────────────────────────────

class TestCoachingEndpoint:
    def test_returns_200_with_prose(self, client):
        user_id, headers = _register_user(client)
        program_id, week, day = _create_program(client, user_id, headers)

        with patch(
            "pgis_bodyweight.api.routers.coaching.generate_coaching",
            new_callable=AsyncMock,
            return_value="Start with the glute bridge. Take your time.",
        ):
            r = client.get(
                f"/v1/programs/{program_id}/sessions/{week}/{day}/coaching",
                params={"user_id": user_id},
                headers=headers,
            )
        assert r.status_code == 200
        assert r.json()["coaching_text"] == "Start with the glute bridge. Take your time."

    def test_returns_200_when_coaching_unavailable(self, client):
        """Program is fully functional when the coaching layer returns nothing."""
        user_id, headers = _register_user(client)
        program_id, week, day = _create_program(client, user_id, headers)

        with patch(
            "pgis_bodyweight.api.routers.coaching.generate_coaching",
            new_callable=AsyncMock,
            return_value=None,
        ):
            r = client.get(
                f"/v1/programs/{program_id}/sessions/{week}/{day}/coaching",
                params={"user_id": user_id},
                headers=headers,
            )
        assert r.status_code == 200
        assert r.json()["coaching_text"] is None

    def test_response_has_coaching_text_key(self, client):
        user_id, headers = _register_user(client)
        program_id, week, day = _create_program(client, user_id, headers)

        with patch(
            "pgis_bodyweight.api.routers.coaching.generate_coaching",
            new_callable=AsyncMock,
            return_value=None,
        ):
            r = client.get(
                f"/v1/programs/{program_id}/sessions/{week}/{day}/coaching",
                params={"user_id": user_id},
                headers=headers,
            )
        assert "coaching_text" in r.json()

    def test_requires_token(self, client):
        user_id, headers = _register_user(client)
        program_id, week, day = _create_program(client, user_id, headers)
        r = client.get(
            f"/v1/programs/{program_id}/sessions/{week}/{day}/coaching",
            params={"user_id": user_id},
        )
        assert r.status_code == 401

    def test_unknown_program_returns_404(self, client):
        user_id, headers = _register_user(client)
        r = client.get(
            "/v1/programs/00000000-0000-0000-0000-000000000000/sessions/1/1/coaching",
            params={"user_id": user_id},
            headers=headers,
        )
        assert r.status_code == 404

    def test_wrong_user_id_returns_403(self, client):
        """A program owned by one user is not accessible to another."""
        user_id, headers = _register_user(client)
        program_id, week, day = _create_program(client, user_id, headers)
        other_user, other_headers = _register_user(client)

        r = client.get(
            f"/v1/programs/{program_id}/sessions/{week}/{day}/coaching",
            params={"user_id": other_user},
            headers=other_headers,
        )
        assert r.status_code == 404

        r = client.get(
            f"/v1/programs/{program_id}/sessions/{week}/{day}/coaching",
            params={"user_id": user_id},
            headers=other_headers,
        )
        assert r.status_code == 403

    def test_unknown_session_returns_404(self, client):
        user_id, headers = _register_user(client)
        program_id, _, _ = _create_program(client, user_id, headers)

        r = client.get(
            f"/v1/programs/{program_id}/sessions/99/99/coaching",
            params={"user_id": user_id},
            headers=headers,
        )
        assert r.status_code == 404


# ── Narrator unit tests ───────────────────────────────────────────────────────

class TestNarrator:
    """
    Verify generate_coaching() absorbs all errors and returns None.
    These tests never call the real Anthropic API.
    """

    def test_returns_none_on_api_error(self):
        from pgis_bodyweight.coaching.narrator import generate_coaching

        async def run():
            with patch(
                "pgis_bodyweight.coaching.narrator.anthropic.AsyncAnthropic"
            ) as mock_cls:
                mock_cls.return_value.messages.create = AsyncMock(
                    side_effect=Exception("connection refused")
                )
                return await generate_coaching({"program": {}, "session": {}})

        assert asyncio.run(run()) is None

    def test_returns_none_on_auth_error(self):
        from pgis_bodyweight.coaching.narrator import generate_coaching

        async def run():
            with patch(
                "pgis_bodyweight.coaching.narrator.anthropic.AsyncAnthropic"
            ) as mock_cls:
                mock_cls.return_value.messages.create = AsyncMock(
                    side_effect=Exception("invalid api key")
                )
                return await generate_coaching({"program": {}, "session": {}})

        assert asyncio.run(run()) is None

    def test_returns_none_on_timeout(self):
        import asyncio as _asyncio
        from pgis_bodyweight.coaching.narrator import generate_coaching

        async def run():
            with patch(
                "pgis_bodyweight.coaching.narrator.anthropic.AsyncAnthropic"
            ) as mock_cls:
                mock_cls.return_value.messages.create = AsyncMock(
                    side_effect=_asyncio.TimeoutError()
                )
                return await generate_coaching({"program": {}, "session": {}})

        assert asyncio.run(run()) is None

    def test_returns_text_on_success(self):
        from pgis_bodyweight.coaching.narrator import generate_coaching

        fake_block = type("Block", (), {"type": "text", "text": "Good session ahead."})()
        fake_message = type("Msg", (), {"content": [fake_block]})()

        async def run():
            with patch(
                "pgis_bodyweight.coaching.narrator.anthropic.AsyncAnthropic"
            ) as mock_cls:
                mock_cls.return_value.messages.create = AsyncMock(
                    return_value=fake_message
                )
                return await generate_coaching({"program": {}, "session": {}})

        assert asyncio.run(run()) == "Good session ahead."

    def test_returns_none_when_response_is_empty(self):
        from pgis_bodyweight.coaching.narrator import generate_coaching

        fake_block = type("Block", (), {"type": "text", "text": "   "})()
        fake_message = type("Msg", (), {"content": [fake_block]})()

        async def run():
            with patch(
                "pgis_bodyweight.coaching.narrator.anthropic.AsyncAnthropic"
            ) as mock_cls:
                mock_cls.return_value.messages.create = AsyncMock(
                    return_value=fake_message
                )
                return await generate_coaching({"program": {}, "session": {}})

        assert asyncio.run(run()) is None

    def test_skips_non_text_blocks(self):
        """Thinking blocks (type='thinking') are ignored; only text blocks returned."""
        from pgis_bodyweight.coaching.narrator import generate_coaching

        thinking_block = type("Block", (), {"type": "thinking", "thinking": "..."})()
        text_block = type("Block", (), {"type": "text", "text": "Here is your session."})()
        fake_message = type("Msg", (), {"content": [thinking_block, text_block]})()

        async def run():
            with patch(
                "pgis_bodyweight.coaching.narrator.anthropic.AsyncAnthropic"
            ) as mock_cls:
                mock_cls.return_value.messages.create = AsyncMock(
                    return_value=fake_message
                )
                return await generate_coaching({"program": {}, "session": {}})

        assert asyncio.run(run()) == "Here is your session."
