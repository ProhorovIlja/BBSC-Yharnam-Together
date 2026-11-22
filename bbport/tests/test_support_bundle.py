"""The launcher's support bundle (launcher/bbport_support.py, Kaniel 2026-10-25): one zip with the logs,
reports, settings and a network check, never a save or the player's secret."""
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))

import bbport_support as support  # noqa: E402


def write(path, text='x', when=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='')  # the bytes as given, on Windows too
    if when is not None:
        os.utime(path, (when, when))
    return path


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.user = self.root / 'install' / 'user'
        log = self.user / 'log'
        for name in ('shad_log.txt', 'console.txt', 'shad_log.prev.txt', 'shadnet.txt', 'launcher-errors.txt',
                     'event-patch.txt', 'crash-1792733000.txt', 'freeze-1792733895.txt'):
            write(log / name, name)
        write(log / 'older' / '20261024-210000-shad_log.txt', 'an older run')
        write(log / support.bbport_coop.REPORTS_SENT, '[]')
        for index in range(5):
            write(log / f'coop-trace-2026102{index}-120000-1.txt', f'trace {index}', when=1792700000 + index)
            write(log / f'crash-17927{index}.dmp', 'MDMP', when=1792700000 + index)
        write(self.user / 'savedata' / '1' / 'userdata0010', 'a save')
        write(self.user / 'last_run.log', 'the game exited')
        self.settings = {'game': 'C:/Games/CUSA03173', 'host_ip': '26.1.2.3', 'account': 'p0123456789abcd',
                         'password': 'the-secret'}

    def tearDown(self):
        self.folder.cleanup()

    def make(self, **more):
        target = self.root / 'out' / support.bundle_name(1792900000)
        failed = support.make_bundle(target, self.user, settings=self.settings, **more)
        with zipfile.ZipFile(target) as bundle:
            return failed, {name: bundle.read(name).decode('utf-8', 'replace') for name in bundle.namelist()}

    def test_the_logs_and_reports_are_in(self):
        failed, files = self.make()
        self.assertEqual(failed, [])
        for name in ('log/shad_log.txt', 'log/console.txt', 'log/shad_log.prev.txt', 'log/shadnet.txt',
                     'log/launcher-errors.txt', 'log/event-patch.txt', 'log/crash-1792733000.txt',
                     'log/freeze-1792733895.txt', 'log/older/20261024-210000-shad_log.txt', 'last_run.log'):
            self.assertIn(name, files)
        self.assertNotIn('log/' + support.bbport_coop.REPORTS_SENT, files)

    def test_only_the_newest_traces_and_dumps(self):
        _failed, files = self.make()
        traces = sorted(name for name in files if 'coop-trace-' in name)
        self.assertEqual(traces, [f'log/coop-trace-2026102{index}-120000-1.txt' for index in (2, 3, 4)])
        dumps = sorted(name for name in files if name.endswith('.dmp'))
        self.assertEqual(dumps, [f'log/crash-17927{index}.dmp' for index in (2, 3, 4)])

    def test_no_save_and_no_secret(self):
        _failed, files = self.make()
        self.assertFalse(any('savedata' in name for name in files))
        self.assertNotIn('the-secret', ''.join(files.values()))
        coop = json.loads(files['coop.json'])
        self.assertEqual(coop['password'], support.LEFT_OUT)
        self.assertEqual(coop['account'], 'p0123456789abcd', "the server's log names the player by it")

    def test_saved_per_server_credentials_are_never_exported(self):
        self.settings['server_ids'] = {
            'private-host': ['hunter-a', 'private-secret-a'],
            'other-host': ['hunter-b', 'private-secret-b'],
            'unknown': {'password': 'unexpected-secret'}
        }
        self.settings['access_token'] = 'access-token-private'
        self.settings['refresh_token'] = 'refresh-token-private'
        _failed, files = self.make()
        combined = ''.join(files.values())
        for secret in ('the-secret', 'private-secret-a', 'private-secret-b',
                       'unexpected-secret', 'access-token-private', 'refresh-token-private'):
            self.assertNotIn(secret, combined)
        copied = json.loads(files['coop.json'])
        self.assertEqual(copied['account'], 'p0123456789abcd')
        self.assertEqual(copied['server_ids']['private-host'], ['hunter-a', support.LEFT_OUT])
        self.assertEqual(copied['server_ids']['other-host'], ['hunter-b', support.LEFT_OUT])
        self.assertEqual(copied['server_ids']['unknown'], support.LEFT_OUT)
        self.assertEqual(copied['access_token'], support.LEFT_OUT)
        self.assertEqual(copied['refresh_token'], support.LEFT_OUT)
        self.assertEqual(self.settings['server_ids']['private-host'][1], 'private-secret-a',
                         'redaction must never mutate real credentials')

    def test_unknown_settings_and_nested_tokens_never_enter_diagnostics(self):
        self.settings['future_account_state'] = {'authorization': 'new-secret',
                                                 'refresh_token': 'refresh-value'}
        self.settings['Session_Token'] = 'session-token'
        self.settings['current_password'] = 'current-password'
        self.settings['api_key'] = 'other-private-key'
        self.settings['server_keys'] = {
            'trusted-server': 'ab' * 32,
            'malformed-server': {'secret': 'unexpected-key'},
            'wrong-length': 'key-only'
        }
        _failed, files = self.make()
        snapshot = files['coop.json']
        for secret in ('new-secret', 'refresh-value', 'session-token',
                       'current-password', 'other-private-key', 'unexpected-key'):
            self.assertNotIn(secret, snapshot)
        saved = json.loads(snapshot)
        self.assertNotIn('future_account_state', saved)
        self.assertEqual(saved['Session_Token'], support.LEFT_OUT)
        self.assertEqual(saved['current_password'], support.LEFT_OUT)
        self.assertEqual(saved['api_key'], support.LEFT_OUT)
        self.assertEqual(saved['server_keys'], {'trusted-server': 'ab' * 32})
        self.assertEqual(saved['host_ip'], self.settings['host_ip'])
        self.assertEqual(self.settings['future_account_state']['authorization'], 'new-secret',
                         'snapshot creation must not alter live account settings')

    def test_texts_and_extra_files(self):
        ini = write(self.root / 'install' / 'bbport.ini', 'upscaler=fsr3\n')
        home = str(self.root / 'home' / 'vitsh')
        _failed, files = self.make(extra_files=[(ini, 'bbport.ini'), (self.root / 'none.ini', 'none.ini')],
                                   texts={'launcher-log.txt': f'started from {home}\\Games'}, home=home)
        self.assertEqual(files['bbport.ini'], 'upscaler=fsr3\n')
        self.assertNotIn('none.ini', files, 'a missing file is skipped')
        self.assertEqual(files['launcher-log.txt'], 'started from %USERPROFILE%\\Games')

    def test_an_unreadable_file_is_listed_not_fatal(self):
        real = zipfile.ZipFile.write

        def busy(bundle, path, name=None, *args, **kwargs):
            if str(name).endswith('freeze-1792733895.txt'):
                raise PermissionError(13, 'The process cannot access the file')
            return real(bundle, path, name, *args, **kwargs)

        zipfile.ZipFile.write = busy
        try:
            failed, files = self.make()
        finally:
            zipfile.ZipFile.write = real
        self.assertEqual(failed, [('log/freeze-1792733895.txt', 'The process cannot access the file')])
        self.assertIn('freeze-1792733895.txt', files['missing.txt'])
        self.assertIn('log/shad_log.txt', files)

    def test_raw_logs_are_explicitly_marked_as_sensitive(self):
        _failed, contents = self.make()
        text = contents['REVIEW-BEFORE-SHARING.txt']
        self.assertIn('review before sharing', text)
        self.assertIn('crash dumps', text)
        self.assertIn('account names', text)
        self.assertIn('host_overrides.custom.json', text)
        self.assertIn('\n', text)

    def test_support_bundle_never_auto_attaches_private_override_settings(self):
        write(self.user / 'host_overrides.custom.json',
              '{"password":"private-override","refresh_token":"also-private"}')
        failed, contents = self.make()
        self.assertEqual(failed, [])
        self.assertNotIn('host_overrides.custom.json', contents)
        self.assertNotIn('private-override', ''.join(contents.values()))
        self.assertNotIn('also-private', ''.join(contents.values()))

    def test_support_bundle_skips_linked_log_and_extra_file(self):
        secret = write(self.root / 'private' / 'secret.txt', 'private-outside-install')
        linked_log = self.user / 'log' / 'linked-private.txt'
        linked_extra = self.root / 'linked.ini'
        try:
            linked_log.symlink_to(secret)
            linked_extra.symlink_to(secret)
        except (OSError, NotImplementedError):
            self.skipTest('creating symlinks requires local privileges')
        failed, contents = self.make(extra_files=[(linked_extra, 'config.ini')])
        self.assertEqual(failed, [])
        self.assertNotIn('log/linked-private.txt', contents)
        self.assertNotIn('config.ini', contents)
        self.assertNotIn('private-outside-install', ''.join(contents.values()))

    def test_linked_old_logs_directory_is_not_recursed(self):
        external = self.root / 'unrelated-folder'
        write(external / 'private.txt', 'outside-private-data')
        old = self.user / 'log' / 'older'
        for child in old.iterdir():
            child.unlink()
        old.rmdir()
        try:
            old.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('creating directory links requires local privileges')
        _failed, contents = self.make()
        self.assertFalse(any(name.startswith('log/older/') for name in contents))
        self.assertNotIn('outside-private-data', ''.join(contents.values()))

    def test_existing_part_symlink_cannot_redirect_archive_staging(self):
        output = self.root / 'out'
        output.mkdir()
        stage = output / (support.bundle_name(1792900000) + '.part')
        private = write(self.root / 'private' / 'target.txt', 'original-private')
        try:
            stage.symlink_to(private)
        except (OSError, NotImplementedError):
            self.skipTest('creating symlinks requires local privileges')
        failed, contents = self.make()
        self.assertEqual(failed, [])
        self.assertIn('coop.json', contents)
        self.assertEqual(private.read_text(encoding='utf-8'), 'original-private')
        self.assertFalse(list(output.glob('*.part-*')), 'unique staging should be cleaned')

    def test_log_rotation_disappearance_does_not_abort_newest_sort(self):
        first = self.user / 'log' / 'coop-trace-20261020-120000-1.txt'
        second = self.user / 'log' / 'coop-trace-20261021-120000-1.txt'
        write(first, 'older', when=1792700001)
        write(second, 'newer', when=1792700002)
        actual_stat = Path.stat

        def log_disappeared(path, *args, **kwargs):
            if Path(path) == first:
                raise FileNotFoundError('rotated before metadata read')
            return actual_stat(path, *args, **kwargs)

        with mock.patch.object(Path, 'stat', log_disappeared):
            self.assertEqual(support.newest([first, second], 2), [second])

    def test_staging_is_removed_if_zip_write_fails(self):
        output = self.root / 'out'
        real_write = zipfile.ZipFile.writestr

        def fail_after_open(*_args, **_kwargs):
            raise OSError('simulated disk write failure')

        with mock.patch.object(zipfile.ZipFile, 'writestr', side_effect=fail_after_open):
            with self.assertRaisesRegex(OSError, 'simulated disk write failure'):
                support.make_bundle(output / support.bundle_name(1792900000),
                                    self.user, settings=self.settings)
        self.assertEqual(list(output.iterdir()), [], 'no partial private ZIP remains')
        self.assertIsNotNone(real_write)  # existing ZipFile implementation remains intact

    def test_no_half_written_zip_is_left(self):
        self.make()
        self.assertEqual([path.name for path in (self.root / 'out').iterdir()], [support.bundle_name(1792900000)])

    def test_a_live_log_can_be_bundled(self):
        # The game keeps its log open and writing while the bundle reads it.
        with open(self.user / 'log' / 'shad_log.txt', 'a', encoding='utf-8') as live:
            live.write(' and more')
            live.flush()
            _failed, files = self.make()
        self.assertEqual(files['log/shad_log.txt'], 'shad_log.txt and more')

    def test_no_log_folder_yet(self):
        empty = self.root / 'fresh' / 'user'
        target = self.root / 'fresh.zip'
        self.assertEqual(support.make_bundle(target, empty, texts={'system.txt': 'x'}), [])
        with zipfile.ZipFile(target) as bundle:
            self.assertEqual(bundle.namelist(), ['REVIEW-BEFORE-SHARING.txt', 'system.txt'])


class ReportTests(unittest.TestCase):
    def test_bundle_name_and_folder(self):
        self.assertRegex(support.bundle_name(1792900000), r'^Yharnam Together support \d{8}-\d{6}\.zip$')
        with tempfile.TemporaryDirectory() as home:
            self.assertEqual(support.default_folder(home), Path(home))
            (Path(home) / 'Desktop').mkdir()
            self.assertEqual(support.default_folder(home), Path(home) / 'Desktop')

    def test_the_desktop_windows_shows(self):
        # Kaniel 2026-11-01: with the Desktop moved (OneDrive), %USERPROFILE%\Desktop can still be there,
        # empty, while Windows shows another one: the zip went where nobody looks.
        with tempfile.TemporaryDirectory() as home:
            shown = Path(home) / 'OneDrive' / 'Desktop'
            shown.mkdir(parents=True)
            (Path(home) / 'Desktop').mkdir()
            self.assertEqual(support.default_folder(home, known_desktop=str(shown)), shown)
            # A known folder that is gone: the old guess.
            self.assertEqual(support.default_folder(home, known_desktop=str(Path(home) / 'gone')),
                             Path(home) / 'Desktop')

    def test_explorer_selects_the_zip(self):
        # Kaniel 2026-11-01: "support bundle don't open correct folder". The zip's name has spaces, and
        # a list made subprocess quote the whole "/select,<path>" switch, which Explorer does not read:
        # it opened its default folder. Only the path is quoted.
        target = support.PureWindowsPath(r'C:\Users\Kaniel\Desktop') / 'Yharnam Together support 20261101-180914.zip'
        command = support.reveal_command(target, r'C:\Windows')
        self.assertIsInstance(command, str)
        self.assertEqual(command, r'"C:\Windows\explorer.exe" /select,"' + str(target) + '"')
        self.assertNotIn('"/select', command)

    def test_network_report(self):
        asked = []

        def answers(host, port):
            asked.append((host, port))
            return port != support.bbport_coop.BACKEND_PORT

        text = support.network_report({'host_ip': '26.1.2.3'}, answers=answers,
                                      addresses=['192.168.1.5', '26.9.8.7'], this_pc=False)
        self.assertIn("Host's IP address: 26.1.2.3 (Radmin VPN)", text)
        self.assertIn('This PC hosts: no', text)
        self.assertIn('VPNs on this PC: Radmin VPN 26.9.8.7', text)
        self.assertIn(f'TCP {support.bbport_coop.SHADNET_PORT}: answers', text)
        self.assertIn(f'TCP {support.bbport_coop.BACKEND_PORT}: no answer', text)
        self.assertEqual({host for host, _port in asked}, {'26.1.2.3'})

    def test_network_report_without_a_host(self):
        text = support.network_report({}, answers=lambda *_a: self.fail('nothing to ask'), addresses=[],
                                      this_pc=False)
        self.assertIn("Host's IP address: (not set)", text)
        self.assertNotIn('TCP', text)

    def test_system_report(self):
        text = support.system_report({'Launcher': '1.7.1', 'Release': '1.2.0'}, now=1792900000)
        self.assertIn('Launcher: 1.7.1\nRelease: 1.2.0\n', text)
        self.assertIn('System: ', text)

    def test_the_overlays_vulkan_layers_are_listed(self):
        # Kaniel 2026-11-01: players say an overlay stops them joining; nobody had logs of which one.
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / 'overlay.json'
            manifest.write_text('{"layer": {"name": "VK_LAYER_Overlay_x64", "description": "x"}}', encoding='utf-8')
            entries = [(str(manifest), 0), (str(Path(folder) / 'gone.json'), 1)]
            layers = support.vulkan_layers(read=lambda: entries)
        self.assertEqual(layers, [('VK_LAYER_Overlay_x64', str(manifest), True),
                                  ('?', str(Path(folder) / 'gone.json'), False)])
        text = support.system_report({}, now=1792900000, layers=layers)
        self.assertIn('Vulkan overlay layers (2):\n', text)
        self.assertIn(f'  VK_LAYER_Overlay_x64 on ({manifest})\n', text)
        self.assertIn('  ? off (', text)

    def test_the_games_log_starts_with_the_overlays_it_loads(self):
        layers = [('VK_LAYER_Discord_x64', 'C:/d.json', True), ('VK_LAYER_HudSight2', 'C:/h.json', True),
                  ('VK_LAYER_obs', 'C:/o.json', False), ('?', 'C:/gone.json', True)]
        line = support.overlay_log_line(layers, '*HudSight*,VK_LAYER_x')
        self.assertEqual(line, 'Launcher: Vulkan overlay layers: VK_LAYER_Discord_x64, VK_LAYER_HudSight2 '
                               '(skipped), VK_LAYER_obs (off), ? (C:/gone.json)\n')
        self.assertEqual(support.overlay_log_line([], ''), 'Launcher: Vulkan overlay layers: none\n')

    def test_no_overlay_layers(self):
        self.assertEqual(support.vulkan_layers(read=lambda: []), [])
        self.assertIn('Vulkan overlay layers: none\n', support.system_report({}, now=1792900000, layers=[]))
        # Off Windows (and the cloud) the registry is not there: nothing, no error.
        self.assertIsInstance(support.vulkan_layers(), list)


class LauncherTests(unittest.TestCase):
    def test_the_button_is_on_the_log_and_co_op_pages_and_translated_everywhere(self):
        import ast
        import bbport_lang
        launcher = Path(__file__).resolve().parents[1] / 'launcher' / 'bbport_launcher_win.py'
        source = launcher.read_text(encoding='utf-8')
        functions = {f.name: f for f in ast.walk(ast.parse(source)) if isinstance(f, ast.FunctionDef)}
        for page in ('build_log', 'build_coop_popup'):
            self.assertIn('self.make_support_bundle', ast.unparse(functions[page]), page)
        names = ('make_support_bundle', 'support_bundle_worker', 'support_bundle_done')
        texts = {n.args[0].value for name in names for n in ast.walk(functions[name]) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == '_' and n.args
                 and isinstance(n.args[0], ast.Constant)}
        texts.add('Support bundle')
        self.assertEqual(len(texts), 5)
        for language in ('ar', 'es', 'pt', 'fr', 'de', 'it', 'pl', 'tr', 'zh', 'ja', 'ko'):
            table = bbport_lang.table(language)
            for text in texts:
                self.assertTrue(table.get(text), f'{language}: {text}')
                self.assertEqual(table[text].count('{}'), text.count('{}'), f'{language}: {text}')
        self.assertIn('bbport_support.worker_priority()', ast.unparse(functions['support_bundle_worker']),
                      'zipping never takes time from the game')


if __name__ == '__main__':
    unittest.main()
