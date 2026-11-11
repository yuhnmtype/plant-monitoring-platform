"""Load and validate a plant profile from YAML."""

import math
from datetime import date
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from ruamel.yaml import YAML

SECTIONS = (
    "profile",
    "sampling",
    "run",
    "assets",
    "sensors",
    "incident_schedule",
    "incident_classes",
)
SENSOR_KINDS = {"measurement", "command", "position"}
INCIDENT_TYPES = {"fault", "attack"}
SPLITS = ("train", "validation", "test")
FOLLOWS_KEYS = {"source", "gain", "offset"}


def load_profile(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        profile = YAML(typ="safe").load(f)
    validate_profile(profile)
    return profile


def generation_order(sensors: list[dict]) -> list[str]:
    """Return sensor ids with every source before its followers."""
    graph = {s["id"]: [s["follows"]["source"]] if "follows" in s else [] for s in sensors}
    return list(TopologicalSorter(graph).static_order())


def validate_profile(p: dict) -> None:
    errors = _errors(p)
    if errors:
        raise ValueError("invalid profile: " + "; ".join(errors))


def _errors(p: dict) -> list[str]:
    missing = [s for s in SECTIONS if not isinstance(p, dict) or s not in p]
    if missing:
        return [f"missing section {s}" for s in missing]

    errors = []
    if p["profile"].get("simulated") is not True:
        errors.append("profile.simulated must be true")
    interval = p["sampling"].get("interval_minutes")
    # Split boundaries are midnights, so the sampling grid must hit every midnight.
    if not isinstance(interval, int) or interval <= 0 or 1440 % interval:
        errors.append("sampling.interval_minutes must be a positive integer that divides a day")

    start = p["run"].get("start")
    # Day 29-31 does not exist in every month, so split boundaries would be ambiguous.
    if not isinstance(start, date) or start.day > 28:
        errors.append("run.start must be a date with day 1-28")
    months = p["run"].get("split_months", {})
    if tuple(months) != SPLITS or not all(isinstance(m, int) and m > 0 for m in months.values()):
        errors.append(f"run.split_months must give positive integers for {SPLITS}")
    gap = p["run"].get("split_gap_days")
    if not isinstance(gap, int) or isinstance(gap, bool) or gap < 0:
        errors.append("run.split_gap_days must be a whole number of days, not negative")

    states = set(p.get("context", {}).get("states", []))
    if "context" in p:
        errors += _context_errors(p["context"], states)

    assets = {a["id"] for a in p["assets"]}
    sensor_ids = [s["id"] for s in p["sensors"]]
    if len(set(sensor_ids)) != len(sensor_ids):
        errors.append("sensor ids must be unique")
    for s in p["sensors"]:
        errors += _sensor_errors(s, assets, states, set(sensor_ids))
    if not errors:
        try:
            generation_order(p["sensors"])
        except CycleError as e:
            errors.append(f"follows cycle: {' -> '.join(e.args[1])}")

    class_ids = [c["id"] for c in p["incident_classes"]]
    if len(set(class_ids)) != len(class_ids):
        errors.append("incident class ids must be unique")
    for c in p["incident_classes"]:
        low, high = c["duration_hours"]
        if c["type"] not in INCIDENT_TYPES:
            errors.append(f"incident class {c['id']}: unknown type {c['type']}")
        if not 0 < low <= high:
            errors.append(f"incident class {c['id']}: bad duration_hours")
    return errors


def _sensor_errors(s: dict, assets: set, states: set, sensor_ids: set) -> list[str]:
    errors = []
    if s["asset"] not in assets:
        errors.append(f"sensor {s['id']}: unknown asset {s['asset']}")
    if s["kind"] not in SENSOR_KINDS:
        errors.append(f"sensor {s['id']}: unknown kind {s['kind']}")
    if not s["nominal_range"][0] < s["nominal_range"][1]:
        errors.append(f"sensor {s['id']}: bad nominal_range")
    noise = s.get("measurement_noise_std", 0)
    if not _is_finite(noise) or noise < 0:
        errors.append(f"sensor {s['id']}: measurement_noise_std must be finite and not negative")
    if "follows" in s:
        return errors + _follows_errors(s, states, sensor_ids)
    if "signal" not in s:
        return errors + [f"sensor {s['id']}: needs a signal or follows block"]
    return errors + _signal_errors(s, states)


def _follows_errors(s: dict, states: set, sensor_ids: set) -> list[str]:
    errors = []
    follows = s["follows"]
    if "signal" in s:
        errors.append(f"sensor {s['id']}: follows must not be combined with a signal block")
    if not isinstance(follows, dict) or set(follows) != FOLLOWS_KEYS:
        return errors + [f"sensor {s['id']}: follows must have exactly {sorted(FOLLOWS_KEYS)}"]
    source = follows["source"]
    if source == s["id"]:
        errors.append(f"sensor {s['id']}: follows itself")
    elif source == "context" or source in states:
        errors.append(f"sensor {s['id']}: follows source {source} is a context channel")
    elif source not in sensor_ids:
        errors.append(f"sensor {s['id']}: unknown follows source {source}")
    for key in ("gain", "offset"):
        if not _is_finite(follows[key]):
            errors.append(f"sensor {s['id']}: follows {key} must be finite")
    return errors


def _is_finite(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _signal_errors(s: dict, states: set) -> list[str]:
    errors = []
    signal = s["signal"]
    if not 0 <= signal["ar1"] < 1:
        errors.append(f"sensor {s['id']}: ar1 must be in [0, 1)")
    if not _is_finite(signal.get("daily_phase_hours", 0)):
        errors.append(f"sensor {s['id']}: daily_phase_hours must be finite")
    if signal["noise_std"] < 0:
        errors.append(f"sensor {s['id']}: noise_std must not be negative")
    unknown = set(signal.get("state_offset", {})) - states
    if unknown:
        errors.append(f"sensor {s['id']}: unknown states {sorted(unknown)}")
    return errors


def _context_errors(context: dict, states: set) -> list[str]:
    hours = context.get("schedule", {}).get("daily_hours", {})
    if set(hours) != states:
        return ["context.schedule.daily_hours must list every state"]
    covered = sorted(h for span in hours.values() for h in range(span[0], span[1]))
    if covered != list(range(24)):
        return ["context.schedule.daily_hours must cover each hour of the day exactly once"]
    return []
