"""Generate and validate the labelled incident schedule. Incidents are not injected into signals."""

import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from plantmon.sim.signals import split_bounds

SPLITS_WITH_INCIDENTS = ("validation", "test")


@dataclass(frozen=True)
class Incident:
    class_id: str
    incident_type: str
    split: str
    start: datetime
    end: datetime  # exclusive


def generate_schedule(profile: dict, seed: int) -> list[Incident]:
    rng = np.random.default_rng([seed, zlib.crc32(b"incident_schedule")])
    bounds = split_bounds(profile)
    incidents = []
    for split in SPLITS_WITH_INCIDENTS:
        incidents += _schedule_split(profile, split, bounds[split], rng)
    return incidents


def _schedule_split(
    profile: dict,
    split: str,
    bounds: tuple[datetime, datetime],
    rng: np.random.Generator,
) -> list[Incident]:
    rules = profile["incident_schedule"]
    step = timedelta(minutes=profile["sampling"]["interval_minutes"])
    steps_per_hour = timedelta(hours=1) / step

    classes = [c for c in profile["incident_classes"] for _ in range(rules["min_per_class"])]
    rng.shuffle(classes)
    durations = [
        int(rng.integers(c["duration_hours"][0] * steps_per_hour,
                         c["duration_hours"][1] * steps_per_hour + 1))
        for c in classes
    ]

    margin = timedelta(hours=rules["boundary_margin_hours"])
    gap_steps = int(rules["min_gap_hours"] * steps_per_hour)
    window_start = bounds[0] + margin
    window_steps = (bounds[1] - margin - window_start) // step
    free_steps = window_steps - sum(durations) - (len(classes) - 1) * gap_steps
    if free_steps < 0:
        raise ValueError(f"{split}: incidents and gaps do not fit in the split")

    # Sorted cut points in the free time keep incidents ordered and apart by construction.
    cuts = np.sort(rng.integers(0, free_steps + 1, len(classes)))
    incidents = []
    used_steps = 0
    for c, duration, cut in zip(classes, durations, cuts):
        start = window_start + (int(cut) + used_steps) * step
        end = start + duration * step
        incidents.append(Incident(c["id"], c["type"], split, start, end))
        used_steps += duration + gap_steps
    return incidents


def validate_schedule(profile: dict, incidents: list[Incident]) -> list[str]:
    """Return every violated rule. An empty list means the schedule is valid."""
    rules = profile["incident_schedule"]
    margin = timedelta(hours=rules["boundary_margin_hours"])
    min_gap = timedelta(hours=rules["min_gap_hours"])
    bounds = split_bounds(profile)
    errors = []

    for inc in incidents:
        if inc.split not in SPLITS_WITH_INCIDENTS:
            errors.append(f"incident in split {inc.split}: {inc.class_id} at {inc.start}")
        if inc.end <= inc.start:
            errors.append(f"empty incident: {inc.class_id} at {inc.start}")
        if inc.split in bounds:
            low, high = bounds[inc.split]
            if inc.start < low + margin or inc.end > high - margin:
                errors.append(f"inside boundary margin or crossing: {inc.class_id} at {inc.start}")

    ordered = sorted(incidents, key=lambda i: i.start)
    for first, second in zip(ordered, ordered[1:]):
        if second.start < first.end:
            errors.append(f"overlap: {first.class_id} and {second.class_id} at {second.start}")
        elif second.start - first.end < min_gap:
            errors.append(f"gap too short: {first.class_id} and {second.class_id}")

    for split in SPLITS_WITH_INCIDENTS:
        for c in profile["incident_classes"]:
            count = sum(i.split == split and i.class_id == c["id"] for i in incidents)
            if count < rules["min_per_class"]:
                errors.append(f"{split}: {count} incidents of {c['id']}")
    for split in bounds:
        share = anomalous_share(profile, incidents, split)
        if share > rules["max_anomalous_share"]:
            errors.append(f"{split}: anomalous share {share:.4f}")
    return errors


def anomalous_share(profile: dict, incidents: list[Incident], split: str) -> float:
    low, high = split_bounds(profile)[split]
    # Valid schedules have no overlaps; a broken one is reported by the overlap rule as well.
    anomalous = sum((i.end - i.start for i in incidents if i.split == split), timedelta())
    return anomalous / (high - low)
