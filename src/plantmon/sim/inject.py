"""Put the scheduled incidents into a clean simulation. All data is simulated.

Post-processing only: the clean run is generated first and no random stream of it is touched, so
every sample outside an incident window stays bit for bit the same. A class of the profile is
injected only when it has an `injection` block; the profile loader validates that block.

Order (docs/specs/m3.md): command_override on a source, then its followers, then scale_relation,
then the same measurement noise as the clean run, then the changes to the reported layer.
"""

import zlib
from bisect import bisect_left
from datetime import datetime, timedelta

import numpy as np

from plantmon.core.profile import MIN_LAG_HOURS, generation_order
from plantmon.sim.schedule import Incident
from plantmon.sim.signals import (
    Simulation,
    _measurement_noise,
    simulate,
    split_bounds,
    timestamps,
)

# Primitives not listed here change the reported layer only and run last.
PHASE = {"command_override": 0, "scale_relation": 1}
SIGNS = {"negative": -1, "positive": 1}


def simulate_run(
    profile: dict, seed: int, incidents: list[Incident], injection: bool = True
) -> Simulation:
    """Return the simulation of one run. With injection off it is exactly the clean simulation.

    incidents is the whole schedule of the run: a replay must not copy from any of its windows.
    """
    clean = simulate(profile, seed)
    specs = {c["id"]: c["injection"] for c in profile["incident_classes"] if "injection" in c}
    chosen = [i for i in incidents if i.class_id in specs]
    if not injection or not chosen:
        return clean

    times = timestamps(profile)
    step = timedelta(minutes=profile["sampling"]["interval_minutes"])
    sigma = sigma_s(profile, clean.reported)
    sensors = {s["id"]: s for s in profile["sensors"]}
    noise = {sid: _measurement_noise(s, len(times), seed) for sid, s in sensors.items()}
    physical = {sid: series.copy() for sid, series in clean.physical.items()}
    reported = {sid: series.copy() for sid, series in clean.reported.items()}

    for incident in sorted(chosen, key=lambda i: PHASE.get(specs[i.class_id]["primitive"], 2)):
        spec = specs[incident.class_id]
        primitive = spec["primitive"]
        w = _window(times, incident.start, incident.end, step)
        rng = _incident_rng(seed, incident)

        if primitive == "replay":
            lag = timedelta(hours=_draw_lag(rng, profile, incident, incidents, spec))
            source = _window(times, incident.start - lag, incident.end - lag, step)
            for target in spec["targets"]:
                reported[target][w] = clean.reported[target][source]
            continue

        target = spec["targets"][rng.integers(len(spec["targets"]))]
        if primitive == "hold":
            reported[target][w] = reported[target][w.start]
            continue

        magnitude = rng.uniform(*spec["magnitude"])
        sign = SIGNS.get(spec.get("sign", "random")) or rng.choice((-1, 1))
        delta = sign * magnitude * sigma[target]

        if primitive == "slope":
            reported[target][w] += delta * np.linspace(0, 1, w.stop - w.start)
        elif primitive == "step_offset":
            reported[target][w] += delta
        elif primitive == "scale_relation":
            offset = sensors[target]["follows"]["offset"]
            part = physical[target][w] - offset
            mean = np.abs(part).mean()
            if mean == 0:
                raise ValueError(f"{incident.class_id} at {incident.start}: {target} has no part"
                                 " above its offset to scale")
            # s = 1 -/+ q with q = magnitude x sigma_s / mean(|v - offset|)
            physical[target][w] = offset + (1 + delta / mean) * part
            reported[target][w] = physical[target][w] + noise[target][w]
        elif primitive == "command_override":
            physical[target][w] += delta
            changed = [target]
            for sid in generation_order(profile["sensors"]):
                follows = sensors[sid].get("follows")
                if follows and follows["source"] in changed:
                    source_values = physical[follows["source"]][w]
                    physical[sid][w] = follows["offset"] + follows["gain"] * source_values
                    changed.append(sid)
            for sid in changed:
                reported[sid][w] = physical[sid][w] + noise[sid][w]
        else:
            raise ValueError(f"unknown primitive {primitive}")

    return Simulation(physical, reported)


def sigma_s(profile: dict, reported: dict[str, np.ndarray]) -> dict[str, float]:
    """Return per sensor the std (ddof 1) of the training values minus their time-of-day mean."""
    train_end = split_bounds(profile)["train"][1]
    interval = profile["sampling"]["interval_minutes"]
    times = timestamps(profile)
    n_train = bisect_left(times, train_end)
    slots = np.array([(t.hour * 60 + t.minute) // interval for t in times[:n_train]])
    counts = np.bincount(slots)
    result = {}
    for sensor_id, series in reported.items():
        values = series[:n_train]
        slot_mean = np.bincount(slots, weights=values) / counts
        result[sensor_id] = float((values - slot_mean[slots]).std(ddof=1))
    return result


def valid_replay_lags(
    profile: dict, incident: Incident, incidents: list[Incident], max_lag_hours: int
) -> list[int]:
    """Whole hours whose source stretch is inside the split and overlaps no incident window."""
    split_start = split_bounds(profile)[incident.split][0]
    step = timedelta(minutes=profile["sampling"]["interval_minutes"])
    lags = []
    for hours in range(MIN_LAG_HOURS, max_lag_hours + 1):
        lag = timedelta(hours=hours)
        start, end = incident.start - lag, incident.end - lag
        # A multiple of 24 h would be aligned with the time of day (a known limit, not measured).
        if hours % 24 == 0 or lag % step or start < split_start:
            continue
        if not any(start < other.end and other.start < end for other in incidents):
            lags.append(hours)
    return lags


def _draw_lag(
    rng: np.random.Generator,
    profile: dict,
    incident: Incident,
    incidents: list[Incident],
    spec: dict,
) -> int:
    valid = set(valid_replay_lags(profile, incident, incidents, spec["max_lag_hours"]))
    # The order of preference depends on this incident only; other incidents can just rule one out.
    for hours in rng.permutation(np.arange(MIN_LAG_HOURS, spec["max_lag_hours"] + 1)):
        if int(hours) in valid:
            return int(hours)
    raise ValueError(
        f"no valid replay lag for incident class {incident.class_id} at {incident.start}"
        f" ({incident.split}) within {spec['max_lag_hours']} h"
    )


def _incident_rng(seed: int, incident: Incident) -> np.random.Generator:
    """A stream of its own per incident: it does not depend on the other incidents."""
    return np.random.default_rng(
        [
            seed,
            zlib.crc32(b"injection"),
            zlib.crc32(incident.class_id.encode()),
            int(incident.start.timestamp()),
        ]
    )


def _window(times: list[datetime], start: datetime, end: datetime, step: timedelta) -> slice:
    """Return the samples of [start, end). Every one of them must exist."""
    first, last = bisect_left(times, start), bisect_left(times, end)
    if last <= first or (last - first) * step != end - start or times[first] != start:
        raise ValueError(f"window {start} to {end} is not fully covered by samples")
    return slice(first, last)
