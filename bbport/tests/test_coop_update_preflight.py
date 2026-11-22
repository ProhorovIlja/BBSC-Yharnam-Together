# SPDX-License-Identifier: GPL-2.0-or-later
"""The co-op installer must not touch live services without a complete save copy.

Run on demand:
    python -m unittest discover -s bbport/tests -p test_coop_update_preflight.py -v
No Windows desktop or real player save is needed for these synthetic cases.
"""
import ast
import http.client
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))
import bbport_coop as coop  # noqa: E402


class SafeCoopUpdateTests(unittest.TestCase):
    def test_download_then_verified_backup_then_stop_in_that_order(self):
        seen = []
        def downloaded(_release, _folder, _progress):
            seen.append('download')
            return Path('synthetic-setup.exe')
        def backed_up(_install, _reason, prune=True):
            self.assertFalse(prune, 'do not prune old backups during an update')
            seen.append('backup')
        def stopped(_install):
            seen.append('stop')
        with mock.patch.object(coop, 'download_update', side_effect=downloaded), \
                mock.patch.object(coop, 'back_up_saves', side_effect=backed_up), \
                mock.patch.object(coop, 'stop_servers', side_effect=stopped):
            setup = coop.prepare_coop_update({'version': 'fixture'}, Path('updates'), Path('install'))
        self.assertEqual(setup, Path('synthetic-setup.exe'))
        self.assertEqual(seen, ['download', 'backup', 'stop'])

    def test_failed_backup_leaves_services_untouched(self):
        with mock.patch.object(coop, 'download_update', return_value=Path('setup.exe')), \
                mock.patch.object(coop, 'back_up_saves', side_effect=OSError('disk full')), \
                mock.patch.object(coop, 'stop_servers') as stop:
            with self.assertRaisesRegex(OSError, 'disk full'):
                coop.prepare_coop_update({}, Path('download'), Path('install'))
        stop.assert_not_called()

    def test_incomplete_http_update_does_not_stop_services_or_back_up(self):
        with mock.patch.object(coop, 'download_update',
                               side_effect=http.client.IncompleteRead(b'half', 4)), \
                mock.patch.object(coop, 'back_up_saves') as backup, \
                mock.patch.object(coop, 'stop_servers') as stop:
            with self.assertRaises(http.client.IncompleteRead):
                coop.prepare_coop_update({}, Path('download'), Path('install'))
        backup.assert_not_called()
        stop.assert_not_called()

    def test_no_saves_still_allows_safe_update(self):
        with mock.patch.object(coop, 'download_update', return_value=Path('setup.exe')), \
                mock.patch.object(coop, 'back_up_saves', return_value=None), \
                mock.patch.object(coop, 'stop_servers') as stop:
            self.assertEqual(coop.prepare_coop_update({}, Path('download'), Path('install')),
                             Path('setup.exe'))
        stop.assert_called_once()

    def test_backup_is_byte_verified_and_a_corrupt_copy_is_discarded(self):
        with tempfile.TemporaryDirectory() as scratch:
            install = Path(scratch)
            relative = Path('savedata/1/CUSA03173/SPRJ0005/userdata0000')
            original = install / 'user' / relative
            original.parent.mkdir(parents=True)
            original.write_bytes(b'synthetic-save-bytes-original')
            actual_write = Path.write_bytes

            def corrupt_backup(path, data):
                if 'save-backups' in Path(path).parts:
                    return actual_write(path, b'corrupted')
                return actual_write(path, data)

            with mock.patch.object(Path, 'write_bytes', corrupt_backup):
                with self.assertRaisesRegex(OSError, 'could not be verified'):
                    coop.back_up_saves(install, 'before an update', now=1792900000, prune=False)
            self.assertEqual(original.read_bytes(), b'synthetic-save-bytes-original')
            self.assertEqual(list((install / 'user' / 'save-backups').iterdir()), [])
            backup = coop.back_up_saves(install, 'before an update', now=1792900000, prune=False)
            self.assertIsNotNone(backup)
            self.assertEqual(coop.save_files(backup), coop.save_files(install / 'user'))
            self.assertIsNone(coop.back_up_saves(install, 'before an update',
                                                now=1792900000, prune=False),
                              'byte-identical existing backup is already safe')

    def test_windows_frontend_calls_preflight_and_catches_http_errors(self):
        source = (Path(__file__).resolve().parents[1] / 'launcher' /
                  'bbport_launcher_win.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        coop_install = next(node for node in ast.walk(tree)
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and
                            node.name == 'coop_install_update')
        callbacks = [node for node in ast.walk(coop_install)
                     if isinstance(node, ast.Call) and
                     isinstance(node.func, ast.Attribute)]
        self.assertTrue(any(node.func.attr == 'prepare_coop_update' for node in callbacks))
        self.assertFalse(any(node.func.attr == 'stop_servers' for node in callbacks))
        self.assertFalse(any(node.func.attr == 'back_up_saves' for node in callbacks))
        self.assertTrue(any(isinstance(node, ast.Attribute) and
                            node.attr == 'HTTPException' for node in ast.walk(coop_install)))


if __name__ == '__main__':
    unittest.main()
