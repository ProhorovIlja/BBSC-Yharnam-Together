#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright 2026 shadNet Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""A shadNet load test (docs/HOSTED_SERVER.md): a fresh server in a temporary folder, simulated
players (bbload) against it, the server's CPU and memory sampled every second.

    run_load.py --shadnet build/shadnet --bbload build/bbload --players 120 --team-size 3

Splits the players over --processes bbload processes (one thread each), prints one JSON line
with the players' numbers (relay delay, losses, join times) and the server's (CPU, memory)."""
import argparse
from contextlib import ExitStack
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)


def cpu_ticks(pid):
    with open(f"/proc/{pid}/stat") as f:
        fields = f.read().rsplit(")", 1)[1].split()
    return int(fields[11]) + int(fields[12])  # utime + stime


def rss_mb(pid):
    with open(f"/proc/{pid}/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    return 0.0


def thread_ticks(pid):
    with open(f"/proc/{pid}/task/{pid}/stat") as f:
        fields = f.read().rsplit(")", 1)[1].split()
    return int(fields[11]) + int(fields[12])


def udp_rcvbuf_errors():
    with open("/proc/net/snmp") as f:
        lines = [line.split() for line in f if line.startswith("Udp:")]
    return int(lines[1][lines[0].index("RcvbufErrors")])


def threads(pid):
    return len(os.listdir(f"/proc/{pid}/task"))


def stop_child(child):
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
    if child.stdout is not None:
        child.stdout.close()


def worker_result(child, deadline):
    output, _ = child.communicate(timeout=max(0.01, deadline - time.monotonic()))
    if child.returncode:
        raise RuntimeError(f"bbload exited with status {child.returncode}")
    rows = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
    if len(rows) != 1 or not isinstance(rows[0], dict):
        raise RuntimeError("bbload did not return exactly one results object")
    return rows[0]


def validate_worker(row, teams, team_size, require_all_playing, seconds=0):
    expected = {"teams": teams, "team_size": team_size, "games": teams * team_size}
    if any(type(row.get(key)) is not int or row[key] != value
           for key, value in expected.items()):
        raise RuntimeError("bbload reported a different party shape than scheduled")
    counters = ("linked", "playing", "refused", "packets_sent", "packets_received",
                "exchanging_game_traffic", "incoming_game_paths", "send_errors")
    if any(type(row.get(key)) is not int or row[key] < 0 for key in counters):
        raise RuntimeError("bbload reported invalid or missing smoke counters")
    if not (0 <= row["playing"] <= row["linked"] <= row["games"]
            and row["exchanging_game_traffic"] <= row["games"]):
        raise RuntimeError("bbload reported inconsistent participation counts")
    steady = row.get("all_playing_seconds")
    if type(steady) not in (int, float) or not math.isfinite(steady) or steady < 0:
        raise RuntimeError("bbload reported an invalid steady window")
    if require_all_playing and steady < seconds:
        raise RuntimeError("incomplete loopback smoke: steady window was too short")
    expected_paths = row["games"] * (team_size - 1)
    if row["incoming_game_paths"] > expected_paths:
        raise RuntimeError("bbload reported too many directed game paths")
    if require_all_playing and (
            row["playing"] != row["games"] or row["refused"]
            or row["exchanging_game_traffic"] != row["games"]
            or row["incoming_game_paths"] != expected_paths or row["send_errors"]
            or not row["packets_sent"] or not row["packets_received"]):
        raise RuntimeError("incomplete loopback smoke: a worker did not reach play and exchange traffic")


BUILD_LOG_MARKER = "Link: games must run this server's build:"


def local_build_fingerprint(log_path, server, timeout=10):
    """Read the checked fingerprint from this run's fresh, private server log."""
    deadline = time.monotonic() + timeout
    with open(log_path, encoding="utf-8", errors="replace") as log:
        while True:
            for line in log:
                if BUILD_LOG_MARKER not in line:
                    continue
                value = line.partition(BUILD_LOG_MARKER)[2].strip()
                fields = {part.partition("=")[0] for part in value.split(";")[1:-1]}
                # Source-only container builds encode an empty revision when Git metadata is absent.
                if (len(value) > 255 or not re.fullmatch(
                        r"bb-build 1;(?:(?:revision=|[a-z]+=[A-Za-z0-9.+_-]+);)+", value)
                        or not {"version", "protocol"} <= fields):
                    raise RuntimeError("invalid checked build fingerprint in shadNet startup log")
                return value
            if server.poll() is not None:
                raise RuntimeError(f"shadNet exited during startup: {server.returncode}")
            if time.monotonic() >= deadline:
                raise RuntimeError("shadNet did not announce a checked build fingerprint")
            time.sleep(0.05)


def print_refusals(home):
    # Only surface bounded refusal lines from the synthetic clients, not server logs or keys.
    remaining = 8
    for name in sorted(os.listdir(home)):
        if not re.fullmatch(r"bbload[0-9]+\.log", name):
            continue
        with open(os.path.join(home, name), encoding="utf-8", errors="replace") as log:
            for line in log:
                if " refused:" in line:
                    msg = "".join(c if c.isprintable() else " " for c in line.strip()[:256])
                    print(f"{name}: {msg}", file=sys.stderr)
                    remaining -= 1
                    if not remaining:
                        return


TIMING_KEYS = (
    "rx_yields", "rx_slice_max_us", "link_ticks", "link_gap_max_ms",
    "link_gaps_over_2x", "world_ticks", "world_gap_max_ms", "world_gaps_over_2x",
)


def admin_timing(binary, home, env):
    result = subprocess.run([os.path.abspath(binary), "--admin", "stats"],
                            cwd=home, env=env, capture_output=True, text=True, timeout=8)
    if result.returncode:
        raise RuntimeError("local admin stats failed; enable Hosted mode for timing runs")
    row = json.loads(result.stdout)
    timing = row.get("udp_timing") if isinstance(row, dict) and row.get("ok") is True else None
    return validate_timing(timing)


def validate_timing(timing):
    if not isinstance(timing, dict) or any(type(timing.get(key)) is not int or timing[key] < 0
                                          for key in TIMING_KEYS):
        raise RuntimeError("local admin stats did not provide valid UDP timing")
    if (not timing["link_ticks"] or not timing["world_ticks"]
            or timing["link_gaps_over_2x"] > timing["link_ticks"]
            or timing["world_gaps_over_2x"] > timing["world_ticks"]):
        raise RuntimeError("local admin stats did not observe valid link and world ticks")
    # Never include the raw admin response in benchmark output.
    return {key: timing[key] for key in TIMING_KEYS}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadnet", required=True)
    parser.add_argument("--bbload", required=True)
    parser.add_argument("--players", type=int, default=60)
    parser.add_argument("--team-size", type=int, default=3)
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--ramp-ms", type=int, default=20)
    parser.add_argument("--processes", type=int, default=0, help="0: one per 150 players")
    parser.add_argument("--port", type=int, default=31314)
    parser.add_argument("--extra", default="", help="more bbload options")
    parser.add_argument("--match-local-build", action="store_true",
                        help="send the checked fingerprint announced by the fresh local server")
    parser.add_argument("--cfg", action="append", default=[], help="Key=Value for shadnet.cfg")
    parser.add_argument("--require-all-playing", action="store_true",
                        help="fail if any scheduled simulated player does not play")
    parser.add_argument("--collect-admin-timing", action="store_true",
                        help="require timing counters via the disposable server's local admin socket")
    parser.add_argument("--keep", action="store_true", help="keep the server's folder")
    parser.add_argument("--attack", default="", help="attack.py arguments, run beside the players")
    parser.add_argument("--attack-delay", type=float, default=20, help="seconds before it")
    args = parser.parse_args()

    if (args.team_size < 1 or args.players < args.team_size or args.seconds < 2
            or min(args.ramp_ms, args.processes, args.attack_delay) < 0
            or not 1025 <= args.port <= 65534):
        parser.error("invalid workload, duration, process count or test port")
    if args.team_size < 2 or args.players % args.team_size:
        parser.error("--players must be a multiple of --team-size (at least two per team)")
    try:
        args.extra = shlex.split(args.extra)
    except ValueError as error:
        parser.error(f"invalid --extra: {error}")
    reserved = {"--teams", "--team-size", "--seconds", "--ramp-ms", "--tag",
                "--json", "--port", "--server", "--shards", "--require-steady", "--"}
    if any(option.partition("=")[0] in reserved or option.startswith("-") and
           not option.startswith("--") and not option[1:].replace(".", "", 1).isdigit()
           for option in args.extra):
        parser.error("--extra cannot override workload, endpoint, or output options")
    if args.match_local_build and any(option.partition("=")[0] == "--build"
                                      for option in args.extra):
        parser.error("--match-local-build conflicts with an explicit --extra --build")
    home = tempfile.mkdtemp(prefix="shadnet-load-")
    try:
        with ExitStack() as cleanup:
            summary = run(args, home, cleanup)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"load test failed: {error}; diagnostic folder: {home}", file=sys.stderr)
        if args.match_local_build:
            try:
                print_refusals(home)
            except OSError:
                pass  # Diagnostic I/O must not hide the original failure.
        return 1
    print(json.dumps(summary))
    if args.keep:
        print("server folder:", home, file=sys.stderr)
    else:
        shutil.rmtree(home, ignore_errors=True)
    return 0


def run(args, home, cleanup):
    for name in ("worlds.cfg", "scoreboards.cfg"):
        shutil.copy(os.path.join(SERVER, name), home)
    cfg = {
        "Host": "127.0.0.1",
        "MatchingUdpPort": str(args.port),
        "UnsecuredPort": str(args.port - 1),
        "WebApiPort": str(args.port + 1),
        "StatsEnabled": "false",
        "BloodborneBackend": "false",
        "BloodborneSeamlessCoop": "true",
    }
    for item in args.cfg:
        key, value = item.split("=", 1)
        cfg[key] = value
    if args.collect_admin_timing:
        cfg["HostedAdminSocket"] = os.path.join(home, "benchmark.sock")
    with open(os.path.join(home, "shadnet.cfg"), "w") as f:
        f.write("[General]\n")
        for key, value in cfg.items():
            f.write(f"{key}={value}\n")

    env = dict(os.environ, SHADNET_HOME=home)
    log = cleanup.enter_context(open(os.path.join(home, "shadnet.log"), "w"))
    server = subprocess.Popen([os.path.abspath(args.shadnet)], cwd=home, env=env, stdout=log,
                              stderr=subprocess.STDOUT)
    cleanup.callback(stop_child, server)
    extra = list(args.extra)
    if args.match_local_build:
        build = local_build_fingerprint(os.path.join(home, "shadnet.log"), server)
        extra += ["--build", build]
    else:
        time.sleep(1.5)
    if server.poll() is not None:
        raise RuntimeError(f"shadNet exited during startup: {server.returncode}")

    samples = []
    stop = threading.Event()

    def sample():
        hz = os.sysconf("SC_CLK_TCK")
        last = cpu_ticks(server.pid)
        last_main = thread_ticks(server.pid)
        last_t = time.monotonic()
        while not stop.wait(1.0):
            try:
                now = cpu_ticks(server.pid)
                main_now = thread_ticks(server.pid)
            except FileNotFoundError:
                return
            t = time.monotonic()
            samples.append({"cpu": (now - last) / hz / (t - last_t) * 100.0,
                            "main": (main_now - last_main) / hz / (t - last_t) * 100.0,
                            "rss_mb": rss_mb(server.pid), "threads": threads(server.pid)})
            last, last_main, last_t = now, main_now, t

    drops_before = udp_rcvbuf_errors()
    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()

    def stop_sampler():
        stop.set()
        sampler.join(timeout=2)

    cleanup.callback(stop_sampler)
    teams = max(1, args.players // args.team_size)
    processes = args.processes or max(1, (teams * args.team_size + 149) // 150)
    per = [teams // processes + (1 if i < teams % processes else 0) for i in range(processes)]
    loads = []
    # bbload ramps per player, not per team; use the largest worker's schedule.
    ramp_seconds = max(per) * args.team_size * args.ramp_ms * processes / 1000
    deadline = time.monotonic() + args.seconds + ramp_seconds + 30
    for index, count in enumerate(per):
        if count == 0:
            continue
        command = [os.path.abspath(args.bbload), "--json", "--port", str(args.port), "--teams",
                   str(count), "--team-size", str(args.team_size), "--seconds",
                   str(args.seconds), "--ramp-ms", str(args.ramp_ms * processes), "--tag",
                   f"lt{index}"] + extra
        if args.require_all_playing:
            command.append("--require-steady")
        worker_log = cleanup.enter_context(open(os.path.join(home, f"bbload{index}.log"), "w"))
        load = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=worker_log, text=True)
        cleanup.callback(stop_child, load)
        loads.append((load, count))
    attack_result = {}
    if args.attack:
        time.sleep(min(args.attack_delay, max(0, deadline - time.monotonic())))
        attack = subprocess.run([sys.executable, os.path.join(HERE, "attack.py"), "--port",
                                 str(args.port)] + args.attack.split(), capture_output=True,
                                text=True, timeout=max(0.01, deadline - time.monotonic()))
        for line in attack.stdout.splitlines():
            if line.startswith("{"):
                attack_result = json.loads(line)
        if attack.returncode or not attack_result:
            raise RuntimeError("attack.py failed or did not produce a results row")
    results = []
    for load, count in loads:
        row = worker_result(load, deadline)
        validate_worker(row, count, args.team_size, args.require_all_playing, args.seconds)
        results.append(row)
    stop_sampler()
    if server.poll() is not None or not samples:
        raise RuntimeError("shadNet stopped early or no server resource samples were collected")
    if sum(row["games"] for row in results) != teams * args.team_size:
        raise RuntimeError("simulator results do not cover the scheduled players")
    udp_drops = udp_rcvbuf_errors() - drops_before
    timing = admin_timing(args.shadnet, home, env) if args.collect_admin_timing else None
    stop_child(server)

    # Approximation: last two thirds of CPU samples; not a timestamp-aligned window.
    steady = samples[len(samples) // 3:] or samples
    summary = {
        "players": sum(r["games"] for r in results),
        "teams": teams,
        "team_size": args.team_size,
        "min_all_playing_seconds": min(row["all_playing_seconds"] for row in results),
        "playing": sum(r["playing"] for r in results),
        "exchanging_game_traffic": sum(r["exchanging_game_traffic"] for r in results),
        "incoming_game_paths": sum(r["incoming_game_paths"] for r in results),
        "expected_game_paths": teams * args.team_size * (args.team_size - 1),
        "send_errors": sum(r["send_errors"] for r in results),
        "refused": sum(r["refused"] for r in results),
        "packets_sent": sum(r["packets_sent"] for r in results),
        "packets_received": sum(r["packets_received"] for r in results),
        # Legacy name: forward gaps, not a definitive count of dropped datagrams.
        "packets_lost": sum(r["packets_lost"] for r in results),
        "packets_late_or_duplicate": sum(r["packets_late_or_duplicate"] for r in results),
        "server_out_mbit": sum(r["bytes_received"] for r in results) * 8 / 1e6 /
        max(1, max(r["seconds"] for r in results)) if results else 0,
        "server_in_mbit": sum(r["bytes_sent"] for r in results) * 8 / 1e6 /
        max(1, max(r["seconds"] for r in results)) if results else 0,
        "relay_ms_p50": max((r["relay_ms_p50"] for r in results), default=0),
        # These are maxima of worker percentiles, not pooled percentiles.
        "relay_ms_p95": max((r["relay_ms_p95"] for r in results), default=0),
        "relay_ms_p99": max((r["relay_ms_p99"] for r in results), default=0),
        "relay_ms_max": max((r["relay_ms_max"] for r in results), default=0),
        "ping_ms_p99": max((r["ping_ms_p99"] for r in results), default=0),
        "welcome_ms_p50": max((r["welcome_ms_p50"] for r in results), default=0),
        "welcome_ms_p99": max((r["welcome_ms_p99"] for r in results), default=0),
        # Hosted: the new accounts' work (on each bbload's work threads).
        "accounts_worked": sum(r.get("accounts_worked", 0) for r in results),
        "work_ms_p50": max((r.get("work_ms_p50", 0) for r in results), default=0),
        "work_ms_p99": max((r.get("work_ms_p99", 0) for r in results), default=0),
        "solve_ms_p50": max((r.get("solve_ms_p50", 0) for r in results), default=0),
        "solve_ms_p99": max((r.get("solve_ms_p99", 0) for r in results), default=0),
        "work_bits_max": max((r.get("work_bits_max", 0) for r in results), default=0),
        "playing_ms_p50": max((r["playing_ms_p50"] for r in results), default=0),
        "playing_ms_p99": max((r["playing_ms_p99"] for r in results), default=0),
        "server_cpu_avg": round(sum(s["cpu"] for s in steady) / max(1, len(steady)), 1),
        "server_cpu_max": round(max((s["cpu"] for s in samples), default=0), 1),
        # The link's thread (the relay, the worlds, the lobby): at 100% it is the limit.
        "main_thread_cpu_avg": round(sum(s["main"] for s in steady) / max(1, len(steady)), 1),
        "main_thread_cpu_max": round(max((s["main"] for s in samples), default=0), 1),
        "udp_buffer_drops": udp_drops,  # the system's, every socket (server's and players')
        "load_avg": os.getloadavg()[0],
        "server_rss_mb_max": round(max((s["rss_mb"] for s in samples), default=0), 1),
        "server_threads": max((s["threads"] for s in samples), default=0),
    }
    if timing is not None:
        summary["udp_timing"] = timing
    if attack_result:
        summary["attack"] = attack_result
        with open(os.path.join(home, "shadnet.log")) as f:
            log_text = f.read()
        summary["accounts_made"] = log_text.count('made the account of player "bot')
    if summary["packets_sent"]:
        summary["delivered_pct"] = round(100.0 * summary["packets_received"] /
                                         summary["packets_sent"], 2)
    summary["requested_players"] = args.players
    summary["scheduled_players"] = teams * args.team_size
    summary["server_samples"] = len(samples)
    return summary


if __name__ == "__main__":
    raise SystemExit(main())
