# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic bundles plus a developer-owned compiled host executable; no game data."""
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import prepared_native as pn


def header(target):
    data = bytearray(256)
    if target == 'linux-x64':
        data[:7] = b'\x7fELF\x02\x01\x01'
        struct.pack_into('<HH', data, 16, 2, 62)
        struct.pack_into('<H', data, 52, 64)
    elif target == 'windows-x64':
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 60, 128)
        data[128:132] = b'PE\0\0'
        struct.pack_into('<H', data, 132, 0x8664)
        struct.pack_into('<H', data, 152, 0x20b)
    else:
        data[:4] = b'\xcf\xfa\xed\xfe'
        struct.pack_into('<I', data, 4, 0x0100000c)
        struct.pack_into('<I', data, 12, 2)
    return data


class PreparedNative(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / 'cache'
        self.selection = {'schema': 1, 'status': 'profile_selected_not_prepared',
                          'profile': 'fixture', 'target': 'linux-x64',
                          'recipe_sha256': 'a' * 64, 'selection_key': 'b' * 64}
        self.deps = {'toolchain': 'c' * 64, 'runtime_abi': 'd' * 64, 'modules': 'e' * 64}
        self.calls = 0

    def build(self, stage, cancelled):
        self.calls += 1
        (stage / 'host').write_bytes(header(self.selection['target']))
        return 'host'

    def prepare(self, build=None, **kw):
        return pn.prepare(self.cache, self.selection, self.deps, build or self.build, **kw)

    def edit_manifest(self, ready, edit):
        path = ready['folder'] / 'manifest.json'
        value = json.loads(path.read_text())
        edit(value)
        path.write_text(json.dumps(value), encoding='utf-8')

    def test_reuse_then_dependency_invalidation(self):
        first = self.prepare()
        self.assertFalse(first['reused'])
        self.assertTrue(self.prepare()['reused'])
        self.assertEqual(self.calls, 1)
        for key in self.deps:
            self.deps[key] = 'f' * 64
            new = self.prepare()
            self.assertFalse(new['reused'])
            self.assertNotEqual(first['folder'], new['folder'])
            first = new
        self.selection['recipe_sha256'] = 'f' * 64
        self.assertFalse(self.prepare()['reused'])
        self.assertEqual(self.calls, 5)

    def test_failure_and_cancellation_preserve_current(self):
        first = self.prepare()
        pointer = (self.cache / 'current.json').read_bytes()
        self.deps['modules'] = 'f' * 64
        def fail(stage, cancelled):
            (stage / 'partial').write_bytes(b'x')
            raise RuntimeError('compiler failed')
        with self.assertRaisesRegex(RuntimeError, 'compiler failed'):
            self.prepare(fail)
        def cancel_after_build(stage, cancelled):
            self.build(stage, cancelled)
            flag[0] = True
            return 'host'
        flag = [False]
        with self.assertRaisesRegex(pn.PreparationError, 'preparation_cancelled'):
            self.prepare(cancel_after_build, cancelled=lambda: flag[0])
        self.assertEqual((self.cache / 'current.json').read_bytes(), pointer)
        self.assertEqual(pn.current(self.cache)['folder'], first['folder'])
        self.assertEqual(list(self.cache.glob('.staging-*')), [])

    def test_pointer_publish_failure_keeps_previous(self):
        first = self.prepare()
        pointer = (self.cache / 'current.json').read_bytes()
        self.deps['modules'] = 'f' * 64
        write = pn._write_json
        def fail(path, value):
            if path.name == 'current.json':
                raise OSError('publication failed')
            write(path, value)
        with patch.object(pn, '_write_json', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'publication failed'):
                self.prepare()
        self.assertEqual((self.cache / 'current.json').read_bytes(), pointer)
        self.assertEqual(pn.current(self.cache)['entry'], first['entry'])
        self.assertEqual(len(list((self.cache / 'builds').iterdir())), 2)

    def test_integrity_and_extra_file_rebuild(self):
        first = self.prepare()
        first['entry'].write_bytes(b'changed')
        with self.assertRaisesRegex(pn.PreparationError, 'artifact_integrity_failed'):
            pn.current(self.cache)
        second = self.prepare()
        self.assertFalse(second['reused'])
        (second['folder'] / 'extra.txt').write_text('unexpected')
        with self.assertRaisesRegex(pn.PreparationError, 'artifact_integrity_failed'):
            pn.current(self.cache)

    def test_invalid_pointer_and_manifest_are_not_executed(self):
        ready = self.prepare()
        pointer = self.cache / 'current.json'
        original = pointer.read_bytes()
        for text in ['{"schema":1,"build":"../../escape"}',
                     '{"schema":true,"build":"' + ready['folder'].name + '"}',
                     '{"schema":1,"schema":1,"build":"' + ready['folder'].name + '"}']:
            pointer.write_text(text)
            with self.subTest(text=text), self.assertRaises(pn.PreparationError):
                pn.current(self.cache)
        pointer.write_bytes(original)
        self.edit_manifest(ready, lambda v: v.update(schema=True))
        with self.assertRaisesRegex(pn.PreparationError, 'invalid_build_manifest'):
            pn.current(self.cache)

    def test_boolean_sizes_do_not_equal_integer_sizes(self):
        def build(stage, cancelled):
            self.build(stage, cancelled)
            (stage / 'one.txt').write_bytes(b'x')
            return 'host'
        ready = self.prepare(build)
        self.edit_manifest(ready, lambda v: v['files']['one.txt'].update(size=True))
        with self.assertRaisesRegex(pn.PreparationError, 'artifact_integrity_failed'):
            pn.current(self.cache)

    def test_wrong_host_console_and_empty_payload(self):
        for payload in (b'', b'\x4f\x15\x3d\x1d' + bytes(256), header('windows-x64')):
            def build(stage, cancelled):
                (stage / 'host').write_bytes(payload)
                return 'host'
            with self.subTest(payload=payload[:8]), self.assertRaisesRegex(
                    pn.PreparationError, 'not_the_selected_host_executable'):
                self.prepare(build)
        console_elf = header('linux-x64')
        struct.pack_into('<H', console_elf, 16, 0xfe10)
        with self.assertRaisesRegex(pn.PreparationError, 'not_the_selected_host_executable'):
            pn._host_header(self._write('console', console_elf), 'linux-x64')

    def _write(self, name, payload):
        path = self.root / name
        path.write_bytes(payload)
        return path

    def test_all_host_header_shapes_and_wrong_architecture(self):
        for target in ('windows-x64', 'linux-x64', 'macos-arm64'):
            with self.subTest(target=target):
                path = self._write('header', header(target))
                pn._host_header(path, target)
                for other in {'windows-x64', 'linux-x64', 'macos-arm64'} - {target}:
                    with self.assertRaises(pn.PreparationError):
                        pn._host_header(path, other)

    def test_paths_and_console_modules(self):
        for name in ('../host', '/host', 'a//b', 'a/./b', 'a\\b', 'CON.exe', 'host.', 'x:host'):
            with self.subTest(name=name), self.assertRaisesRegex(pn.PreparationError, 'invalid_artifact_path'):
                self.prepare(lambda stage, cancelled: name)
        def build(stage, cancelled):
            self.build(stage, cancelled)
            (stage / 'lib.prx').write_bytes(b'console')
            return 'host'
        with self.assertRaisesRegex(pn.PreparationError, 'non_runtime_artifact'):
            self.prepare(build)

    @unittest.skipUnless(os.name == 'posix', 'POSIX filesystem link fixture')
    def test_links_and_case_collisions(self):
        outside = self._write('outside', b'x')
        for link in ('symlink', 'hardlink'):
            def build(stage, cancelled):
                self.build(stage, cancelled)
                if link == 'symlink':
                    (stage / 'linked').symlink_to(outside)
                else:
                    os.link(outside, stage / 'linked')
                return 'host'
            with self.subTest(link=link), self.assertRaises(pn.PreparationError):
                self.prepare(build)
        # Skip name collision fixture on case-insensitive volumes.
        probe = self._write('lower', b'x')
        if not (self.root / 'LOWER').exists():
            def build(stage, cancelled):
                self.build(stage, cancelled)
                (stage / 'HOST').write_bytes(b'x')
                return 'host'
            with self.assertRaisesRegex(pn.PreparationError, 'ambiguous_artifact_path'):
                self.prepare(build)

    def test_invalid_selection_and_dependencies(self):
        for key, value in (('schema', True), ('target', 'ps4'), ('selection_key', 'bad'), ('profile', '../x')):
            bad = dict(self.selection, **{key: value})
            with self.subTest(key=key), self.assertRaises(pn.PreparationError):
                pn.prepare(self.cache, bad, self.deps, self.build)
        with self.assertRaisesRegex(pn.PreparationError, 'invalid_build_dependencies'):
            pn.prepare(self.cache, self.selection, dict(self.deps, toolchain=True), self.build)

    def test_kernel_lock_busy_and_recovers_after_process_death(self):
        self.cache.mkdir()
        child_code = ('import sys,time; from pathlib import Path; import prepared_native as p; '
                      'ctx=p._lock(Path(sys.argv[1])); ctx.__enter__(); '
                      'print("locked",flush=True); time.sleep(30)')
        env = dict(os.environ, PYTHONPATH=str(Path(pn.__file__).parent.resolve()))
        child = subprocess.Popen([sys.executable, '-c', child_code, str(self.cache)],
                                 env=env, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'locked')
            with self.assertRaisesRegex(pn.PreparationError, 'preparation_busy'):
                self.prepare()
        finally:
            child.kill()
            child.wait(timeout=10)
            child.stdout.close()
        self.assertFalse(self.prepare()['reused'])

    def test_launch_wrong_platform_fails_before_spawn(self):
        self.prepare()
        with patch.object(pn.sys, 'platform', 'unsupported'), patch.object(pn.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(pn.PreparationError, 'wrong_launch_platform'):
                pn.launch(self.cache, self.root, self.root / 'user')
            spawn.assert_not_called()

    def test_launch_rejects_overlapping_cache_assets_and_user_before_writing(self):
        self.selection['target'] = {'linux': 'linux-x64', 'win32': 'windows-x64',
                                    'darwin': 'macos-arm64'}[sys.platform]
        ready = self.prepare()
        assets = self.root / 'assets'
        assets.mkdir()
        (assets / 'nested').mkdir()
        user = self.root / 'user'
        forbidden = ready['folder'] / 'writable'
        cases = ((assets, forbidden), (assets, self.cache), (assets, self.root),
                 (self.cache, user), (ready['folder'], user), (assets, assets),
                 (assets, assets / 'writable'), (assets / 'nested', assets))
        alias = self.root / 'ASSETS'
        if alias.exists():
            cases += ((assets, alias / 'writable'),)
        for asset_path, user_path in cases:
            with self.subTest(assets=asset_path, user=user_path):
                with patch.object(pn.subprocess, 'Popen') as spawn:
                    with self.assertRaisesRegex(pn.PreparationError, 'overlapping_runtime_directories'):
                        pn.launch(self.cache, asset_path, user_path, self.selection, self.deps)
                    spawn.assert_not_called()
        self.assertFalse(forbidden.exists())
        self.assertFalse(user.exists())
        self.assertFalse((assets / 'writable').exists())

    def test_actual_host_launch_after_preparation_input_removed(self):
        target = {'linux': 'linux-x64', 'darwin': 'macos-arm64', 'win32': 'windows-x64'}.get(sys.platform)
        compiler = shutil.which('cl' if sys.platform == 'win32' else 'cc')
        if not target or not compiler:
            self.skipTest('needs supported host C compiler')
        arch = platform.machine().lower()
        if arch not in ({'arm64', 'aarch64'} if sys.platform == 'darwin' else {'x86_64', 'amd64'}):
            self.skipTest('unsupported host architecture')
        self.selection['target'] = target
        source = self.root / 'developer_fixture.c'
        source.write_text('''#include <stdio.h>
#include <stdlib.h>
int main(void) {
    if (getenv("BB_EBOOT") || getenv("BB_PROBE") || getenv("BB_ELF") || getenv("BB_GAME_DIR")) return 40;
    const char *root = getenv("BB_NATIVE_USER_DIR");
    if (!root || !getenv("BB_NATIVE_ASSET_ROOT")) return 41;
    char path[4096];
    if (snprintf(path, sizeof(path), "%s/result.txt", root) >= (int)sizeof(path)) return 42;
    FILE *f = fopen(path, "w"); if (!f) return 43;
    fputs("host-entry-ran", f); return fclose(f) ? 44 : 0;
}
''', encoding='utf-8')
        def build(stage, cancelled):
            entry = 'host.exe' if sys.platform == 'win32' else 'host'
            args = ([compiler, '/nologo', str(source), '/Fe:' + str(stage / entry),
                     '/Fo:' + str(self.root / 'fixture.obj')] if sys.platform == 'win32' else
                    [compiler, str(source), '-o', str(stage / entry)])
            subprocess.run(args, check=True, capture_output=True, timeout=30)
            return entry
        self.prepare(build)
        source.unlink()
        assets = self.root / 'assets'
        assets.mkdir()
        user = self.root / 'user'
        with patch.dict(os.environ, BB_EBOOT='removed-input', BB_PROBE='must-not-run'):
            child = pn.launch(self.cache, assets, user, self.selection, self.deps)
            self.assertEqual(child.wait(timeout=10), 0)
        self.assertEqual((user / 'result.txt').read_text(), 'host-entry-ran')
        self.assertFalse(source.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
