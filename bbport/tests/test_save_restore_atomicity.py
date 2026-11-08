# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic save restoration failures; no real user save folders or game data."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))
import bbport_coop as coop  # noqa: E402


class SaveRestoreSafetyTests(unittest.TestCase):
    SLOT = 'savedata/1/CUSA03173/SPRJ0005/userdata0000'
    HOME_SLOT = 'home/1000/savedata/CUSA03173/SPRJ0005/userdata0001'
    PARTY = 'bloodborne_party_world_slot0.txt'
    BACKUP = '20261024-231630'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='bbsc-save-restore-synthetic-')
        self.addCleanup(self.tmp.cleanup)
        self.install = Path(self.tmp.name)
        self.user = self.install / 'user'
        self.write(self.SLOT, b'current-character')
        self.write(self.HOME_SLOT, b'current-home-save')
        self.write(self.PARTY, b'current-party')
        self.write('log/shad_log.txt', b'keep the log')
        self.write(self.SLOT, b'older-character', under=self.user / coop.SAVE_BACKUPS / self.BACKUP)
        self.write(self.PARTY, b'older-party', under=self.user / coop.SAVE_BACKUPS / self.BACKUP)
        self.before = coop.save_files(self.user)

    def write(self, rel, data, under=None):
        path = (under or self.user) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def stage_paths(self):
        return list(self.user.glob('.bbsc-restore-stage-*'))

    def test_successful_restore_preserves_non_save_files_and_undo_snapshot(self):
        safety = coop.restore_saves(self.install, self.BACKUP)
        self.assertIsNotNone(safety)
        self.assertEqual(coop.save_files(safety), self.before)
        self.assertEqual((self.user / self.SLOT).read_bytes(), b'older-character')
        self.assertFalse((self.user / self.HOME_SLOT).exists())
        self.assertEqual((self.user / self.PARTY).read_bytes(), b'older-party')
        self.assertEqual((self.user / 'log/shad_log.txt').read_bytes(), b'keep the log')
        self.assertEqual(self.stage_paths(), [])
        coop.restore_saves(self.install, safety.name)
        self.assertEqual(coop.save_files(self.user), self.before, 'restore must remain undoable')

    def test_staging_io_failure_never_removes_current_save_or_creates_safety_backup(self):
        real = Path.write_bytes
        def fail_stage(path, data):
            if any(part.startswith('.bbsc-restore-stage-') for part in path.parts):
                raise OSError('synthetic out of disk space during preflight')
            return real(path, data)
        with mock.patch.object(Path, 'write_bytes', fail_stage):
            with self.assertRaisesRegex(OSError, 'synthetic out of disk'):
                coop.restore_saves(self.install, self.BACKUP)
        self.assertEqual(coop.save_files(self.user), self.before)
        self.assertEqual([b['name'] for b in coop.save_backups(self.install)], [self.BACKUP])
        self.assertEqual(self.stage_paths(), [])

    def test_first_commit_write_failure_rolls_back_full_character_and_party_set(self):
        real = Path.write_bytes
        hit = []
        target = self.user / self.SLOT
        def fail_once(path, data):
            if path == target and not hit:
                hit.append(True)
                raise OSError('synthetic write interruption')
            return real(path, data)
        with mock.patch.object(Path, 'write_bytes', fail_once):
            with self.assertRaisesRegex(OSError, 'previous saves were restored'):
                coop.restore_saves(self.install, self.BACKUP)
        self.assertEqual(len(hit), 1)
        self.assertEqual(coop.save_files(self.user), self.before)
        self.assertEqual((self.user / 'log/shad_log.txt').read_bytes(), b'keep the log')
        self.assertEqual(self.stage_paths(), [])
        candidates = [b for b in coop.save_backups(self.install) if b['launcher']]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(coop.save_files(candidates[0]['path']), self.before)

    def test_unrecoverable_write_failure_keeps_safety_snapshot_and_reports_it(self):
        real = Path.write_bytes
        target = self.user / self.SLOT
        def fail_both(path, data):
            if path == target:
                raise OSError('synthetic persistent disk error')
            return real(path, data)
        with mock.patch.object(Path, 'write_bytes', fail_both):
            with self.assertRaisesRegex(OSError, 'automatic rollback failed'):
                coop.restore_saves(self.install, self.BACKUP)
        copies = [b for b in coop.save_backups(self.install) if b['launcher']]
        self.assertEqual(len(copies), 1)
        self.assertEqual(coop.save_files(copies[0]['path']), self.before)
        self.assertEqual(self.stage_paths(), [])

    def test_invalid_backup_never_wipes_live_progress(self):
        for name in ('', '..', '20991231-010203'):
            with self.assertRaises(ValueError):
                coop.restore_saves(self.install, name)
        self.assertEqual(coop.save_files(self.user), self.before)


if __name__ == '__main__':
    unittest.main()
