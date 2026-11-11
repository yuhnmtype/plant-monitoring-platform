"""Draw one chart of a stored sensor series. The chart is always labelled as simulated."""

from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Writes a file only; a display backend would fail in CI and Docker.
from matplotlib import pyplot as plt  # noqa: E402


def write_chart(
    path: Path,
    profile_name: str,
    sensor: dict,
    times: list[datetime],
    values: list[float],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(times, values, linewidth=0.8, label=sensor["id"])
    low, high = sensor["nominal_range"]
    ax.axhspan(low, high, alpha=0.1, color="tab:green", label="nominal range")
    ax.set_title(f"SIMULATED DATA: {profile_name}, {sensor['id']}")
    ax.set_ylabel(sensor["unit"])
    ax.set_xlabel("simulated time (UTC)")
    ax.legend(loc="upper right")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
