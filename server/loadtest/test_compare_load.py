# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from compare_load import METRICS, summarize, validate


def row(value=2, **changes):
    return dict({key: value for key in METRICS}, scheduled_players=3, playing=3,
                refused=0, packets_sent=100, packets_received=100, server_samples=5) | changes


class CompareTests(unittest.TestCase):
    def test_alternating_order_and_paired_delta(self):
        runs = [("baseline", row(8)), ("candidate", row(6)),
                ("candidate", row(11)), ("baseline", row(12))]
        self.assertEqual(summarize(runs)["relay_ms_p99"],
                         {"baseline_median": 10, "candidate_median": 8.5,
                          "paired_delta_median": -1.5})

    def test_failed_or_empty_run_is_not_a_gain(self):
        for item in (row(playing=2), row(refused=1), row(server_samples=0),
                     row(packets_received=0), row(value=float("nan"))):
            with self.assertRaises(ValueError):
                validate(item)

    def test_reject_incomplete_or_mismatched_pair(self):
        for runs in ([("baseline", row())],
                     [("baseline", row()), ("baseline", row())],
                     [("baseline", row()), ("candidate", row(playing=6, scheduled_players=6))]):
            with self.assertRaises(ValueError):
                summarize(runs)
