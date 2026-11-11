import math
import zlib
from datetime import date, timedelta

import numpy as np
import pytest

from plantmon.sim.signals import (
    _ar1_noise,
    context_states,
    simulate,
    split_bounds,
    timestamps,
)


def test_same_seed_is_identical_and_other_seed_differs(profile):
    first = simulate(profile, 42).reported
    second = simulate(profile, 42).reported
    other = simulate(profile, 43).reported
    for sensor_id, series in first.items():
        assert np.array_equal(series, second[sensor_id])
        assert not np.array_equal(series, other[sensor_id])


def test_adding_a_sensor_does_not_change_the_others(profile):
    before = simulate(profile, 42).reported["s1"]
    profile["sensors"].append({**profile["sensors"][1], "id": "s3"})
    assert np.array_equal(before, simulate(profile, 42).reported["s1"])


def test_split_lengths_match_the_calendar(profile):
    # At one sample per hour: Jan 1 to Feb 1, then Feb 8 to Mar 8, then Mar 15 to Apr 15, 2025.
    times = timestamps(profile)
    counts = [sum(low <= t < high for t in times) for low, high in split_bounds(profile).values()]
    assert counts == [31 * 24, 28 * 24, 31 * 24]
    assert len(times) == sum(counts)


def test_each_later_split_starts_exactly_one_gap_after_the_previous_end(profile):
    bounds = list(split_bounds(profile).values())
    times = timestamps(profile)
    assert bounds[1][0] - bounds[0][1] == timedelta(days=7)
    assert bounds[2][0] - bounds[1][1] == timedelta(days=7)
    # The first sample after each gap sits on the new split's start.
    assert bounds[1][0] == min(t for t in times if t >= bounds[0][1])
    assert bounds[2][0] == min(t for t in times if t >= bounds[1][1])


def test_gap_samples_are_absent_from_every_output(profile):
    bounds = list(split_bounds(profile).values())
    gaps = [(bounds[0][1], bounds[1][0]), (bounds[1][1], bounds[2][0])]
    times = timestamps(profile)
    assert not [t for t in times for low, high in gaps if low <= t < high]

    result = simulate(profile, 42)
    states = context_states(profile, times)
    assert len(states) == len(times)
    for sensor_id in result.reported:
        assert len(result.physical[sensor_id]) == len(times)
        assert len(result.reported[sensor_id]) == len(times)


def test_process_runs_through_the_gap_then_the_gap_is_dropped(profile):
    spec = profile["sensors"][1]["signal"]
    spec["ar1"] = 0.9
    bounds = list(split_bounds(profile).values())
    n = int((bounds[2][1] - bounds[0][0]) / timedelta(hours=1))
    hours = np.arange(n, dtype=float)
    rng = np.random.default_rng([42, zlib.crc32(b"s2")])
    full = spec["base"] + spec["daily_amplitude"] * np.sin(2 * math.pi * hours / 24)
    full = full + _ar1_noise(rng, n, spec["noise_std"], spec["ar1"])

    all_times = [bounds[0][0] + timedelta(hours=h) for h in range(n)]
    kept = [any(low <= t < high for low, high in bounds) for t in all_times]
    assert np.array_equal(simulate(profile, 42).physical["s2"], full[kept])


def test_a_gap_of_zero_gives_contiguous_splits(profile):
    profile["run"]["split_gap_days"] = 0
    bounds = list(split_bounds(profile).values())
    assert bounds[0][1] == bounds[1][0]
    assert bounds[1][1] == bounds[2][0]


def test_a_split_start_on_day_29_is_refused(profile):
    profile["run"]["start"] = date(2025, 1, 22)
    profile["run"]["split_months"]["train"] = 2  # Ends Mar 22, so validation starts Mar 29.
    with pytest.raises(ValueError, match="starts on day 29"):
        split_bounds(profile)


def test_default_settings_equal_the_plain_recipe(profile):
    # Phase absent and no gap: base + daily sine + AR(1), drawn from [seed, crc32(id)].
    profile["run"]["split_gap_days"] = 0
    spec = profile["sensors"][1]["signal"]
    n = len(timestamps(profile))
    hours = np.arange(n, dtype=float)
    rng = np.random.default_rng([42, zlib.crc32(b"s2")])
    expected = spec["base"] + spec["daily_amplitude"] * np.sin(2 * math.pi * hours / 24)
    expected = expected + _ar1_noise(rng, n, spec["noise_std"], spec["ar1"])
    assert np.array_equal(simulate(profile, 42).physical["s2"], expected)


def test_phase_zero_equals_no_phase(profile):
    before = simulate(profile, 42).physical["s2"]
    profile["sensors"][1]["signal"]["daily_phase_hours"] = 0
    assert np.array_equal(before, simulate(profile, 42).physical["s2"])


def test_phase_shifts_the_daily_cycle_by_the_given_hours(profile):
    spec = profile["sensors"][1]["signal"]
    spec["noise_std"] = 0.0
    start = simulate(profile, 42).physical["s2"]
    spec["daily_phase_hours"] = 6
    shifted = simulate(profile, 42).physical["s2"]
    # Hourly samples: the delayed cycle equals the original six samples earlier.
    assert np.allclose(shifted[6:24 * 31], start[:24 * 31 - 6])
    assert not np.allclose(shifted, start)


def test_context_is_optional(profile):
    times = timestamps(profile)
    states = context_states(profile, times)
    assert states[0] == "alpha" and states[12] == "beta"

    del profile["context"]
    del profile["sensors"][0]["signal"]["state_offset"]
    assert context_states(profile, times) is None
    assert len(simulate(profile, 42).reported["s1"]) == len(times)


def test_states_inside_simulate_equal_those_of_the_kept_timestamps_across_a_gap(profile):
    # With no base, cycle or noise, the signal is only the offset of the state simulate() used.
    profile["sensors"][0]["signal"].update(base=0.0, daily_amplitude=0.0, noise_std=0.0)
    times = timestamps(profile)
    assert max(b - a for a, b in zip(times, times[1:])) > timedelta(days=7)
    expected = [20.0 if state == "beta" else 0.0 for state in context_states(profile, times)]
    assert simulate(profile, 42).physical["s1"].tolist() == expected


def test_state_offset_shifts_the_signal(profile):
    times = timestamps(profile)
    states = np.array(context_states(profile, times))
    with_offset = simulate(profile, 42).reported["s1"]
    del profile["context"]
    del profile["sensors"][0]["signal"]["state_offset"]
    without = simulate(profile, 42).reported["s1"]

    assert np.allclose((with_offset - without)[states == "beta"], 20)
    assert np.allclose((with_offset - without)[states == "alpha"], 0)
