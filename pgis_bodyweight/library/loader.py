from __future__ import annotations

import pathlib
from functools import lru_cache

from pgis_bodyweight.engine.types import ExerciseInstance, MovementPattern

_EXERCISES_DIR = pathlib.Path(__file__).parent / "exercises"


def _load_yaml(path: pathlib.Path) -> dict:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required to load the exercise library. "
            "Install it with: pip install pyyaml"
        ) from exc
    with path.open() as f:
        return yaml.safe_load(f)


def _entry_to_instance(entry: dict) -> ExerciseInstance:
    return ExerciseInstance(
        exercise_id=entry["exercise_id"],
        sets=entry["sets"],
        reps_or_time=entry["reps_or_time"],
        rest_s=entry["rest_s"],
        target_rpe=float(entry["target_rpe"]),
        regression_alt=entry["regression_alt"],
        progression_alt=entry["progression_alt"],
    )


def _track(data: dict, key: str) -> dict[int, ExerciseInstance]:
    return {e["level"]: _entry_to_instance(e) for e in data[key]}


# ── Single-track loader (warmup, cooldown) ────────────────────────────────────

@lru_cache(maxsize=None)
def load_pattern_ladder(pattern_file: str) -> dict[int, ExerciseInstance]:
    """Load the 'levels' track from a YAML file. Used for single-track patterns."""
    data = _load_yaml(_EXERCISES_DIR / pattern_file)
    return _track(data, "levels")


# ── Multi-track loaders ───────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def load_squat_ladders() -> tuple[dict[int, ExerciseInstance], dict[int, ExerciseInstance]]:
    """Return (standard, knee_safe)."""
    data = _load_yaml(_EXERCISES_DIR / "squat.yaml")
    return _track(data, "standard"), _track(data, "knee_safe")


@lru_cache(maxsize=None)
def load_hinge_ladders() -> tuple[dict[int, ExerciseInstance], dict[int, ExerciseInstance]]:
    """Return (standard, lower_back_safe)."""
    data = _load_yaml(_EXERCISES_DIR / "hinge.yaml")
    return _track(data, "levels"), _track(data, "lower_back_safe")


@lru_cache(maxsize=None)
def load_push_ladders() -> tuple[
    dict[int, ExerciseInstance],
    dict[int, ExerciseInstance],
    dict[int, ExerciseInstance],
]:
    """Return (standard, shoulder_safe, wrist_safe)."""
    data = _load_yaml(_EXERCISES_DIR / "horizontal_push.yaml")
    return _track(data, "levels"), _track(data, "shoulder_safe"), _track(data, "wrist_safe")


@lru_cache(maxsize=None)
def load_pull_ladders() -> tuple[dict[int, ExerciseInstance], dict[int, ExerciseInstance]]:
    """Return (standard, shoulder_safe)."""
    data = _load_yaml(_EXERCISES_DIR / "pull.yaml")
    return _track(data, "levels"), _track(data, "shoulder_safe")


@lru_cache(maxsize=None)
def load_core_ladders() -> tuple[dict[int, ExerciseInstance], dict[int, ExerciseInstance]]:
    """Return (standard, lower_back_safe)."""
    data = _load_yaml(_EXERCISES_DIR / "core.yaml")
    return _track(data, "levels"), _track(data, "lower_back_safe")


@lru_cache(maxsize=None)
def load_balance_ladders() -> tuple[dict[int, ExerciseInstance], dict[int, ExerciseInstance]]:
    """Return (standard, hip_safe)."""
    data = _load_yaml(_EXERCISES_DIR / "single_leg_balance.yaml")
    return _track(data, "levels"), _track(data, "hip_safe")


# ── Fixed blocks ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def load_fixed_block(block_file: str) -> list[ExerciseInstance]:
    """Load a fixed (non-leveled) block such as warmup or cooldown."""
    data = _load_yaml(_EXERCISES_DIR / block_file)
    return [_entry_to_instance(e) for e in data["exercises"]]


# ── Exercise → pattern map ────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def build_exercise_pattern_map() -> dict[str, MovementPattern]:
    """
    Return a mapping of exercise_id → MovementPattern for all leveled patterns.
    Covers all tracks (standard and joint-flag safe variants).
    Fixed blocks (warmup, cooldown) are excluded — their exercises don't carry
    RPE that drives level changes.
    """
    result: dict[str, MovementPattern] = {}

    def _add(instances: dict[int, ExerciseInstance], pattern: MovementPattern) -> None:
        for inst in instances.values():
            result[inst.exercise_id] = pattern

    squat_std, squat_knee = load_squat_ladders()
    _add(squat_std, MovementPattern.SQUAT)
    _add(squat_knee, MovementPattern.SQUAT)

    hinge_std, hinge_lb = load_hinge_ladders()
    _add(hinge_std, MovementPattern.HINGE)
    _add(hinge_lb, MovementPattern.HINGE)

    push_std, push_sh, push_wr = load_push_ladders()
    _add(push_std, MovementPattern.HORIZONTAL_PUSH)
    _add(push_sh, MovementPattern.HORIZONTAL_PUSH)
    _add(push_wr, MovementPattern.HORIZONTAL_PUSH)

    pull_std, pull_sh = load_pull_ladders()
    _add(pull_std, MovementPattern.PULL)
    _add(pull_sh, MovementPattern.PULL)

    core_std, core_lb = load_core_ladders()
    _add(core_std, MovementPattern.CORE)
    _add(core_lb, MovementPattern.CORE)

    balance_std, balance_hip = load_balance_ladders()
    _add(balance_std, MovementPattern.SINGLE_LEG_BALANCE)
    _add(balance_hip, MovementPattern.SINGLE_LEG_BALANCE)

    return result
