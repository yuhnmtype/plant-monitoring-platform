"""Command line: python -m plantmon demo --profile <id>. Run from the repo root."""

import argparse
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

from plantmon.core.chart import write_chart
from plantmon.core.profile import load_profile
from plantmon.core.store import apply_schema, connect, count_rows, read_series, replace_run
from plantmon.sim.schedule import anomalous_share, generate_schedule, validate_schedule
from plantmon.sim.signals import context_states, simulate, split_bounds, timestamps

CHART_PATH = Path("data/generated/chart.png")
CHART_DAYS = 14
PRIMARY_SEED = 42  # P5 in docs/evaluation-criteria-v1.md


def demo(profile_id: str, seed: int) -> int:
    started = time.perf_counter()
    subprocess.run(["docker", "compose", "up", "-d", "--wait", "db"], check=True)
    profile = load_profile(Path("profiles") / profile_id / "profile.yaml")

    incidents = generate_schedule(profile, seed)
    errors = validate_schedule(profile, incidents)
    if errors:
        print("Incident schedule is invalid:", *errors, sep="\n  ")
        return 1

    times = timestamps(profile)
    values = simulate(profile, seed).reported
    states = context_states(profile, times)
    with connect() as conn:
        apply_schema(conn)
        written = replace_run(conn, profile, seed, times, values, states, incidents)
        sensor = next(s for s in profile["sensors"] if s["kind"] == "measurement")
        chart_times, chart_values = read_series(
            conn, profile_id, sensor["id"], times[0] + timedelta(days=CHART_DAYS)
        )
        stored = {
            table: count_rows(conn, table, profile_id)
            for table in ("readings", "context_readings", "incident_labels")
        }
    write_chart(CHART_PATH, profile["profile"]["name"], sensor, chart_times, chart_values)

    print(f"All data is simulated. Profile {profile_id}, seed {seed}.")
    print(f"Samples per sensor: {len(times)}. Sensors: {len(values)}. Readings written: {written}.")
    print(f"Rows stored: {stored}")
    step = timedelta(minutes=profile["sampling"]["interval_minutes"])
    for split, (low, high) in split_bounds(profile).items():
        samples = sum(low <= t < high for t in times)
        days = samples * step / timedelta(days=1)
        chosen = [i for i in incidents if i.split == split]
        share = anomalous_share(profile, incidents, split)
        print(
            f"Split {split}: {days:g} days, {samples} samples per sensor,"
            f" {len(chosen)} incidents, anomalous share {share:.4f}"
        )
    print(f"Chart: {CHART_PATH}")
    print(f"Run time: {time.perf_counter() - started:.1f} s")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="plantmon")
    commands = parser.add_subparsers(dest="command", required=True)
    demo_parser = commands.add_parser("demo", help="simulate, store and chart one profile")
    demo_parser.add_argument("--profile", required=True, help="folder name under profiles/")
    demo_parser.add_argument("--seed", type=int, default=PRIMARY_SEED)
    args = parser.parse_args()
    return demo(args.profile, args.seed)


if __name__ == "__main__":
    sys.exit(main())
