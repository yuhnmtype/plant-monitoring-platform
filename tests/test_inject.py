"""Incident injection on a small neutral synthetic profile. All data is simulated.

Sensors: a is a constant source (10) with measurement noise, b = 5 + 2a, c = 100 + b without
noise, d is an independent noisy signal. So the expected injected values can be worked out by hand.
"""

import subprocess
import sys
import types
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from plantmon.core.profile import load_profile, validate_profile
from plantmon.sim.inject import sigma_s, simulate_run, valid_replay_lags
from plantmon.sim.schedule import Incident, generate_schedule, validate_schedule
from plantmon.sim.signals import simulate, timestamps

# The last commit before any injection code existed.
BEFORE_INJECTION = "d1fadf1"
START = datetime(2025, 2, 14, tzinfo=UTC)  # inside validation, which starts on 2025-02-08
HOUR = timedelta(hours=1)
BLOCKS = {
    "k_slope": {"primitive": "slope", "targets": ["d"], "magnitude": [3, 3], "sign": "positive"},
    "k_hold": {"primitive": "hold", "targets": ["d"]},
    "k_step": {"primitive": "step_offset", "targets": ["a", "d"], "magnitude": [2, 6]},
    "k_scale": {"primitive": "scale_relation", "targets": ["b"], "magnitude": [2, 6]},
    "k_replay": {"primitive": "replay", "targets": ["a", "b", "c", "d"], "max_lag_hours": 168},
    "k_command": {"primitive": "command_override", "targets": ["a"], "magnitude": [2, 6]},
}


def _profile(blocks: dict = BLOCKS) -> dict:
    flat = {"base": 10, "daily_amplitude": 0, "noise_std": 0.0, "ar1": 0.0}
    common = {"asset": "a1", "kind": "measurement", "unit": "u", "nominal_range": [0, 200]}
    return {
        "profile": {"id": "test_inject", "name": "Neutral injection profile", "simulated": True},
        "sampling": {"interval_minutes": 60},
        "run": {
            "start": date(2025, 1, 1),
            "split_gap_days": 7,
            "split_months": {"train": 1, "validation": 1, "test": 1},
        },
        "assets": [{"id": "a1", "name": "Asset one", "kind": "generic"}],
        "sensors": [
            {**common, "id": "a", "signal": flat, "measurement_noise_std": 1.0},
            {
                **common,
                "id": "b",
                "follows": {"source": "a", "gain": 2.0, "offset": 5.0},
                "measurement_noise_std": 1.0,
            },
            {**common, "id": "c", "follows": {"source": "b", "gain": 1.0, "offset": 100.0}},
            {
                **common,
                "id": "d",
                "signal": {"base": 50, "daily_amplitude": 5, "noise_std": 1.0, "ar1": 0.5},
            },
        ],
        "incident_schedule": {
            "min_per_class": 2,
            "max_anomalous_share": 0.2,
            "boundary_margin_hours": 48,
            "min_gap_hours": 12,
        },
        "incident_classes": [
            {"id": class_id, "type": "fault", "duration_hours": [3, 5], "injection": dict(block)}
            for class_id, block in blocks.items()
        ],
    }


def _incident(class_id: str = "x", start: datetime = START, hours: int = 5) -> Incident:
    return Incident(class_id, "fault", "validation", start, start + hours * HOUR)


def _one(**block):
    """Inject a single five-hour incident. Return (clean, injected, window, sigma)."""
    profile = _profile({"x": block})
    validate_profile(profile)
    clean = simulate(profile, 42)
    injected = simulate_run(profile, 42, [_incident()])
    first = timestamps(profile).index(START)
    return clean, injected, slice(first, first + 5), sigma_s(profile, clean.reported)


def _assert_unchanged(clean, injected, sensor_ids, where=slice(None)):
    for sensor_id in sensor_ids:
        for layer in ("physical", "reported"):
            before = getattr(clean, layer)[sensor_id][where]
            after = getattr(injected, layer)[sensor_id][where]
            assert np.array_equal(before, after), f"{layer} {sensor_id} changed"


def test_sigma_s_is_the_std_around_the_time_of_day_mean_of_the_training_split():
    profile = _profile()
    times = timestamps(profile)
    # Training is January: +1 on days 1-15, -1 on days 16-30, 0 on day 31, around 10 x hour.
    # Every time-of-day mean is exactly 10 x hour, so the residuals are 360 of +1, 360 of -1 and
    # 24 zeros: std (ddof 1) = sqrt(720 / 743). Later samples are junk and must not count.
    series = np.array(
        [
            10 * t.hour + (1 if t.day <= 15 else -1 if t.day <= 30 else 0)
            if t.month == 1
            else 1e9 * (i % 7)
            for i, t in enumerate(times)
        ],
        dtype=float,
    )
    assert sigma_s(profile, {"a": series})["a"] == pytest.approx(np.sqrt(720 / 743), rel=1e-12)


def test_slope_goes_linearly_from_zero_to_the_peak():
    clean, injected, w, sigma = _one(
        primitive="slope", targets=["d"], magnitude=[3, 3], sign="positive"
    )
    expected = 3 * sigma["d"] * np.array([0, 0.25, 0.5, 0.75, 1])
    assert injected.reported["d"][w] - clean.reported["d"][w] == pytest.approx(expected)
    assert np.array_equal(injected.physical["d"], clean.physical["d"])
    _assert_unchanged(clean, injected, "abc")


def test_hold_repeats_the_first_value_of_the_window():
    clean, injected, w, _ = _one(primitive="hold", targets=["d"])
    assert np.array_equal(injected.reported["d"][w], np.full(5, clean.reported["d"][w.start]))
    assert not np.array_equal(injected.reported["d"][w], clean.reported["d"][w])
    assert np.array_equal(injected.physical["d"], clean.physical["d"])
    _assert_unchanged(clean, injected, "abc")


@pytest.mark.parametrize(("sign", "factor"), [("positive", 3), ("negative", -3)])
def test_step_offset_adds_a_step_to_the_reported_value_only(sign, factor):
    clean, injected, w, sigma = _one(
        primitive="step_offset", targets=["a"], magnitude=[3, 3], sign=sign
    )
    difference = injected.reported["a"][w] - clean.reported["a"][w]
    assert difference == pytest.approx(np.full(5, factor * sigma["a"]))
    # The followers of a do not respond: only what a reports changed.
    assert np.array_equal(injected.physical["a"], clean.physical["a"])
    _assert_unchanged(clean, injected, "bcd")


@pytest.mark.parametrize(("sign", "direction"), [("negative", -1), ("positive", 1)])
def test_scale_relation_on_a_hand_computed_case(sign, direction):
    clean, injected, w, sigma = _one(
        primitive="scale_relation", targets=["b"], magnitude=[3, 3], sign=sign
    )
    # b = 5 + 2 x 10 = 25 and offset = 5, so |v - offset| = 20 and q = 3 x sigma / 20.
    assert np.array_equal(clean.physical["b"][w], np.full(5, 25.0))
    q = 3 * sigma["b"] / 20
    expected = 5 + (1 + direction * q) * 20
    assert expected == pytest.approx(25 + direction * 3 * sigma["b"])
    assert injected.physical["b"][w] == pytest.approx(np.full(5, expected))
    # The measurement noise of the clean run is still on top.
    noise = clean.reported["b"][w] - clean.physical["b"][w]
    assert injected.reported["b"][w] == pytest.approx(injected.physical["b"][w] + noise)
    # c follows b but does not respond to a scaled relation.
    _assert_unchanged(clean, injected, "acd")


def test_scale_relation_uses_the_mean_absolute_part_over_a_varying_window():
    profile = _profile({"x": {"primitive": "scale_relation", "targets": ["b"],
                              "magnitude": [2, 2], "sign": "negative"}})
    profile["sensors"][0]["signal"] = {
        "base": 10, "daily_amplitude": 4, "noise_std": 0.0, "ar1": 0.0
    }
    clean = simulate(profile, 42)
    injected = simulate_run(profile, 42, [_incident()])
    first = timestamps(profile).index(START)
    w = slice(first, first + 5)
    sigma = sigma_s(profile, clean.reported)["b"]
    part = clean.physical["b"][w] - 5
    assert np.ptp(part) > 0
    q = 2 * sigma / np.abs(part).mean()
    assert injected.physical["b"][w] == pytest.approx(5 + (1 - q) * part)
    assert np.abs(injected.physical["b"][w] - clean.physical["b"][w]).mean() == pytest.approx(
        2 * sigma
    )


def test_command_override_moves_the_source_and_its_followers_respond():
    clean, injected, w, sigma = _one(
        primitive="command_override", targets=["a"], magnitude=[3, 3], sign="positive"
    )
    step = 3 * sigma["a"]
    assert injected.physical["a"][w] == pytest.approx(np.full(5, 10 + step))
    assert injected.physical["b"][w] == pytest.approx(np.full(5, 25 + 2 * step))
    assert injected.physical["c"][w] == pytest.approx(np.full(5, 125 + 2 * step))
    for sensor_id in "abc":
        noise = clean.reported[sensor_id][w] - clean.physical[sensor_id][w]
        expected = injected.physical[sensor_id][w] + noise
        assert injected.reported[sensor_id][w] == pytest.approx(expected)
    _assert_unchanged(clean, injected, "d")
    for outside in (slice(0, w.start), slice(w.stop, None)):
        _assert_unchanged(clean, injected, "abc", outside)


def test_replay_copies_the_source_stretch_exactly():
    # With a bound of 25 h the only possible lag is 25 h.
    clean, injected, w, _ = _one(primitive="replay", targets=["a", "d"], max_lag_hours=25)
    source = slice(w.start - 25, w.stop - 25)
    for sensor_id in "ad":
        assert np.array_equal(injected.reported[sensor_id][w], clean.reported[sensor_id][source])
        assert np.array_equal(injected.physical[sensor_id], clean.physical[sensor_id])
    _assert_unchanged(clean, injected, "bc")


def test_replay_lags_obey_the_bounds_and_avoid_every_incident():
    profile = _profile()
    incident = _incident("k_replay", START)
    # Another incident from 30 h to 28 h before: lags 29..34 would copy part of it.
    other = _incident("k_hold", START - 30 * HOUR, hours=2)
    lags = valid_replay_lags(profile, incident, [incident, other], 50)
    assert lags == [25, 26, 27, 28, *range(35, 48), 49, 50]  # 48 is a multiple of 24


def test_replay_source_stays_inside_the_split():
    profile = _profile()
    split_start = datetime(2025, 2, 8, tzinfo=UTC)
    incident = _incident("k_replay", split_start + 27 * HOUR)
    assert valid_replay_lags(profile, incident, [incident], 168) == [25, 26, 27]


def test_replay_without_a_valid_lag_fails_and_names_the_incident():
    profile = _profile()
    split_start = datetime(2025, 2, 8, tzinfo=UTC)
    incident = _incident("k_replay", split_start + 24 * HOUR)
    with pytest.raises(ValueError, match="no valid replay lag for incident class k_replay at"):
        simulate_run(profile, 42, [incident])


def _full_run(seed: int = 42):
    profile = _profile()
    validate_profile(profile)
    incidents = generate_schedule(profile, seed)
    assert validate_schedule(profile, incidents) == []
    return profile, incidents, simulate(profile, seed), simulate_run(profile, seed, incidents)


def _inside(profile, incident) -> np.ndarray:
    return np.array([incident.start <= t < incident.end for t in timestamps(profile)])


def test_clean_twin_nothing_outside_an_incident_window_changes():
    profile, incidents, clean, injected = _full_run()
    outside = ~np.any([_inside(profile, i) for i in incidents], axis=0)
    _assert_unchanged(clean, injected, "abcd", outside)
    for incident in incidents:  # and every window of the schedule was injected
        inside = _inside(profile, incident)
        assert any(
            not np.array_equal(clean.reported[s][inside], injected.reported[s][inside])
            for s in "abcd"
        ), incident


def test_injected_samples_are_exactly_the_scheduled_window():
    profile = _profile({"x": {"primitive": "step_offset", "targets": ["d"], "magnitude": [2, 2]}})
    incidents = [_incident(), _incident(start=START + 72 * HOUR, hours=3)]
    clean, injected = simulate(profile, 42), simulate_run(profile, 42, incidents)
    changed = clean.reported["d"] != injected.reported["d"]
    assert np.array_equal(changed, np.any([_inside(profile, i) for i in incidents], axis=0))


@pytest.mark.parametrize("seed", [42, 43])
def test_the_schedule_does_not_depend_on_the_injection_blocks(seed):
    profile, stripped = _profile(), _profile()
    for incident_class in stripped["incident_classes"]:
        del incident_class["injection"]
    assert generate_schedule(profile, seed) == generate_schedule(stripped, seed)


def test_same_seed_is_identical_and_another_seed_draws_differently():
    _, incidents, _, first = _full_run()
    _, _, _, second = _full_run()
    for sensor_id in "abcd":
        assert np.array_equal(first.reported[sensor_id], second.reported[sensor_id])

    profile = _profile({"x": {"primitive": "step_offset", "targets": ["d"], "magnitude": [2, 6]}})
    deltas = []
    for seed in (42, 43):
        difference = simulate_run(profile, seed, [_incident()]).reported["d"]
        difference = difference - simulate(profile, seed).reported["d"]
        deltas.append(difference[difference != 0].mean())
    assert abs(deltas[0] - deltas[1]) > 1e-6


@pytest.mark.parametrize("class_id", list(BLOCKS))
def test_another_incident_does_not_change_this_incidents_draw(class_id):
    profile = _profile()
    mine = _incident(class_id)
    # Far later, so it cannot rule out any replay source of mine.
    other = _incident("k_step", START + 240 * HOUR)
    alone = simulate_run(profile, 42, [mine])
    together = simulate_run(profile, 42, [mine, other])
    inside = _inside(profile, mine)
    for sensor_id in "abcd":
        assert np.array_equal(alone.reported[sensor_id][inside],
                              together.reported[sensor_id][inside])


def test_magnitude_target_and_sign_are_drawn_per_incident_within_the_profile_limits():
    profile = _profile({"x": {"primitive": "step_offset", "targets": ["a", "d"],
                              "magnitude": [2, 6]}})
    incidents = [_incident(start=START + n * 20 * HOUR) for n in range(20)]
    clean, injected = simulate(profile, 42), simulate_run(profile, 42, incidents)
    sigma = sigma_s(profile, clean.reported)
    seen = set()
    for incident in incidents:
        inside = _inside(profile, incident)
        deltas = {s: (injected.reported[s] - clean.reported[s])[inside] for s in "ad"}
        (target,) = [s for s, d in deltas.items() if d.any()]
        magnitude = deltas[target][0] / sigma[target]
        assert 2 <= abs(magnitude) <= 6
        seen.add((target, np.sign(magnitude)))
    assert seen == {("a", -1), ("a", 1), ("d", -1), ("d", 1)}


def test_a_class_without_an_injection_block_injects_nothing():
    profile = _profile()
    incidents = generate_schedule(profile, 42)
    for incident_class in profile["incident_classes"]:
        del incident_class["injection"]
    _assert_unchanged(simulate(profile, 42), simulate_run(profile, 42, incidents), "abcd")


def test_injection_off_equals_the_clean_run():
    profile, incidents, clean, injected = _full_run()
    off = simulate_run(profile, 42, incidents, injection=False)
    _assert_unchanged(clean, off, "abcd")
    assert not np.array_equal(clean.reported["d"], injected.reported["d"])


@pytest.mark.parametrize(
    "path", sorted(Path("profiles").glob("*/profile.yaml")), ids=lambda p: p.parent.name
)
def test_injection_off_equals_the_output_before_injection_existed(path, monkeypatch):
    """Run the simulator of the last commit without injection next to today's, same machine."""
    try:
        shown = subprocess.run(
            ["git", "show", f"{BEFORE_INJECTION}:src/plantmon/sim/signals.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError:
        pytest.skip("git is not installed, so the earlier simulator cannot be read")
    if shown.returncode:
        pytest.skip(f"commit {BEFORE_INJECTION} is not in this clone")
    before = types.ModuleType("signals_before_injection")
    monkeypatch.setitem(sys.modules, before.__name__, before)  # dataclass looks it up
    exec(compile(shown.stdout, before.__name__, "exec"), before.__dict__)

    profile = load_profile(path)
    old = before.simulate(profile, 42)
    new = simulate_run(profile, 42, generate_schedule(profile, 42), injection=False)
    assert before.timestamps(profile) == timestamps(profile)
    _assert_unchanged(old, new, [s["id"] for s in profile["sensors"]])


def _block(**changes) -> dict:
    block = {"primitive": "step_offset", "targets": ["d"], "magnitude": [2, 6]}
    block.update(changes)
    return {key: value for key, value in block.items() if value is not None}


@pytest.mark.parametrize(
    ("block", "message"),
    [
        (_block(primitive="nope"), "unknown primitive"),
        ("step_offset", "must be a mapping"),
        (_block(targets=["zz"]), "unknown target sensor zz"),
        (_block(targets=None), "non-empty targets"),
        (_block(targets=[]), "non-empty targets"),
        (_block(primitive="scale_relation", targets=["d"]), "needs a target with follows"),
        (_block(primitive="command_override", targets=["b"]), "needs a target without follows"),
        (_block(magnitude=None), "magnitude must be"),
        (_block(magnitude=[6, 2]), "magnitude must be"),
        (_block(magnitude=[0, 2]), "magnitude must be"),
        (_block(magnitude=[2, float("inf")]), "magnitude must be"),
        (_block(magnitude=[float("nan"), 2]), "magnitude must be"),
        (_block(magnitude=[2]), "magnitude must be"),
        (_block(sign="up"), "sign must be one of"),
        (_block(sing="negative"), "unknown keys"),
        (_block(primitive="hold"), "unknown keys"),
        (_block(primitive="replay", magnitude=None), "max_lag_hours"),
        (_block(primitive="replay", magnitude=None, max_lag_hours=24), "max_lag_hours"),
        (_block(primitive="replay", magnitude=None, max_lag_hours=25.5), "max_lag_hours"),
    ],
)
def test_loader_rejects_a_bad_injection_block(block, message):
    profile = _profile({"x": {"primitive": "hold", "targets": ["d"]}})
    validate_profile(profile)
    profile["incident_classes"][0]["injection"] = block
    with pytest.raises(ValueError, match=message):
        validate_profile(profile)
