from __future__ import annotations

import pathlib
from functools import lru_cache

from pgis_bodyweight.engine.types import ExerciseInstance

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


@lru_cache(maxsize=None)
def load_pattern_ladder(pattern_file: str) -> dict[int, ExerciseInstance]:
    """
    Load a single-track progression ladder from a YAML file.

    Returns a dict mapping level (int) → ExerciseInstance.
    Expects the YAML root key to be 'levels'.
    """
    data = _load_yaml(_EXERCISES_DIR / pattern_file)
    return {entry["level"]: _entry_to_instance(entry) for entry in data["levels"]}


@lru_cache(maxsize=None)
def load_squat_ladders() -> tuple[dict[int, ExerciseInstance], dict[int, ExerciseInstance]]:
    """
    Return (standard_track, knee_safe_track) for the squat pattern.

    Each track is a dict mapping level → ExerciseInstance.
    """
    data = _load_yaml(_EXERCISES_DIR / "squat.yaml")
    standard = {e["level"]: _entry_to_instance(e) for e in data["standard"]}
    knee_safe = {e["level"]: _entry_to_instance(e) for e in data["knee_safe"]}
    return standard, knee_safe


@lru_cache(maxsize=None)
def load_fixed_block(block_file: str) -> list[ExerciseInstance]:
    """
    Load a fixed (non-leveled) block such as warmup or cooldown.

    Expects the YAML root key to be 'exercises'.
    """
    data = _load_yaml(_EXERCISES_DIR / block_file)
    return [_entry_to_instance(e) for e in data["exercises"]]
