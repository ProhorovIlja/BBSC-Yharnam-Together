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

    def test_expanded_budget_is_checked_before_staging(self):
        with mock.patch('bbport_update_zip.MAX_EXPANDED_BYTES', 1):
            self.stage(['BLauncher.exe'])


if __name__ == "__main__":
    unittest.main()
