from pathlib import Path

import pytest

from plantmon.core.profile import load_profile, validate_profile
from plantmon.sim.schedule import generate_schedule, validate_schedule

PROFILE_PATHS = sorted(Path("profiles").glob("*/profile.yaml"))
SEEDS = [42, 43, 44, 45, 46]  # P5


def test_valid_profile_passes(profile):
    validate_profile(profile)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda p: p["profile"].update(simulated=False), "simulated"),
        (lambda p: p.pop("sensors"), "missing section sensors"),
        (lambda p: p["sensors"][0].update(asset="nope"), "unknown asset"),
        (lambda p: p["sensors"][0].update(kind="nope"), "unknown kind"),
        (lambda p: p["sensors"][0]["signal"].update(ar1=1.0), "ar1"),
        (lambda p: p["sensors"][0]["signal"]["state_offset"].update(gamma=1), "unknown states"),
        (lambda p: p["context"]["schedule"]["daily_hours"].update(beta=[11, 24]), "exactly once"),
        (lambda p: p["incident_classes"][0].update(type="nope"), "unknown type"),
        (lambda p: p["sampling"].update(interval_minutes=7), "divides a day"),
        (lambda p: p["run"].update(split_gap_days=7.5), "split_gap_days"),
        (lambda p: p["run"].update(split_gap_days=-1), "split_gap_days"),
        (lambda p: p["run"].update(split_gap_days=True), "split_gap_days"),
        (lambda p: p["run"].pop("split_gap_days"), "split_gap_days"),
        (lambda p: p["sensors"][0]["signal"].update(daily_phase_hours=float("nan")), "phase"),
        (lambda p: p["sensors"][0]["signal"].update(daily_phase_hours=float("inf")), "phase"),
        (lambda p: p["sensors"][0]["signal"].update(daily_phase_hours="8"), "phase"),
    ],
)
def test_invalid_profile_is_rejected(profile, change, message):
    change(profile)
    with pytest.raises(ValueError, match=message):
        validate_profile(profile)


@pytest.mark.parametrize("path", PROFILE_PATHS, ids=lambda p: p.parent.name)
@pytest.mark.parametrize("seed", SEEDS)
def test_every_repo_profile_has_a_valid_schedule(path, seed):
    loaded = load_profile(path)
    assert validate_schedule(loaded, generate_schedule(loaded, seed)) == []


@pytest.mark.parametrize("path", PROFILE_PATHS, ids=lambda p: p.parent.name)
def test_every_follows_source_exists(path):
    sensors = load_profile(path)["sensors"]
    ids = {s["id"] for s in sensors}
    assert all(s["follows"]["source"] in ids for s in sensors if "follows" in s)


@pytest.mark.parametrize("path", PROFILE_PATHS, ids=lambda p: p.parent.name)
def test_schedule_rules_meet_the_criteria_minimums(path):
    # Minimums from docs/evaluation-criteria-v1.md section 1, item 5; margin <= gap from section 2.
    loaded = load_profile(path)
    rules = loaded["incident_schedule"]
    assert rules["min_gap_hours"] >= 24
    assert rules["boundary_margin_hours"] >= 48
    assert rules["boundary_margin_hours"] <= loaded["run"]["split_gap_days"] * 24


def test_at_least_one_repo_profile_is_checked():
    assert PROFILE_PATHS


def test_at_least_one_repo_profile_uses_follows():
    assert any("follows" in s for path in PROFILE_PATHS for s in load_profile(path)["sensors"])
