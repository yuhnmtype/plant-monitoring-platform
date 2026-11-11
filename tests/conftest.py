from datetime import date

import pytest


@pytest.fixture
def profile() -> dict:
    """A small neutral profile with an optional context channel."""
    return {
        "profile": {"id": "test_neutral", "name": "Neutral test profile", "simulated": True},
        "sampling": {"interval_minutes": 60},
        "run": {
            "start": date(2025, 1, 1),
            "split_gap_days": 7,
            "split_months": {"train": 1, "validation": 1, "test": 1},
        },
        "assets": [{"id": "a1", "name": "Asset one", "kind": "generic"}],
        "context": {
            "states": ["alpha", "beta"],
            "schedule": {"daily_hours": {"alpha": [0, 12], "beta": [12, 24]}},
        },
        "sensors": [
            {
                "id": "s1",
                "asset": "a1",
                "kind": "measurement",
                "unit": "u",
                "nominal_range": [0, 100],
                "signal": {
                    "base": 50,
                    "daily_amplitude": 5,
                    "noise_std": 1.0,
                    "ar1": 0.5,
                    "state_offset": {"alpha": 0, "beta": 20},
                },
            },
            {
                "id": "s2",
                "asset": "a1",
                "kind": "command",
                "unit": "u",
                "nominal_range": [0, 100],
                "signal": {"base": 10, "daily_amplitude": 1, "noise_std": 0.5, "ar1": 0.0},
            },
        ],
        "incident_schedule": {
            "min_per_class": 2,
            "max_anomalous_share": 0.10,
            "boundary_margin_hours": 24,
            "min_gap_hours": 12,
        },
        "incident_classes": [
            {"id": "c1", "type": "fault", "duration_hours": [2, 4]},
            {"id": "c2", "type": "attack", "duration_hours": [2, 4]},
        ],
    }
