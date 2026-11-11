"""Cross-sensor coupling on a tiny synthetic profile: c follows b, b follows a."""

import numpy as np
import pytest

from plantmon.core.profile import validate_profile
from plantmon.sim.signals import simulate

A_GAIN_B, A_OFFSET_B = 2.0, -3.0
B_GAIN_C, B_OFFSET_C = 0.5, 1.0


@pytest.fixture
def chain(profile) -> dict:
    common = {"asset": "a1", "kind": "measurement", "unit": "u", "nominal_range": [0, 100]}
    # Listed against generation order on purpose: c needs b, b needs a.
    profile["sensors"] = [
        {**common, "id": "c", "follows": {"source": "b", "gain": B_GAIN_C, "offset": B_OFFSET_C}},
        {**common, "id": "b", "follows": {"source": "a", "gain": A_GAIN_B, "offset": A_OFFSET_B}},
        {
            **common,
            "id": "a",
            "signal": {"base": 50, "daily_amplitude": 5, "noise_std": 1.0, "ar1": 0.5},
        },
    ]
    return profile


def _sensor(profile: dict, sensor_id: str) -> dict:
    return next(s for s in profile["sensors"] if s["id"] == sensor_id)


def test_chain_is_a_valid_profile(chain):
    validate_profile(chain)


def test_without_noise_follower_is_exact_and_reported_equals_physical(chain):
    result = simulate(chain, 42)
    assert np.array_equal(result.physical["b"], A_OFFSET_B + A_GAIN_B * result.physical["a"])
    assert np.array_equal(result.physical["c"], B_OFFSET_C + B_GAIN_C * result.physical["b"])
    for sensor_id in "abc":
        assert np.array_equal(result.reported[sensor_id], result.physical[sensor_id])


def test_noise_changes_reported_only(chain):
    clean = simulate(chain, 42)
    _sensor(chain, "a")["measurement_noise_std"] = 1.0
    noisy = simulate(chain, 42)

    assert not np.array_equal(noisy.reported["a"], noisy.physical["a"])
    # A follower reads its source's physical value, so noise on the source does not reach it.
    for sensor_id in "abc":
        assert np.array_equal(noisy.physical[sensor_id], clean.physical[sensor_id])
    assert np.array_equal(noisy.reported["b"], clean.reported["b"])


def test_same_seed_is_identical_and_other_seed_differs(chain):
    _sensor(chain, "b")["measurement_noise_std"] = 0.5
    first, second, other = simulate(chain, 42), simulate(chain, 42), simulate(chain, 43)
    for sensor_id in "abc":
        assert np.array_equal(first.physical[sensor_id], second.physical[sensor_id])
        assert np.array_equal(first.reported[sensor_id], second.reported[sensor_id])
        assert not np.array_equal(first.physical[sensor_id], other.physical[sensor_id])
        assert not np.array_equal(first.reported[sensor_id], other.reported[sensor_id])


def test_independent_sensor_does_not_change_when_a_follower_is_added(chain):
    with_followers = simulate(chain, 42).physical["a"]
    chain["sensors"] = [_sensor(chain, "a")]
    assert np.array_equal(with_followers, simulate(chain, 42).physical["a"])


def test_measurement_noise_uses_a_separate_stream(chain):
    before = simulate(chain, 42).physical["a"]
    _sensor(chain, "a")["measurement_noise_std"] = 1.0
    assert np.array_equal(before, simulate(chain, 42).physical["a"])


def test_follower_inherits_the_phase_of_its_source(chain):
    before = simulate(chain, 42).physical["b"]
    _sensor(chain, "a")["signal"]["daily_phase_hours"] = 6
    result = simulate(chain, 42)
    assert not np.array_equal(before, result.physical["b"])
    assert np.array_equal(result.physical["b"], A_OFFSET_B + A_GAIN_B * result.physical["a"])


def _make_a_follow_c(p: dict) -> None:
    a = _sensor(p, "a")
    del a["signal"]
    a["follows"] = {"source": "c", "gain": 1.0, "offset": 0.0}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (_make_a_follow_c, "follows cycle"),
        (lambda p: _sensor(p, "b")["follows"].update(source="b"), "follows itself"),
        (lambda p: _sensor(p, "b")["follows"].update(source="nope"), "unknown follows source"),
        (lambda p: _sensor(p, "b")["follows"].update(source="alpha"), "context channel"),
        (lambda p: _sensor(p, "b")["follows"].update(source="context"), "context channel"),
        (lambda p: _sensor(p, "b")["follows"].update(gain=float("inf")), "gain must be finite"),
        (lambda p: _sensor(p, "b")["follows"].update(offset=float("nan")), "offset must be finite"),
        (lambda p: _sensor(p, "b")["follows"].update(lag=4), "follows must have exactly"),
        (lambda p: _sensor(p, "b")["follows"].pop("gain"), "follows must have exactly"),
        (lambda p: _sensor(p, "b").update(signal={"base": 1}), "combined with a signal"),
        (lambda p: _sensor(p, "a").pop("signal"), "needs a signal or follows"),
        (lambda p: _sensor(p, "a").update(measurement_noise_std=-1), "measurement_noise_std"),
        (lambda p: _sensor(p, "a").update(measurement_noise_std=float("nan")), "measurement_noise"),
    ],
)
def test_bad_coupling_is_rejected(chain, change, message):
    change(chain)
    with pytest.raises(ValueError, match=message):
        validate_profile(chain)
