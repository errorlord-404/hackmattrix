"""Deterministic, field-scoped Tomato demo soil simulator.

The simulator is intentionally pure apart from the values supplied by the
router. It produces bounded values from a scenario and tick number so a
hackathon demo is repeatable and never depends on ambient randomness.
"""

from __future__ import annotations

import math
from typing import Any

SOURCE = "simulation:tomato-demo:v1"
TICK_INTERVAL_SECONDS = 15
MEASUREMENTS = (
    ("moisture", "%"),
    ("temperature", "°C"),
    ("ph", "pH"),
    ("ec", "mS/cm"),
    ("nitrogen", "mg/kg"),
    ("phosphorus", "mg/kg"),
    ("potassium", "mg/kg"),
)
SCENARIOS = ("balanced", "water-stress", "nitrogen-low", "salinity-risk", "alkaline-soil")


def _offset(seed: int, tick: int, scale: float) -> float:
    """Return deterministic, bounded variation for a seed/tick pair."""

    return math.sin((seed + 1) * 0.71 + tick * 0.63) * scale


def initial_values(scenario: str, seed: int) -> dict[str, float]:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unsupported Tomato demo scenario: {scenario}")
    bases: dict[str, float] = {
        "balanced": {"moisture": 42.0, "temperature": 25.4, "ph": 6.5, "ec": 0.8, "nitrogen": 310.0, "phosphorus": 38.0, "potassium": 265.0},
        "water-stress": {"moisture": 34.0, "temperature": 29.5, "ph": 6.6, "ec": 1.0, "nitrogen": 305.0, "phosphorus": 38.0, "potassium": 260.0},
        "nitrogen-low": {"moisture": 41.0, "temperature": 26.0, "ph": 6.4, "ec": 0.9, "nitrogen": 255.0, "phosphorus": 40.0, "potassium": 270.0},
        "salinity-risk": {"moisture": 36.0, "temperature": 28.0, "ph": 7.1, "ec": 2.2, "nitrogen": 300.0, "phosphorus": 35.0, "potassium": 250.0},
        "alkaline-soil": {"moisture": 39.0, "temperature": 26.5, "ph": 8.1, "ec": 1.0, "nitrogen": 290.0, "phosphorus": 28.0, "potassium": 245.0},
    }[scenario].copy()
    bases["moisture"] += _offset(seed, 0, 0.8)
    bases["temperature"] += _offset(seed, 0, 0.4)
    return _round_values(bases)


def advance_values(
    values: dict[str, Any],
    scenario: str,
    seed: int,
    tick: int,
    irrigation_ticks_remaining: int = 0,
) -> tuple[dict[str, float], int]:
    """Advance one simulation tick and return values plus remaining irrigation ticks."""

    next_values = {key: float(value) for key, value in values.items()}
    next_values["temperature"] += _offset(seed, tick, 0.22)
    next_values["moisture"] += _offset(seed + 4, tick, 0.35)

    if scenario == "water-stress":
        next_values["moisture"] -= 1.25
        next_values["temperature"] += 0.08
    elif scenario == "nitrogen-low":
        next_values["nitrogen"] -= 1.2
        next_values["phosphorus"] += _offset(seed + 2, tick, 0.25)
    elif scenario == "salinity-risk":
        next_values["ec"] += 0.08
        next_values["moisture"] -= 0.15
    elif scenario == "alkaline-soil":
        next_values["ph"] += 0.015

    remaining = max(0, int(irrigation_ticks_remaining))
    if remaining:
        next_values["moisture"] += 5.5
        next_values["ec"] -= 0.12
        remaining -= 1

    return _round_values(next_values), remaining


def _round_values(values: dict[str, float]) -> dict[str, float]:
    bounds = {
        "moisture": (0.0, 100.0), "temperature": (-10.0, 60.0), "ph": (3.0, 11.0),
        "ec": (0.0, 8.0), "nitrogen": (0.0, 1000.0), "phosphorus": (0.0, 500.0),
        "potassium": (0.0, 1000.0),
    }
    normalized: dict[str, float] = {}
    for key, value in values.items():
        lower, upper = bounds[key]
        normalized[key] = round(min(max(float(value), lower), upper), 2)
    return normalized


def observations(values: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"measurement": measurement, "value": float(values[measurement]), "unit": unit}
        for measurement, unit in MEASUREMENTS
    ]
