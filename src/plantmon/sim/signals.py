"""Generate seeded simulated signals from a profile, as a physical and a reported layer.

Physical: base + daily sine + AR(1) noise + context, or offset + gain x the source's physical value.
Reported: physical + independent measurement noise.
"""

import math
import zlib
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import numpy as np

from plantmon.core.profile import generation_order

# Third seed word: keeps measurement noise apart from the process noise of the same sensor.
MEASUREMENT_STREAM = 1


@dataclass(frozen=True)
class Simulation:
    physical: dict[str, np.ndarray]
    reported: dict[str, np.ndarray]  # The only layer that is stored.


def add_months(start: date, months: int) -> date:
    years, month_index = divmod(start.month - 1 + months, 12)
    return start.replace(year=start.year + years, month=month_index + 1)


def split_bounds(profile: dict) -> dict[str, tuple[datetime, datetime]]:
    """Return the half-open [start, end) time range of each split, in order, apart by the gap."""
    run = profile["run"]
    gap = timedelta(days=run["split_gap_days"])
    bounds = {}
    begin = run["start"]
    for name, months in run["split_months"].items():
        # Day 29-31 does not exist in every month, so the split's end would be ambiguous.
        if begin.day > 28:
            raise ValueError(f"split {name} starts on day {begin.day}; run.start must avoid this")
        end = add_months(begin, months)
        bounds[name] = (_utc(begin), _utc(end))
        begin = end + gap
    return bounds


def timestamps(profile: dict) -> list[datetime]:
    """Return the sample times inside the splits. Gap times are never exposed."""
    continuous = _continuous_times(profile)
    return [t for t, kept in zip(continuous, _in_a_split(profile, continuous)) if kept]


def context_states(profile: dict, times: list[datetime]) -> list[str] | None:
    """Return the state per timestamp, or None when the profile defines no context channel."""
    if "context" not in profile:
        return None
    state_by_hour = {}
    for state, (first, last) in profile["context"]["schedule"]["daily_hours"].items():
        state_by_hour.update(dict.fromkeys(range(first, last), state))
    return [state_by_hour[t.hour] for t in times]


def simulate(profile: dict, seed: int) -> Simulation:
    """Return both layers per sensor. Each has its own streams, so adding one changes no other.

    Signals run over the continuous timeline, so AR(1) noise carries across a gap, and the gap
    samples are dropped before anything is returned.
    """
    continuous = _continuous_times(profile)
    hours = np.array([(t - continuous[0]).total_seconds() / 3600 for t in continuous])
    states = context_states(profile, continuous)
    sensors = {s["id"]: s for s in profile["sensors"]}

    full = {}
    for sensor_id in generation_order(profile["sensors"]):
        follows = sensors[sensor_id].get("follows")
        if follows:
            full[sensor_id] = follows["offset"] + follows["gain"] * full[follows["source"]]
        else:
            full[sensor_id] = _signal(sensors[sensor_id], hours, states, seed)

    kept = np.array(_in_a_split(profile, continuous))
    physical = {sensor_id: series[kept] for sensor_id, series in full.items()}
    reported = {
        sensor_id: physical[sensor_id] + _measurement_noise(sensor, int(kept.sum()), seed)
        for sensor_id, sensor in sensors.items()
    }
    return Simulation(physical, reported)


def _continuous_times(profile: dict) -> list[datetime]:
    bounds = split_bounds(profile).values()
    start = min(b[0] for b in bounds)
    end = max(b[1] for b in bounds)
    step = timedelta(minutes=profile["sampling"]["interval_minutes"])
    return [start + i * step for i in range((end - start) // step)]


def _in_a_split(profile: dict, times: list[datetime]) -> list[bool]:
    bounds = split_bounds(profile).values()
    return [any(low <= t < high for low, high in bounds) for t in times]


def _signal(sensor: dict, hours: np.ndarray, states: list[str] | None, seed: int) -> np.ndarray:
    spec = sensor["signal"]
    rng = np.random.default_rng([seed, zlib.crc32(sensor["id"].encode())])
    # hours counts from a midnight, so this is wall-clock time; the phase delays the daily cycle.
    cycle = np.sin(2 * math.pi * (hours - spec.get("daily_phase_hours", 0)) / 24)
    values = spec["base"] + spec["daily_amplitude"] * cycle
    values = values + _ar1_noise(rng, len(hours), spec["noise_std"], spec["ar1"])
    offsets = spec.get("state_offset")
    if offsets and states:
        values = values + np.array([offsets.get(state, 0.0) for state in states])
    return values


def _measurement_noise(sensor: dict, n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng([seed, zlib.crc32(sensor["id"].encode()), MEASUREMENT_STREAM])
    return rng.normal(0.0, sensor.get("measurement_noise_std", 0.0), n)


def _ar1_noise(rng: np.random.Generator, n: int, std: float, ar1: float) -> np.ndarray:
    # The innovation is scaled so that noise_std is the stationary standard deviation.
    innovations = rng.normal(0.0, std * math.sqrt(1 - ar1**2), n)
    noise = np.empty(n)
    previous = rng.normal(0.0, std)
    for i, innovation in enumerate(innovations):
        previous = ar1 * previous + innovation
        noise[i] = previous
    return noise


def _utc(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)
