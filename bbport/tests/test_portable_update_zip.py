# SPDX-License-Identifier: GPL-2.0-or-later
"""Portable update safety tests backported from the existing tested launcher candidate."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

class PortableUpdateZipTests(unittest.TestCase):
    def stage(self, names, *, valid=False):
        import io
        import warnings
        import zipfile
        from bbport_update_zip import extract_update

        blob = io.BytesIO()
        with warnings.catch_warnings(), zipfile.ZipFile(blob, 'w') as archive:
            warnings.simplefilter('ignore', UserWarning)  # deliberate duplicate
            for name in names:
                # zipfile's writer normalizes backslashes on Windows. Patch
                # equal-length names in the local and central headers instead.
                archive.writestr(name.replace('\\', '~'), b'fixture')
        blob = io.BytesIO(blob.getvalue().replace(b'bin~escape', br'bin\escape'))
        with tempfile.TemporaryDirectory() as scratch, zipfile.ZipFile(blob) as archive:
            out = Path(scratch) / 'fresh'
            if valid:
                path = extract_update(archive, out)
                self.assertEqual(path, out / 'Игра' / 'BLauncher.exe')
                self.assertEqual(path.read_bytes(), b'fixture')
                with self.assertRaises(FileExistsError):
                    extract_update(archive, out)
            else:
                with self.assertRaises(ValueError):
                    extract_update(archive, out)
                self.assertFalse(out.exists())
                self.assertFalse((Path(scratch) / 'escape').exists())

    def test_valid_unicode_package_and_exclusive_staging(self):
        self.stage(['Игра/BLauncher.exe', 'Игра/bin/probe.exe'], valid=True)

    def test_rejects_ambiguous_or_unsafe_names_before_extraction(self):
        for names in (['../escape'], ['/escape'], ['C:/escape'], [r'bin\escape'],
                      ['bin/AUX.txt'], ['bin/hidden.'], ['bin/stream:alternate'],
                      ['bin/file', 'BIN/other'], ['bin/file', 'bin/File'],
                      ['bin/file', 'bin/file'], ['bin', 'bin/file'],
                      ['nested/BLauncher.exe']):
            with self.subTest(names=names):
                self.stage(['BLauncher.exe', *names])

    def test_download_bounds_and_complete_body(self):
        import io
        from bbport_update_zip import download_update

        for declared, body, valid in ((None, b'abc', True), ('3', b'abc', True),
                                      ('3', b'ab', False), ('2', b'abc', False),
                                      (None, b'abcd', False), ('4', b'abc', False),
                                      ('x', b'abc', False), (None, b'', False)):
            with self.subTest(declared=declared, body=body):
                response, out, progress = io.BytesIO(body), io.BytesIO(), []
                response.headers = {} if declared is None else {'Content-Length': declared}
                with mock.patch('bbport_update_zip.MAX_DOWNLOAD_BYTES', 3):
                    if valid:
                        download_update(response, out, progress.append)
                        self.assertEqual(out.getvalue(), body)
                        self.assertEqual(progress, [100 if declared else 0])
                    else:
                        with self.assertRaises(ValueError):
                            download_update(response, out, progress.append)

    def test_crc_failure_removes_partial_staging_but_preserves_install(self):
        import io
        import zipfile
        from bbport_update_zip import extract_update

        blob = io.BytesIO()
        with zipfile.ZipFile(blob, 'w', compression=zipfile.ZIP_STORED) as archive:
            archive.writestr('BLauncher.exe', b'new')
            archive.writestr('bin/fail.dll', b'original-payload')
        broken = io.BytesIO(blob.getvalue().replace(b'original-payload', b'corrupt--payload'))
        with tempfile.TemporaryDirectory() as scratch, zipfile.ZipFile(broken) as archive:
            installed = Path(scratch) / 'installed'
            installed.mkdir()
            launcher = installed / 'BLauncher.exe'
            launcher.write_bytes(b'old')
            out = Path(scratch) / 'fresh'
            with self.assertRaises(zipfile.BadZipFile):
                extract_update(archive, out)
            self.assertFalse(out.exists())
            self.assertEqual(launcher.read_bytes(), b'old')

    def test_overlay_preserves_saves_and_external_hardlink_target(self):
        from bbport_update_zip import copy_portable_update
        import shutil

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            stage, install = root / 'stage', root / 'install'
            for folder in (stage, install):
                (folder / 'user').mkdir(parents=True)
            (stage / 'BLauncher.exe').write_bytes(b'new')
            (stage / 'user' / 'save').write_bytes(b'package')
            (install / 'user' / 'save').write_bytes(b'player')
            external = root / 'external.exe'
            external.write_bytes(b'old')
            os.link(external, install / 'BLauncher.exe')
            copy_portable_update(stage, install, shutil.ignore_patterns('user'))
            self.assertEqual((install / 'BLauncher.exe').read_bytes(), b'new')
            self.assertEqual((install / 'user' / 'save').read_bytes(), b'player')
            self.assertEqual(external.read_bytes(), b'old')

    def test_interrupted_file_copy_preserves_existing_binary(self):
        from bbport_update_zip import copy_portable_update

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            stage, install = root / 'stage', root / 'install'
            stage.mkdir()
            install.mkdir()
            (stage / 'BLauncher.exe').write_bytes(b'complete new binary')
            existing = install / 'BLauncher.exe'
            existing.write_bytes(b'old')

            def interrupted(_src, temporary):
                Path(temporary).write_bytes(b'incomplete')
                raise OSError('simulated disk write failure')

            with mock.patch('bbport_update_zip.shutil.copyfile', side_effect=interrupted):
                with self.assertRaises(OSError):
                    copy_portable_update(stage, install, lambda *_: ())
            self.assertEqual(existing.read_bytes(), b'old')
            self.assertEqual(list(install.iterdir()), [existing])

    def test_overlay_rejects_linked_directory_before_any_writes(self):
        from bbport_update_zip import copy_portable_update
        import subprocess

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            stage, install, external = (root / name for name in ('stage', 'install', 'external'))
            (stage / 'bin').mkdir(parents=True)
            install.mkdir()
            external.mkdir()
            (stage / 'BLauncher.exe').write_bytes(b'new')
            (stage / 'bin' / 'new.dll').write_bytes(b'new')
            old = install / 'BLauncher.exe'
            old.write_bytes(b'old')
            linked = install / 'bin'
            if os.name == 'nt':
                subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(linked), str(external)],
                               check=True, capture_output=True)
            else:
                linked.symlink_to(external, target_is_directory=True)
            with self.assertRaises(ValueError):
                copy_portable_update(stage, install, lambda *_: ())
            self.assertEqual(old.read_bytes(), b'old')
            self.assertFalse((external / 'new.dll').exists())

    def test_distinct_attempt_staging_and_install_lock(self):
        import subprocess
        from bbport_update_zip import lock_portable_install, make_portable_stage

        with tempfile.TemporaryDirectory() as scratch:
            first = make_portable_stage(scratch)
            second = make_portable_stage(scratch)
            self.assertNotEqual(first, second)
            install = Path(scratch) / 'install'
            install.mkdir()
            script = ("import sys; sys.path.insert(0, sys.argv[1]); "
                      "from bbport_update_zip import lock_portable_install\n"
                      "try:\n with lock_portable_install(sys.argv[2]): pass\n"
                      "except ValueError:\n sys.exit(23)")
            command = [sys.executable, '-c', script, sys.path[0], str(install)]
            with lock_portable_install(install):
                self.assertEqual(subprocess.run(command, timeout=10).returncode, 23)
                with lock_portable_install(second):
                    self.assertTrue(second.is_dir())
            self.assertEqual(subprocess.run(command, timeout=10).returncode, 0)

    def test_rejects_updater_lock_and_transaction_members(self):
        self.stage(['BLauncher.exe', '.bbport-update.lock'])
        self.stage(['BLauncher.exe', '.bbport-update-undo-forged/backup'])

    def test_second_replacement_failure_restores_all_old_files(self):
        from bbport_update_zip import copy_portable_update
        import shutil

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stage, install = root / 'stage', root / 'install'
            (stage / 'bin').mkdir(parents=True)
            (install / 'bin').mkdir(parents=True)
            (install / 'user').mkdir()
            (install / 'user' / 'hunter.save').write_bytes(b'unique-save')
            for name in ('BLauncher.exe', 'bin/game.dll'):
                (stage / name).write_bytes(b'new-' + name.encode())
                (install / name).write_bytes(b'old-' + name.encode())
            original_replace = os.replace
            count = 0

            def fail_second(src, dst):
                nonlocal count
                count += 1
                if count == 2:
                    raise PermissionError('simulated second file lock')
                return original_replace(src, dst)

            with mock.patch('bbport_update_zip.os.replace', side_effect=fail_second):
                with self.assertRaises(PermissionError):
                    copy_portable_update(stage, install, shutil.ignore_patterns('user'))
            for name in ('BLauncher.exe', 'bin/game.dll'):
                self.assertEqual((install / name).read_bytes(), b'old-' + name.encode())
            self.assertEqual((install / 'user' / 'hunter.save').read_bytes(), b'unique-save')
            self.assertFalse(list(install.glob('.bbport-update-undo-*')))

    def test_failed_copy_before_commit_never_mutates_install(self):
        from bbport_update_zip import copy_portable_update

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stage, install = root / 'stage', root / 'install'
            stage.mkdir()
            install.mkdir()
            (stage / 'BLauncher.exe').write_bytes(b'new')
            (install / 'BLauncher.exe').write_bytes(b'old')
            real_copy = __import__('shutil').copyfile

            def fail_backup(src, dst):
                if Path(src) == install / 'BLauncher.exe':
                    raise OSError('simulated backup disk full')
                return real_copy(src, dst)

            with mock.patch('bbport_update_zip.shutil.copyfile', side_effect=fail_backup):
                with self.assertRaises(OSError):
                    copy_portable_update(stage, install, lambda *_: ())
            self.assertEqual((install / 'BLauncher.exe').read_bytes(), b'old')
            self.assertFalse(list(install.glob('.bbport-update-undo-*')))

    def test_rollback_failure_keeps_backups_for_manual_recovery(self):
        from bbport_update_zip import copy_portable_update
        import shutil

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stage, install = root / 'stage', root / 'install'
            stage.mkdir()
            install.mkdir()
            for name in ('BLauncher.exe', 'game.dll'):
                (stage / name).write_bytes(b'new')
                (install / name).write_bytes(b'old')
            original_replace = os.replace
            calls = 0

            def deny_second_and_restore(src, dst):
                nonlocal calls
                calls += 1
                if calls >= 2:
                    raise PermissionError('simulated locked destination and rollback')
                return original_replace(src, dst)

            with mock.patch('bbport_update_zip.os.replace', side_effect=deny_second_and_restore):
                with self.assertRaisesRegex(RuntimeError, 'backups retained at'):
                    copy_portable_update(stage, install, shutil.ignore_patterns('user'))
            backups = list(install.glob('.bbport-update-undo-*'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(sorted(p.read_bytes() for p in (backups[0] / 'originals').iterdir()),
                             [b'old', b'old'])
            self.assertEqual(sum((install / name).read_bytes() == b'new'
                                 for name in ('BLauncher.exe', 'game.dll')), 1)

    def test_rejects_direct_lock_file_overlay(self):
        from bbport_update_zip import copy_portable_update

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stage, install = root / 'stage', root / 'install'
            stage.mkdir()
            install.mkdir()
            (stage / 'BLauncher.exe').write_bytes(b'new')
            (stage / '.bbport-update.lock').write_bytes(b'malicious')
            (install / 'BLauncher.exe').write_bytes(b'old')
            with self.assertRaises(ValueError):
                copy_portable_update(stage, install, lambda *_: ())
            self.assertEqual((install / 'BLauncher.exe').read_bytes(), b'old')

    def test_expanded_budget_is_checked_before_staging(self):
        with mock.patch('bbport_update_zip.MAX_EXPANDED_BYTES', 1):
            self.stage(['BLauncher.exe'])


if __name__ == "__main__":
    unittest.main()
