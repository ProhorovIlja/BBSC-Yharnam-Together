"""The launcher stays responsive (a player's installed copy lagged, 2026-10-15): typing in the Co-op
card does not redo the game lookup, the status and the banner art for every key, and with no game
folder set nothing walks the folder the launcher runs from (the install folder: PyInstaller's
_internal and the player's files)."""
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))

if sys.platform == 'win32':
    import bbport_coop
    import bbport_launcher_win as launcher


@unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
class CoopCardTypingTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        import tkinter
        from tkinter import filedialog, messagebox, ttk
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        scratch = Path(self.tmp.name)
        (scratch / 'config').mkdir()
        (scratch / 'config' / 'settings.json').write_text('{"check_updates": false}', encoding='utf-8')
        self.looked_in = []
        real_find = bbport_coop.find_game_folder

        def counting_find(folder, depth=3):
            self.looked_in.append(folder)
            return real_find(folder, depth)

        for patch in (mock.patch.dict(launcher.os.environ, {'BB_CONFIG': str(scratch / 'bbport.ini'),
                                                            'BB_LAUNCHER_ANIMATIONS': '0'}),
                      mock.patch.object(launcher, 'CONFIG_FILE', scratch / 'config' / 'settings.json'),
                      mock.patch.object(launcher, 'CONFIG_DIR', scratch / 'config'),
                      mock.patch.object(launcher, 'DATA_DIR', scratch),
                      mock.patch.object(launcher, 'connected_displays', return_value=[]),
                      mock.patch.object(launcher, 'gpu_tool', return_value=(scratch / 'no-such.exe', {})),
                      mock.patch.object(launcher, 'LANG', 'en'),
                      mock.patch.object(launcher, 'COOP_INSTALL', True),
                      mock.patch.object(bbport_coop, 'load_settings', return_value={}),
                      mock.patch.object(bbport_coop, 'save_settings'),
                      mock.patch.object(bbport_coop, 'search_game', return_value=None),
                      mock.patch.object(bbport_coop, 'fetch_newest_release', return_value=None),
                      mock.patch.object(bbport_coop, 'find_game_folder', side_effect=counting_find)):
            patch.start()
            self.addCleanup(patch.stop)
        for _attempt in range(5):  # Tk now and then cannot find its scripts right after another window closed
            try:
                self.root = tkinter.Tk()
                break
            except tkinter.TclError:
                time.sleep(0.5)
        else:
            self.skipTest('no display for Tk')
        self.addCleanup(self.root.destroy)
        self.app = launcher.Launcher(self.root, tkinter, ttk, filedialog, messagebox)
        self.settle()

    def settle(self, seconds=0.6):
        end = time.time() + seconds
        while time.time() < end:
            self.root.update()
            time.sleep(0.02)

    def test_typing_does_not_redo_the_game_lookup_for_every_key(self):
        self.looked_in.clear()
        host_ip = self.app.coop_vars['host_ip']
        for text in ('1', '10', '10.', '10.0', '10.0.', '10.0.0', '10.0.0.', '10.0.0.5'):
            host_ip.set(text)
            self.root.update()
        self.settle()
        self.assertEqual(self.app.coop['host_ip'], '10.0.0.5', 'the setting is still taken')
        self.assertLessEqual(len(self.looked_in), 3, self.looked_in)

    def test_no_game_folder_walks_nothing(self):
        self.looked_in.clear()
        self.app.coop_vars['game'].set('')
        self.settle()
        self.assertNotIn('.', [str(folder) for folder in self.looked_in])
        self.assertIsNone(self.app.coop_game_info())


class FakeRoot:
    """What Motion asks of the Tk root: a window shown, focused or not."""

    def __init__(self, focused):
        self.focused, self.calls = focused, []
        self.tk = self

    def call(self, *args):
        return '.' if self.focused else ''

    def winfo_viewable(self):
        return True

    def state(self):
        return 'normal'

    def after(self, ms, fn):
        self.calls.append(ms)
        return len(self.calls)


@unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
class AnimationTests(unittest.TestCase):
    def ticks(self, focused):
        root, frames = FakeRoot(focused), []
        motion = launcher.Motion(root, Exception, True)
        motion.loop('embers', 33, frames.append)
        motion.tick()
        motion.close()
        return frames, root.calls[-1]

    def test_the_banner_moves_while_the_launcher_has_the_focus(self):
        frames, delay = self.ticks(focused=True)
        self.assertEqual(len(frames), 1)
        self.assertLess(delay, 100)

    def test_the_banner_rests_while_another_window_has_the_focus(self):
        # The game, or anything else, in front: no drawing 30 times a second behind it.
        frames, delay = self.ticks(focused=False)
        self.assertEqual(frames, [])
        self.assertGreaterEqual(delay, 300)


@unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
class SearchAroundTheInstallTests(unittest.TestCase):
    def test_the_programs_and_appdata_folders_around_an_install_are_not_walked(self):
        # Installed per user, the launcher lives in %LOCALAPPDATA%\Programs: its parent and
        # grandparent hold thousands of other programs' folders, walked with no time limit.
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / 'AppData' / 'Local'
            install = local / 'Programs' / 'Bloodborne Seamless Co-op'
            install.mkdir(parents=True)
            game = local / 'Programs' / 'Other' / 'CUSA03173'
            game.mkdir(parents=True)
            (game / 'eboot.bin').write_bytes(b'x')
            self.assertIsNone(bbport_coop.search_game(install, drives=[], homes=[]))


@unittest.skipUnless(sys.platform == 'win32', 'requires the Windows launcher')
class WorkerLifecycleTests(unittest.TestCase):
    def fake_window(self):
        from types import SimpleNamespace
        import queue

        state = SimpleNamespace(
            server_checking=False, server_starting=False, server_stopping=False,
            server_stop_pending=False, server_status_epoch=0, coop_upnp=None,
            coop_help=None, coop={'host_ip': '192.0.2.20'},
            coop_server_line=mock.Mock(), messagebox=mock.Mock(),
            ui_calls=queue.Queue(), coop_say=mock.Mock(),
            coop_firewall=mock.Mock(return_value=True),
            coop_open_router=mock.Mock(return_value=''),
            coop_help_refresh_public=mock.Mock(),
        )
        state.coop_stop_servers = lambda: launcher.Launcher.coop_stop_servers(state)
        return state

    def test_start_stop_serialized_even_when_stop_clicked_during_start(self):
        state = self.fake_window()
        tasks = []

        class DeferredThread:
            def __init__(self, *, target, daemon, **_):
                self.target = target

            def start(self):
                tasks.append(self.target)

        with (mock.patch.object(launcher.threading, 'Thread', DeferredThread),
              mock.patch.object(launcher.bbport_coop, 'valid_ip', return_value=True),
              mock.patch.object(launcher.bbport_coop, 'is_this_pc', return_value=True),
              mock.patch.object(launcher.bbport_coop, 'start_servers', return_value=['started']) as start,
              mock.patch.object(launcher.bbport_coop, 'stop_servers', return_value='done') as stop,
              mock.patch.object(launcher.bbport_coop, 'server_state', return_value='running'),
              mock.patch.object(launcher.bbport_coop, 'wants_router', return_value=False)):
            launcher.Launcher.coop_start_servers(state)
            launcher.Launcher.coop_start_servers(state)
            self.assertEqual(len(tasks), 1)
            launcher.Launcher.coop_stop_servers(state)
            self.assertTrue(state.server_stop_pending)
            self.assertEqual(len(tasks), 1)
            tasks.pop(0)()
            state.ui_calls.get_nowait()()
            self.assertFalse(state.server_stop_pending)
            self.assertTrue(state.server_stopping)
            self.assertEqual(len(tasks), 1)
            tasks.pop(0)()
            state.ui_calls.get_nowait()()
            self.assertFalse(state.server_starting or state.server_stopping)
            self.assertEqual(state.server_status_epoch, 2)
            start.assert_called_once()
            stop.assert_called_once()

    def test_start_and_stop_thread_failure_resets_status(self):
        state = self.fake_window()
        with (mock.patch.object(launcher.bbport_coop, 'valid_ip', return_value=True),
              mock.patch.object(launcher.bbport_coop, 'is_this_pc', return_value=True),
              mock.patch.object(launcher.threading, 'Thread') as thread):
            thread.return_value.start.side_effect = RuntimeError('no worker')
            launcher.Launcher.coop_start_servers(state)
            self.assertFalse(state.server_starting)
            self.assertIn('no worker', state.coop_server_line.configure.call_args.kwargs['text'])
            launcher.Launcher.coop_stop_servers(state)
            self.assertFalse(state.server_stopping)
            self.assertIn('no worker', state.coop_server_line.configure.call_args.kwargs['text'])

    def test_stale_probe_failure_does_not_replace_active_server_status(self):
        state = self.fake_window()
        state.server_checking = True
        state.server_starting = True
        state.server_status_epoch = 2
        with mock.patch.object(launcher.bbport_coop, 'server_state', side_effect=OSError('probe failed')):
            launcher.Launcher.coop_check_server(state, 1)
        state.ui_calls.get_nowait()()
        self.assertFalse(state.server_checking)
        state.coop_server_line.configure.assert_not_called()

    def test_play_thread_start_failure_returns_to_idle(self):
        state = self.fake_window()
        state.coop_busy = False
        state.coop_changed = mock.Mock()
        state.coop_ready = mock.Mock(return_value=False)
        state.collect = mock.Mock()
        state.open_coop = mock.Mock()
        state.play_button = mock.Mock()
        state.set_running = mock.Mock()
        state.status = mock.Mock()
        state.coop_prepare_and_play = mock.Mock()
        state.coop_start_game = lambda *args: launcher.Launcher.coop_start_game(state, *args)
        with (mock.patch.object(launcher.bbport_coop, 'missing', return_value=False),
              mock.patch.object(launcher.bbport_coop, 'played_settings', return_value={}),
              mock.patch.object(launcher.threading, 'Thread') as thread):
            thread.return_value.start.side_effect = RuntimeError('cannot start thread')
            launcher.Launcher.play_coop(state)
        self.assertFalse(state.coop_busy)
        self.assertEqual(state.play_button.configure.call_args.kwargs['state'], 'normal')
        state.messagebox.showerror.assert_called_once()
        self.assertIn('cannot start thread', state.messagebox.showerror.call_args.args[1])


if __name__ == '__main__':
    unittest.main()
