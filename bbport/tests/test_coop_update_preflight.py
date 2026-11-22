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

    def test_existing_nonbackup_name_is_never_overwritten_or_deleted(self):
        with tempfile.TemporaryDirectory() as scratch:
            install = Path(scratch)
            sample = install / 'user/savedata/1/CUSA03173/SPRJ0005/userdata0000'
            sample.parent.mkdir(parents=True)
            sample.write_bytes(b'original')
            when = 1792900000
            import time
            name = time.strftime('%Y%m%d-%H%M%S', time.localtime(when))
            blocked = install / 'user/save-backups' / name
            blocked.parent.mkdir()
            blocked.write_text('another application owns this name')
            result = coop.back_up_saves(install, 'update', now=when, prune=False)
            self.assertNotEqual(result, blocked)
            self.assertEqual(blocked.read_text(), 'another application owns this name')
            self.assertEqual(coop.save_files(result), coop.save_files(install / 'user'))

    def test_source_that_changes_during_backup_aborts_and_discards_copy(self):
        with tempfile.TemporaryDirectory() as scratch:
            install = Path(scratch)
            sample = install / 'user/savedata/1/CUSA03173/SPRJ0005/userdata0000'
            sample.parent.mkdir(parents=True)
            sample.write_bytes(b'before')
            original_write = Path.write_bytes

            def write_while_game_saves(path, data):
                wrote = original_write(path, data)
                if 'save-backups' in Path(path).parts:
                    original_write(sample, b'after')
                return wrote

            with mock.patch.object(Path, 'write_bytes', write_while_game_saves):
                with self.assertRaisesRegex(OSError, 'changed during backup'):
                    coop.back_up_saves(install, 'update', now=1792900000, prune=False)
            self.assertEqual(sample.read_bytes(), b'after')
            self.assertEqual(list((install / 'user/save-backups').iterdir()), [])

    def test_linked_backup_root_is_refused_without_touching_outside_files(self):
        with tempfile.TemporaryDirectory() as scratch:
            install = Path(scratch)
            sample = install / 'user/savedata/1/CUSA03173/SPRJ0005/userdata0000'
            sample.parent.mkdir(parents=True)
            sample.write_bytes(b'original')
            external = install / 'external'
            external.mkdir()
            sentinel = external / 'unrelated.txt'
            sentinel.write_bytes(b'untouched')
            try:
                (install / 'user/save-backups').symlink_to(external, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest('creating links requires local permissions')
            with self.assertRaisesRegex(OSError, 'symbolic link or junction'):
                coop.back_up_saves(install, 'update', now=1792900000, prune=False)
            self.assertEqual(sentinel.read_bytes(), b'untouched')
            self.assertEqual(sample.read_bytes(), b'original')

    def test_numbered_personal_world_archives_are_backed_up(self):
        # The game's RetireOwnWorld() preserves .txt.1 etc. after a home
        # transition; those were missing from the legacy '*.txt' glob.
        with tempfile.TemporaryDirectory() as root:
            install = Path(root)
            save = install / 'user/savedata/1/CUSA03173/SPRJ0005/userdata0000'
            save.parent.mkdir(parents=True)
            save.write_bytes(b'character')
            before_home = install / 'user/bloodborne_party_personal_world_before_home_slot0.txt'
            archive_1 = Path(str(before_home) + '.1')
            before_home.write_bytes(b'own-world-current')
            archive_1.write_bytes(b'own-world-prior')
            unicode_sidecar = install / 'user/bloodborne_party_имя_персонажа.txt'
            unicode_sidecar.write_bytes(b'legacy-unicode-sidecar')
            (install / 'user/bloodborne_party_private.log').write_bytes(b'never-a-save')
            backup = coop.back_up_saves(install, 'before an update', now=1792900000, prune=False)
            self.assertEqual((backup / before_home.name).read_bytes(), b'own-world-current')
            self.assertEqual((backup / archive_1.name).read_bytes(), b'own-world-prior')
            self.assertEqual((backup / unicode_sidecar.name).read_bytes(),
                             b'legacy-unicode-sidecar')
            self.assertFalse((backup / 'bloodborne_party_private.log').exists())
            self.assertIn(archive_1.name, coop.save_files(backup))

    def test_restore_reinstates_archived_world_and_removes_stale_archive(self):
        with tempfile.TemporaryDirectory() as root:
            install = Path(root)
            save = install / 'user/savedata/1/CUSA03173/SPRJ0005/userdata0000'
            save.parent.mkdir(parents=True)
            save.write_bytes(b'character')
            file_name = 'bloodborne_party_personal_world_before_home_slot0.txt.1'
            world = install / 'user' / file_name
            world.write_bytes(b'world-before')
            snapshot = coop.back_up_saves(install, 'before an update', now=1792900000, prune=False)
            world.write_bytes(b'world-after')
            extra_archive = install / 'user/bloodborne_party_personal_world_before_home_slot0.txt.2'
            extra_archive.write_bytes(b'extra-after')
            coop.restore_saves(install, snapshot.name)
            self.assertEqual(world.read_bytes(), b'world-before')
            self.assertFalse(extra_archive.exists(), 'stale archive must not outlive restored snapshot')
            self.assertEqual(save.read_bytes(), b'character')

    def test_linked_world_sidecar_refuses_backup(self):
        with tempfile.TemporaryDirectory() as root:
            install = Path(root)
            save = install / 'user/savedata/1/CUSA03173/SPRJ0005/userdata0000'
            save.parent.mkdir(parents=True)
            save.write_bytes(b'character')
            external = install / 'external-private'
            external.write_bytes(b'secret')
            sidecar = install / 'user/bloodborne_party_personal_world_slot0.txt'
            try:
                sidecar.symlink_to(external)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks require privileges')
            with self.assertRaisesRegex(OSError, 'symbolic link'):
                coop.back_up_saves(install, 'before an update', now=1792900000, prune=False)
            self.assertEqual(external.read_bytes(), b'secret')

    def test_linked_native_save_file_is_not_read_into_backup(self):
        with tempfile.TemporaryDirectory() as root:
            install = Path(root)
            outside = install / 'private-native-file'
            outside.write_bytes(b'not-a-hunter-save')
            native = install / 'user/savedata/1/CUSA03173/SPRJ0005/userdata0000'
            native.parent.mkdir(parents=True)
            try:
                native.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest('native file symlink creation requires privileges')
            with self.assertRaisesRegex(OSError, 'symbolic link or junction'):
                coop.back_up_saves(install, 'before update', now=1792900000, prune=False)
            self.assertEqual(outside.read_bytes(), b'not-a-hunter-save')
            self.assertFalse((install / 'user/save-backups').exists())

    def test_linked_native_save_directory_is_not_traversed(self):
        with tempfile.TemporaryDirectory() as root:
            install = Path(root)
            outside = install / 'unrelated-profile'
            outside.mkdir()
            (outside / 'userdata0000').write_bytes(b'other-character')
            parent = install / 'user/savedata/1'
            parent.mkdir(parents=True)
            linked = parent / 'CUSA03173'
            try:
                linked.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('native directory symlink creation requires privileges')
            with self.assertRaisesRegex(OSError, 'symbolic link or junction'):
                coop.back_up_saves(install, 'before update', now=1792900000, prune=False)
            self.assertEqual((outside / 'userdata0000').read_bytes(), b'other-character')
            self.assertFalse((install / 'user/save-backups').exists())

    def test_linked_home_root_is_refused_before_any_backup(self):
        with tempfile.TemporaryDirectory() as root:
            install = Path(root)
            outside = install / 'outside-home'
            outside.mkdir()
            (outside / 'unrelated.txt').write_text('private', encoding='utf-8')
            user = install / 'user'
            user.mkdir()
            try:
                (user / 'home').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('home-root symlink creation requires privileges')
            with self.assertRaisesRegex(OSError, 'symbolic link or junction'):
                coop.back_up_saves(install, 'before update', now=1792900000, prune=False)
            self.assertEqual((outside / 'unrelated.txt').read_text(encoding='utf-8'), 'private')
            self.assertFalse((user / 'save-backups').exists())

    def test_regular_native_and_home_save_trees_still_backup(self):
        with tempfile.TemporaryDirectory() as root:
            install = Path(root)
            native = install / 'user/savedata/1/CUSA03173/SPRJ0005/userdata0000'
            home = install / 'user/home/hunter1/savedata/1/CUSA03173/SPRJ0005/userdata0000'
            for path, content in ((native, b'native'), (home, b'home')):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            backup = coop.back_up_saves(install, 'before update', now=1792900000, prune=False)
            self.assertEqual((backup / native.relative_to(install / 'user')).read_bytes(), b'native')
            self.assertEqual((backup / home.relative_to(install / 'user')).read_bytes(), b'home')
            self.assertEqual(coop.save_files(backup), coop.save_files(install / 'user'))

    def test_bad_calendar_backups_do_not_hide_valid_snapshots(self):
        with tempfile.TemporaryDirectory() as root:
            install = Path(root)
            folder = install / 'user/save-backups'
            fake = folder / '20269977-999999'
            fake.mkdir(parents=True)
            (fake / 'launcher.txt').write_text('invalid date', encoding='utf-8')
            valid = folder / '20261024-231630'
            valid.mkdir()
            (valid / 'launcher.txt').write_text('previous working backup', encoding='utf-8')
            actual = coop.save_backups(install)
            self.assertEqual([item['name'] for item in actual], ['20261024-231630'])
            self.assertEqual(actual[0]['note'], 'previous working backup')
            self.assertTrue(fake.exists(), 'malformed folder is not destroyed')

    def test_dated_symlink_backup_refused_before_listing(self):
        with tempfile.TemporaryDirectory() as root:
            install = Path(root)
            backup_root = install / 'user/save-backups'
            backup_root.mkdir(parents=True)
            external = install / 'private'
            external.mkdir()
            (external / 'secret').write_bytes(b'private')
            try:
                (backup_root / '20261024-231630').symlink_to(
                    external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('creating symlinks requires privileges')
            with self.assertRaisesRegex(OSError, 'symbolic link or junction'):
                coop.save_backups(install)
            self.assertEqual((external / 'secret').read_bytes(), b'private')

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
        names = {node.attr for node in ast.walk(coop_install) if isinstance(node, ast.Attribute)}
        self.assertIn('coop_busy', names, 'never upgrade during co-op preparation')
        self.assertIn('installing', names, 'never upgrade during another installation')
        self.assertFalse(any(node.func.attr == 'stop_servers' for node in callbacks))
        self.assertFalse(any(node.func.attr == 'back_up_saves' for node in callbacks))
        self.assertTrue(any(isinstance(node, ast.Attribute) and
                            node.attr == 'HTTPException' for node in ast.walk(coop_install)))


if __name__ == '__main__':
    unittest.main()
