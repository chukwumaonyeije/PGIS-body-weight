"""
Per-pattern level autoregulation.

Pure: no network, no DB, no I/O. exercise_pattern_map is injected by the caller.

Rule:
  mean RPE ≤ 6.0 for a pattern → advance one level (capped at max_level)
  mean RPE > 6.0               → hold
  no RPE data for a pattern    → hold
  exercise_id absent from map  → ignored (warmup/cooldown exercises)
"""
from __future__ import annotations

from pgis_bodyweight.engine.types import MovementPattern

RPE_ADVANCE_THRESHOLD = 6.0


def autoregulate(
    per_exercise_rpe: dict[str, float],
    current_levels: dict[MovementPattern, int],
    exercise_pattern_map: dict[str, MovementPattern],
    max_level: int = 3,
) -> dict[MovementPattern, int]:
    """
    Return new per-pattern levels after applying one session of RPE data.

    Patterns absent from per_exercise_rpe are unchanged.
    """
    pattern_rpes: dict[MovementPattern, list[float]] = {}
    for exercise_id, rpe in per_exercise_rpe.items():
        pattern = exercise_pattern_map.get(exercise_id)
        if pattern is None:
            continue
        pattern_rpes.setdefault(pattern, []).append(rpe)

    new_levels = dict(current_levels)
    for pattern, rpes in pattern_rpes.items():
        mean_rpe = sum(rpes) / len(rpes)
        if mean_rpe <= RPE_ADVANCE_THRESHOLD:
            new_levels[pattern] = min(current_levels[pattern] + 1, max_level)

    return new_levels
