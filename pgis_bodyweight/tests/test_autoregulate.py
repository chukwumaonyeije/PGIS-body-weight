"""
Tests for engine/autoregulate.py.

The engine is pure — no I/O, no DB. exercise_pattern_map is injected.

Autoregulation rules:
  mean RPE ≤ 6.0 for a pattern → advance one level (capped at max_level)
  mean RPE > 6.0              → hold
  no RPE data for a pattern   → hold
  exercise_id not in map      → ignored (warmup/cooldown exercises)
"""
from __future__ import annotations

import pytest

from pgis_bodyweight.engine.autoregulate import autoregulate
from pgis_bodyweight.engine.types import MovementPattern

# Minimal exercise→pattern fixture shared across tests.
_MAP: dict[str, MovementPattern] = {
    "bodyweight_squat": MovementPattern.SQUAT,
    "hip_hinge":        MovementPattern.HINGE,
    "wall_pushup":      MovementPattern.HORIZONTAL_PUSH,
    "band_row":         MovementPattern.PULL,
    "dead_bug":         MovementPattern.CORE,
    "single_leg_stand": MovementPattern.SINGLE_LEG_BALANCE,
}
_BASE_LEVELS: dict[MovementPattern, int] = {p: 1 for p in MovementPattern}


# ── Advance rules ──────────────────────────────────────────────────────────────

def test_rpe_at_threshold_advances():
    rpe = {"bodyweight_squat": 6.0}
    result = autoregulate(rpe, _BASE_LEVELS, _MAP)
    assert result[MovementPattern.SQUAT] == 2


def test_rpe_below_threshold_advances():
    rpe = {"bodyweight_squat": 4.0}
    result = autoregulate(rpe, _BASE_LEVELS, _MAP)
    assert result[MovementPattern.SQUAT] == 2


def test_advance_capped_at_max_level():
    levels = {**_BASE_LEVELS, MovementPattern.SQUAT: 3}
    rpe = {"bodyweight_squat": 5.0}
    result = autoregulate(rpe, levels, _MAP, max_level=3)
    assert result[MovementPattern.SQUAT] == 3


# ── Hold rules ────────────────────────────────────────────────────────────────

def test_rpe_just_above_threshold_holds():
    rpe = {"bodyweight_squat": 6.1}
    result = autoregulate(rpe, _BASE_LEVELS, _MAP)
    assert result[MovementPattern.SQUAT] == 1


def test_rpe_in_target_zone_holds():
    rpe = {"bodyweight_squat": 7.5}
    result = autoregulate(rpe, _BASE_LEVELS, _MAP)
    assert result[MovementPattern.SQUAT] == 1


def test_rpe_very_high_holds():
    rpe = {"bodyweight_squat": 9.5}
    result = autoregulate(rpe, _BASE_LEVELS, _MAP)
    assert result[MovementPattern.SQUAT] == 1


def test_missing_pattern_rpe_holds():
    # No SQUAT exercise in the RPE dict — squat level stays put.
    rpe = {"hip_hinge": 5.0}
    result = autoregulate(rpe, _BASE_LEVELS, _MAP)
    assert result[MovementPattern.SQUAT] == 1


# ── Multi-exercise pattern (mean decides) ─────────────────────────────────────

def test_mean_rpe_advances_when_both_below_threshold():
    # Two exercises, both in the same pattern — mean is 5.0.
    extra_map = {**_MAP, "goblet_squat": MovementPattern.SQUAT}
    rpe = {"bodyweight_squat": 4.0, "goblet_squat": 6.0}
    result = autoregulate(rpe, _BASE_LEVELS, extra_map)
    assert result[MovementPattern.SQUAT] == 2


def test_mean_rpe_holds_when_mean_above_threshold():
    # mean = (5.0 + 8.0) / 2 = 6.5 → hold
    extra_map = {**_MAP, "goblet_squat": MovementPattern.SQUAT}
    rpe = {"bodyweight_squat": 5.0, "goblet_squat": 8.0}
    result = autoregulate(rpe, _BASE_LEVELS, extra_map)
    assert result[MovementPattern.SQUAT] == 1


# ── Unknown exercise IDs are ignored ─────────────────────────────────────────

def test_unknown_exercise_id_ignored():
    rpe = {"warmup_jog": 4.0, "bodyweight_squat": 6.0}
    result = autoregulate(rpe, _BASE_LEVELS, _MAP)
    assert result[MovementPattern.SQUAT] == 2


# ── All patterns advance independently ───────────────────────────────────────

def test_independent_pattern_advancement():
    rpe = {
        "bodyweight_squat": 5.0,  # advances
        "hip_hinge":        7.0,  # holds
        "wall_pushup":      6.0,  # advances
        "band_row":         8.0,  # holds
        "dead_bug":         5.5,  # advances
        # single_leg_balance has no entry → holds
    }
    result = autoregulate(rpe, _BASE_LEVELS, _MAP)
    assert result[MovementPattern.SQUAT]              == 2
    assert result[MovementPattern.HINGE]              == 1
    assert result[MovementPattern.HORIZONTAL_PUSH]    == 2
    assert result[MovementPattern.PULL]               == 1
    assert result[MovementPattern.CORE]               == 2
    assert result[MovementPattern.SINGLE_LEG_BALANCE] == 1


# ── Empty RPE dict ────────────────────────────────────────────────────────────

def test_empty_rpe_holds_all():
    result = autoregulate({}, _BASE_LEVELS, _MAP)
    assert result == _BASE_LEVELS
