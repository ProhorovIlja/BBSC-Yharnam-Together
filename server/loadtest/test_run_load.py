# SPDX-License-Identifier: GPL-2.0-or-later
import unittest

from run_load import validate_worker


class WorkerResultTests(unittest.TestCase):
    def row(self, **overrides):
        return dict(teams=2, team_size=5, games=10, linked=10, playing=10,
                    refused=0, packets_sent=100, packets_received=98) | overrides

    def test_exact_five_hunter_run(self):
        validate_worker(self.row(), 2, 5, True)

    def test_correct_game_total_does_not_hide_wrong_team_shape(self):
        with self.assertRaisesRegex(RuntimeError, "party shape"):
            validate_worker(self.row(teams=5, team_size=2), 2, 5, True)

    def test_healthy_worker_cannot_mask_another_with_no_traffic(self):
        validate_worker(self.row(), 2, 5, True)
        for field in ("packets_sent", "packets_received"):
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, "incomplete"):
                validate_worker(self.row(**{field: 0}), 2, 5, True)

    def test_incomplete_lobby_or_refusal_fails_smoke(self):
        for row in (self.row(playing=9), self.row(refused=1)):
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                validate_worker(row, 2, 5, True)
            validate_worker(row, 2, 5, False)

    def test_missing_and_malformed_counters(self):
        missing = self.row()
        del missing["playing"]
        for row in (missing, self.row(refused=False), self.row(packets_received=-1)):
            with self.assertRaisesRegex(RuntimeError, "counters"):
                validate_worker(row, 2, 5, True)

    def test_participation_cannot_exceed_linked_or_scheduled(self):
        for row in (self.row(linked=9), self.row(linked=11)):
            with self.assertRaisesRegex(RuntimeError, "participation"):
                validate_worker(row, 2, 5, True)
