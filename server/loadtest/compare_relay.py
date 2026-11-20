#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Run the same strict loopback workload on two explicitly supplied ShadNet binaries."""
import argparse
import hashlib
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path

from run_load import validate_timing

RUNNER = Path(__file__).with_name("run_load.py")
METRICS = ("steady_relay_ms_p50", "steady_relay_ms_p95", "steady_relay_ms_p99", "server_cpu_avg",
           "main_thread_cpu_avg", "server_out_mbit", "delivered_pct", "udp_buffer_drops")


def schedule(repeats):
    for trial in range(repeats):
        for size in (2, 5):
            for side in (("base", "candidate") if trial % 2 == 0 else ("candidate", "base")):
                yield trial, size, side


def fingerprint(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def validate(summary, size, players, seconds=0):
    if not isinstance(summary, dict):
        raise ValueError("benchmark did not produce a JSON object")
    expected = {"team_size": size, "teams": players // size, "playing": players,
                "scheduled_players": players, "expected_game_paths": players * (size - 1),
                "incoming_game_paths": players * (size - 1), "fresh_game_paths": players * (size - 1),
                "send_errors": 0, "refused": 0}
    if any(type(summary.get(key)) is not int or summary[key] != value
           for key, value in expected.items()):
        raise ValueError("benchmark result did not match the strict party/route workload")
    for key in (*METRICS, "min_all_playing_seconds"):
        value = summary.get(key)
        if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
            raise ValueError(f"invalid benchmark metric: {key}")
    if type(summary.get("steady_relay_samples")) is not int or summary["steady_relay_samples"] <= 0:
        raise ValueError("benchmark has no steady relay samples")
    if summary["min_all_playing_seconds"] < seconds:
        raise ValueError("benchmark did not complete the requested steady window")
    return summary


def timing_summary(runs, repeats):
    by_key = {(r["trial"], r["team_size"], r["side"]): r["metrics"]["udp_timing"] for r in runs}
    keys = ("rx_slice_max_us", "link_gap_max_ms", "world_gap_max_ms")
    return {str(size): {
        key: statistics.median(by_key[trial, size, "candidate"][key] -
                               by_key[trial, size, "base"][key] for trial in range(repeats))
        for key in keys
    } for size in (2, 5)}


def paired_deltas(runs, repeats):
    by_key = {(r["trial"], r["team_size"], r["side"]): r["metrics"] for r in runs}
    return {str(size): {
        key: [by_key[trial, size, "candidate"][key] - by_key[trial, size, "base"][key]
              for trial in range(repeats)]
        for key in METRICS
    } for size in (2, 5)}


def summarize(runs, repeats):
    return {size: {key: statistics.median(values) for key, values in metrics.items()}
            for size, metrics in paired_deltas(runs, repeats).items()}


def journal_record(path, record):
    if path is None:
        return
    with path.open("a", encoding="utf-8") as log:
        log.write(json.dumps(record, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("base", "candidate", "bbload"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--journal", type=Path, help="new JSONL file for partial trial evidence")
    parser.add_argument("--trials", type=int, default=4)
    parser.add_argument("--teams", type=int, default=2)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--port", type=int, default=32040)
    parser.add_argument("--hosted-timing", action="store_true",
                        help="require private UDP/tick metrics from two instrumented builds")
    args = parser.parse_args()
    if not (2 <= args.trials <= 20 and 1 <= args.teams <= 30 and
            10 <= args.seconds <= 300 and 1025 <= args.port <= 65534):
        parser.error("use 2–20 trials, 1–30 teams, 10–300 seconds and a nonprivileged test port")
    binaries = {key: getattr(args, key).resolve() for key in ("base", "candidate", "bbload")}
    try:
        hashes = {key: fingerprint(path) for key, path in binaries.items()}
        if hashes["base"] == hashes["candidate"]:
            raise ValueError("baseline and candidate binaries are identical")
        if args.journal is not None:
            args.journal.touch(exist_ok=False)
            journal_record(args.journal, {"event": "start", "sha256": hashes,
                           "teams": args.teams, "seconds": args.seconds, "trials": args.trials})
        runs = []
        for trial, size, side in schedule(args.trials):
            players = size * args.teams
            command = [sys.executable, str(RUNNER), "--shadnet", str(binaries[side]),
                       "--bbload", str(binaries["bbload"]), "--players", str(players),
                       "--team-size", str(size), "--seconds", str(args.seconds),
                       "--port", str(args.port), "--require-all-playing", "--match-local-build"]
            if args.hosted_timing:
                command += ["--collect-admin-timing", "--cfg", "Hosted=true", "--cfg", "SignIn=open",
                            "--cfg", "HostedSignupWorkBits=0", "--cfg", "HostedSignupWorkMaxBits=0"]
            trial_id = {"trial": trial, "side": side, "team_size": size}
            journal_record(args.journal, {"event": "trial_start", **trial_id})
            proc = subprocess.run(command, stdout=subprocess.PIPE, text=True)
            if proc.returncode:
                journal_record(args.journal, {"event": "trial_exit", **trial_id,
                                               "exit_code": proc.returncode})
                raise ValueError(f"{side} trial {trial + 1}, size {size}: workload failed")
            row = validate(json.loads(proc.stdout), size, players, args.seconds)
            if args.hosted_timing:
                row["udp_timing"] = validate_timing(row.get("udp_timing"))
            result = {**trial_id, "metrics": row}
            journal_record(args.journal, {"event": "trial_complete", **result})
            runs.append(result)
        if any(fingerprint(path) != hashes[key] for key, path in binaries.items()):
            raise ValueError("a benchmark binary changed during the comparison")
        report = {"sha256": hashes, "trials": args.trials, "teams": args.teams,
                  "seconds": args.seconds, "hosted_timing": args.hosted_timing, "runs": runs,
                  "candidate_minus_base_median": summarize(runs, args.trials),
                  "candidate_minus_base_trials": paired_deltas(runs, args.trials)}
        if args.hosted_timing:
            report["timing_candidate_minus_base_median"] = timing_summary(runs, args.trials)
        output = json.dumps(report, allow_nan=False)
        journal_record(args.journal, {"event": "comparison_complete"})
        print(output)
    except (OSError, ValueError, RuntimeError, OverflowError) as error:
        print(f"comparison failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
