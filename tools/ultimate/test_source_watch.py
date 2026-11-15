import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import source_watch as watch

A, B = 'a' * 40, 'b' * 40


class SourceWatchTests(unittest.TestCase):
    def test_heads_and_prs_keep_exact_identities(self):
        refs = watch.parse_refs(f'{A}\trefs/heads/main\n{B}\trefs/pull/42/head\n')
        self.assertEqual(refs, {'refs/heads/main': A, 'refs/pull/42/head': B})

    def test_malformed_or_conflicting_output_is_not_coverage(self):
        for text in ('', 'bad', f'{A}\tHEAD\n', f'{A}\trefs/heads/main\n{B}\trefs/heads/main\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                watch.parse_refs(text)

    def test_repository_cannot_inject_git_options_or_credentials(self):
        runner = Mock()
        for repo in ('--upload-pack=evil', 'https://github.com/user/repo', 'user/repo/extra',
                     'user@secret/repo', 'user/repo\nother'):
            with self.subTest(repo=repo), self.assertRaises(ValueError):
                watch.discover(repo, runner=runner)
        runner.assert_not_called()

    def test_timeout_cannot_report_every_branch_removed(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired('git', 40))
        row = watch.discover('owner/repo', runner=runner)
        self.assertEqual(row['status'], 'failed')
        self.assertIsNone(row['refs'])
        self.assertEqual(watch.changes(row, {'refs': {'refs/heads/main': A}}),
                         {'status': 'unknown_due_to_failed_scan'})

    def test_delta_records_added_removed_changed(self):
        old = {'status': 'inventoried_not_reviewed', 'refs': {'main': A, 'gone': A}}
        new = {'status': 'inventoried_not_reviewed', 'refs': {'main': B, 'new': A}}
        self.assertEqual(watch.changes(new, old), {'status': 'compared', 'added': ['new'],
                                                 'removed': ['gone'], 'changed': ['main']})

    def test_failed_baseline_needs_initial_inventory(self):
        self.assertEqual(watch.changes({'status': 'inventoried_not_reviewed', 'refs': {}},
                                       {'status': 'failed', 'refs': None}),
                         {'status': 'initial_inventory'})

    def test_consecutive_failed_scans_preserve_delta_baseline_without_claiming_coverage(self):
        good = {'status': 'inventoried_not_reviewed', 'refs': {'refs/heads/main': A}}
        first = {'status': 'failed', 'refs': None}
        second = {'status': 'failed', 'refs': None}
        watch.carry_scan_history(first, good)
        watch.carry_scan_history(second, first)
        self.assertIsNone(second['refs'])
        self.assertEqual(second['delta']['status'], 'unknown_due_to_failed_scan')
        self.assertEqual(second['last_successful_refs'], good['refs'])
        recovered = {'status': 'inventoried_not_reviewed', 'refs': {'refs/heads/main': B}}
        watch.carry_scan_history(recovered, second)
        self.assertEqual(recovered['delta']['changed'], ['refs/heads/main'])

    def test_failed_publication_keeps_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshot.json'
            watch.write_atomic(path, {'old': True})
            with patch.object(watch.os, 'replace', side_effect=OSError('test disk failure')):
                with self.assertRaises(OSError):
                    watch.write_atomic(path, {'new': True})
            self.assertEqual(json.loads(path.read_text()), {'old': True})
            self.assertEqual(list(path.parent.iterdir()), [path])


if __name__ == '__main__':
    unittest.main()
