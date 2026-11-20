# SPDX-License-Identifier: GPL-2.0-or-later
import math
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import json

from compare_relay import METRICS, schedule, summarize, timing_summary, validate
from run_load import TIMING_KEYS, admin_timing


class ComparisonTests(unittest.TestCase):
    def row(self):
        return {key: 1 for key in METRICS} | dict(
            team_size=5, teams=2, playing=10, scheduled_players=10,
            expected_game_paths=40, incoming_game_paths=40, fresh_game_paths=40,
            send_errors=0, refused=0,
            min_all_playing_seconds=10.01)

    def test_counterbalanced_pairs(self):
        self.assertEqual(list(schedule(2)), [
            (0, 2, "base"), (0, 2, "candidate"), (0, 5, "base"), (0, 5, "candidate"),
            (1, 2, "candidate"), (1, 2, "base"), (1, 5, "candidate"), (1, 5, "base")])

    def test_missing_route_and_mismatched_shape_fail(self):
        for bad in (dict(incoming_game_paths=39), dict(team_size=2), dict(send_errors=False)):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "party/route"):
                validate(self.row() | bad, 5, 10)

    def test_invalid_metrics_fail(self):
        for value in (math.nan, math.inf, True, -1, None):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "metric"):
                validate(self.row() | {"relay_ms_p99": value}, 5, 10)

    def test_median_paired_deltas_keep_party_sizes_separate(self):
        runs = [{"trial": trial, "team_size": size, "side": side,
                 "metrics": {key: 10 + (size + trial if side == "candidate" else 0)
                             for key in METRICS}} for trial, size, side in schedule(4)]
        self.assertEqual(summarize(runs, 4)["2"]["relay_ms_p99"], 3.5)
        self.assertEqual(summarize(runs, 4)["5"]["relay_ms_p99"], 6.5)

    @patch("run_load.subprocess.run")
    def test_only_known_timing_fields_returned(self, run):
        timing = dict.fromkeys(TIMING_KEYS, 1)
        run.return_value = SimpleNamespace(returncode=0, stdout=json.dumps(
            {"ok": True, "udp_timing": timing | {"ignored": 9}, "link_key": "ignored"}))
        self.assertEqual(admin_timing("shadnet", ".", {}), timing)
        self.assertEqual(run.call_args.args[0][-2:], ["--admin", "stats"])
        self.assertEqual(run.call_args.kwargs["timeout"], 8)

    @patch("run_load.subprocess.run")
    def test_malformed_timing_cannot_pass(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout='{"ok":true,"udp_timing":{}}')
        with self.assertRaisesRegex(RuntimeError, "valid UDP timing"):
            admin_timing("shadnet", ".", {})

    def test_paired_run_cannot_credit_startup_as_steady_play(self):
        validate(self.row(), 5, 10, 10)
        with self.assertRaisesRegex(ValueError, "requested steady"):
            validate(self.row(), 5, 10, 11)

    def test_timing_summary_compares_maxima_only(self):
        runs = [{"trial": trial, "team_size": size, "side": side,
                 "metrics": {"udp_timing": dict.fromkeys(
                     TIMING_KEYS, 10 + (size if side == "candidate" else 0))}}
                for trial, size, side in schedule(2)]
        self.assertEqual(timing_summary(runs, 2)["5"],
                         {"rx_slice_max_us": 5, "link_gap_max_ms": 5, "world_gap_max_ms": 5})

    @patch("run_load.subprocess.run")
    def test_zero_ticks_do_not_qualify_as_timing_evidence(self, run):
        timing = dict.fromkeys(TIMING_KEYS, 0)
        run.return_value = SimpleNamespace(returncode=0, stdout=json.dumps(
            {"ok": True, "udp_timing": timing}))
        with self.assertRaisesRegex(RuntimeError, "valid link and world ticks"):
            admin_timing("shadnet", ".", {})
