#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Alternate two shadNet builds against the same local synthetic workload."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys

METRICS = ("server_cpu_avg", "main_thread_cpu_avg", "server_rss_mb_max",
           "relay_ms_p99", "ping_ms_p99", "packets_lost", "udp_buffer_drops")
RUNNER = Path(__file__).with_name("run_load.py")


def validate(row):
    if row["playing"] != row["scheduled_players"] or row["refused"] != 0:
        raise ValueError("not all scheduled players reached play")
    if not row["packets_sent"] or not row["packets_received"] or not row["server_samples"]:
        raise ValueError("missing traffic or server resource samples")
    if any(not math.isfinite(row[key]) or row[key] < 0 for key in METRICS):
        raise ValueError("invalid resource or latency sample")
    return row


def summarize(samples):
    if not samples or len(samples) % 2:
        raise ValueError("comparison requires complete A/B pairs")
    pairs = []
    for i in range(0, len(samples), 2):
        pair = dict(samples[i:i+2])
        if set(pair) != {"baseline", "candidate"}:
            raise ValueError("comparison requires one result per build in each pair")
        base, candidate = (validate(pair[k]) for k in ("baseline", "candidate"))
        if base["scheduled_players"] != candidate["scheduled_players"]:
            raise ValueError("builds did not run the same workload")
        pairs.append((base, candidate))
    return {key: {
        "baseline_median": statistics.median(a[key] for a, _ in pairs),
        "candidate_median": statistics.median(b[key] for _, b in pairs),
        "paired_delta_median": statistics.median(b[key] - a[key] for a, b in pairs),
    } for key in METRICS}


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "candidate", "bbload", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name, default in (("players", 60), ("team-size", 3), ("seconds", 30),
                          ("pairs", 3), ("port", 31314)):
        parser.add_argument("--" + name, type=int, default=default)
    args = parser.parse_args()
    if not (1 <= args.pairs <= 10 and 2 <= args.seconds <= 600 and
            1 <= args.team_size <= args.players <= 1000 and args.players % args.team_size == 0):
        parser.error("use complete teams, 1–10 pairs, and 2–600 seconds")
    args.output.mkdir()
    builds = {"baseline": args.baseline, "candidate": args.candidate, "bbload": args.bbload}
    identity = {key: digest(path) for key, path in builds.items()}
    samples = []
    try:
        for number in range(args.pairs):
            order = ("baseline", "candidate") if number % 2 == 0 else ("candidate", "baseline")
            for label in order:
                stem = args.output / f"{number + 1:02d}-{label}"
                command = [sys.executable, str(RUNNER), "--shadnet", str(builds[label].resolve()),
                           "--bbload", str(args.bbload.resolve()), "--players", str(args.players),
                           "--team-size", str(args.team_size), "--seconds", str(args.seconds),
                           "--port", str(args.port)]
                # run_load owns the child-process deadlines and cleanup; do not kill its parent
                # out from underneath it with an outer subprocess timeout.
                result = subprocess.run(command, capture_output=True, text=True)
                stem.with_suffix(".stdout").write_text(result.stdout, encoding="utf-8")
                stem.with_suffix(".stderr").write_text(result.stderr, encoding="utf-8")
                if result.returncode:
                    raise RuntimeError(f"{label} failed; see {stem.with_suffix('.stderr')}")
                samples.append((label, validate(json.loads(result.stdout))))
        if any(digest(path) != identity[key] for key, path in builds.items()):
            raise ValueError("a binary changed during the comparison")
        report = {"scope": "synthetic loopback shadNet; not game FPS or WAN latency",
                  "sha256": identity, "players": args.players, "team_size": args.team_size,
                  "seconds_per_run": args.seconds, "pairs": args.pairs,
                  "metrics": summarize(samples)}
        (args.output / "comparison.json").write_text(json.dumps(report, indent=2) + "\n",
                                                      encoding="utf-8")
    except (KeyError, ValueError, OSError, RuntimeError) as error:
        print(f"comparison incomplete: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
