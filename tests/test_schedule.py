from dataclasses import replace
from datetime import timedelta

import pytest

from plantmon.sim.schedule import (
    Incident,
    anomalous_share,
    generate_schedule,
    validate_schedule,
)
from plantmon.sim.signals import split_bounds


def test_generated_schedule_is_valid(profile):
    incidents = generate_schedule(profile, 42)
    assert validate_schedule(profile, incidents) == []
    assert len(incidents) == 2 * 2 * 2  # splits x classes x min_per_class


def test_every_incident_lies_inside_its_split_and_never_in_a_gap(profile):
    bounds = split_bounds(profile)
    for incident in generate_schedule(profile, 42):
        low, high = bounds[incident.split]
        assert low <= incident.start and incident.end <= high


def test_same_seed_is_identical_and_other_seed_differs(profile):
    assert generate_schedule(profile, 42) == generate_schedule(profile, 42)
    assert generate_schedule(profile, 42) != generate_schedule(profile, 43)


def test_incidents_lie_on_the_sampling_grid(profile):
    first = split_bounds(profile)["train"][0]
    for incident in generate_schedule(profile, 42):
        assert (incident.start - first) % timedelta(minutes=60) == timedelta()


def test_generator_refuses_a_schedule_that_cannot_fit(profile):
    profile["incident_schedule"]["min_gap_hours"] = 24 * 40
    with pytest.raises(ValueError, match="do not fit"):
        generate_schedule(profile, 42)


def test_rule_minimum_per_class(profile):
    incidents = generate_schedule(profile, 42)
    errors = validate_schedule(profile, incidents[1:])
    assert any("incidents of" in e for e in errors)


def test_rule_anomalous_share(profile):
    profile["incident_schedule"]["max_anomalous_share"] = 0.001
    errors = validate_schedule(profile, generate_schedule(profile, 42))
    assert any("anomalous share" in e for e in errors)


def test_rule_no_incident_in_training(profile):
    start = split_bounds(profile)["train"][0] + timedelta(days=5)
    extra = Incident("c1", "fault", "train", start, start + timedelta(hours=2))
    errors = validate_schedule(profile, [*generate_schedule(profile, 42), extra])
    assert any("incident in split train" in e for e in errors)


def test_rule_no_overlap(profile):
    incidents = generate_schedule(profile, 42)
    first = incidents[0]
    overlapping = replace(first, start=first.start + timedelta(hours=1))
    errors = validate_schedule(profile, [*incidents, overlapping])
    assert any("overlap" in e for e in errors)


def test_rule_minimum_gap(profile):
    incidents = generate_schedule(profile, 42)
    first = incidents[0]
    close = replace(
        first,
        start=first.end + timedelta(hours=1),
        end=first.end + timedelta(hours=2),
    )
    errors = validate_schedule(profile, [*incidents, close])
    assert any("gap too short" in e for e in errors)


def test_rule_boundary_margin(profile):
    incidents = generate_schedule(profile, 42)
    low = split_bounds(profile)["validation"][0]
    inside_margin = replace(incidents[0], start=low, end=low + timedelta(hours=2))
    errors = validate_schedule(profile, [*incidents[1:], inside_margin])
    assert any("boundary margin" in e for e in errors)


def test_rule_crossing_a_split_boundary(profile):
    incidents = generate_schedule(profile, 42)
    high = split_bounds(profile)["validation"][1]
    crossing = replace(
        incidents[0], start=high - timedelta(hours=1), end=high + timedelta(hours=1)
    )
    errors = validate_schedule(profile, [*incidents[1:], crossing])
    assert any("crossing" in e for e in errors)


def test_anomalous_share_is_time_over_split_length(profile):
    low, high = split_bounds(profile)["validation"]
    incident = Incident("c1", "fault", "validation", low, low + (high - low) / 4)
    assert anomalous_share(profile, [incident], "validation") == 0.25
