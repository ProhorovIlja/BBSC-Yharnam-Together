"""The launcher stays responsive (a player's installed copy lagged, 2026-10-15): typing in the Co-op
card does not redo the game lookup, the status and the banner art for every key, and with no game
folder set nothing walks the folder the launcher runs from (the install folder: PyInstaller's
_internal and the player's files)."""
import queue
import sys
import time
import types
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
                                                            'BB_LAUNCHER_ANIMATIONS': '0',
                                                            'BB_LAUNCHER_CUSTOM_CHROME': '0'}),
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

    def test_windows_owns_title_bar_and_resize_border_by_default(self):
        self.assertTrue(self.app.chrome.native_frame)
        self.assertFalse(self.root.overrideredirect())
        self.assertEqual(self.app.caption_buttons, {})
        self.assertFalse(hasattr(self.app, 'grip'))
        self.assertEqual(self.root.resizable(), (1, 1))


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

    def test_drag_pauses_animation_until_release(self):
        root, frames = FakeRoot(True), []
        motion = launcher.Motion(root, Exception, True)
        try:
            motion.loop('embers', 33, frames.append)
            motion.paused = True
            motion.tick()
            self.assertEqual(frames, [])
            motion.paused = False
            motion.tick()
            self.assertEqual(len(frames), 1)
        finally:
            motion.close()

    def test_drag_defers_queued_ui_work_until_release(self):
        callback = mock.Mock()
        window = types.SimpleNamespace(chrome=types.SimpleNamespace(grab=(1, 2)), ui_calls=queue.Queue(),
                                       output=queue.Queue(), root=mock.Mock(), drain_output=mock.Mock())
        window.ui_calls.put(callback)
        launcher.Launcher.drain_output(window)
        callback.assert_not_called()
        window.chrome.grab = None
        launcher.Launcher.drain_output(window)
        callback.assert_called_once_with()

    def test_scrolled_page_only_updates_layout_when_it_changes(self):
        outer, body, inner, canvas, bar = (mock.Mock() for _ in range(5))
        window = types.SimpleNamespace(
            tk=types.SimpleNamespace(Frame=mock.Mock(side_effect=[outer, body, inner]),
                                     Canvas=mock.Mock(return_value=canvas)),
            ttk=types.SimpleNamespace(Scrollbar=mock.Mock(return_value=bar)),
            px=lambda n: n, content=mock.Mock(), pages={},
        )
        canvas.create_window.return_value = 42
        canvas.winfo_height.return_value = 300
        inner.winfo_reqheight.return_value = 400
        self.assertIs(launcher.Launcher.scrolled_page(window, 'test', None, None), inner)
        resize = canvas.bind.call_args.args[1]
        fit = inner.bind.call_args.args[1]
        canvas.configure.reset_mock()
        for _ in range(100):
            resize(types.SimpleNamespace(width=640))
            fit()
        canvas.itemconfigure.assert_called_once_with(42, width=640)
        canvas.configure.assert_called_once_with(scrollregion=(0, 0, 1, 408))
        bar.pack.assert_called_once_with(side='right', fill='y', padx=(0, 4), before=canvas)
        bar.pack_forget.assert_not_called()

        # Height-only resize still hides the scrollbar; changed content can show it again.
        canvas.winfo_height.return_value = 450
        resize(types.SimpleNamespace(width=640))
        bar.pack_forget.assert_called_once_with()
        canvas.itemconfigure.assert_called_once()
        inner.winfo_reqheight.return_value = 500
        fit()
        self.assertEqual(bar.pack.call_count, 2)
        self.assertEqual(canvas.configure.call_args, mock.call(scrollregion=(0, 0, 1, 508)))
        resize(types.SimpleNamespace(width=650))
        self.assertEqual(canvas.itemconfigure.call_args, mock.call(42, width=650))

    def test_custom_drag_coalesces_bursts_and_applies_release_position(self):
        root = mock.Mock()
        root.after.return_value = 'move'
        motion = types.SimpleNamespace(paused=True)
        chrome = launcher.WindowChrome(types.SimpleNamespace(root=root, motion=motion))
        chrome.grab = (10, 20)

        def at(x, y):
            return types.SimpleNamespace(x_root=x, y_root=y)

        for i in range(100):
            chrome.drag_move(at(100 + i, 200 + i))
        root.after.assert_called_once_with(8, chrome.flush_drag)
        root.geometry.assert_not_called()
        chrome.flush_drag()
        root.geometry.assert_called_once_with('+189+279')

        chrome.drag_move(at(201, 301))
        chrome.drag_end(at(205, 305))
        root.after_cancel.assert_called_once_with('move')
        self.assertEqual(root.geometry.call_args_list, [mock.call('+189+279'), mock.call('+195+285')])
        self.assertFalse(motion.paused)
        chrome.flush_drag()  # a stale callback cannot move a released window
        self.assertEqual(root.geometry.call_count, 2)

    def test_same_rendered_hover_colors_do_not_write_to_tk_twice(self):
        corner = mock.Mock()
        card = types.SimpleNamespace(configure=mock.Mock(), corners=[corner])
        window = types.SimpleNamespace(tk=types.SimpleNamespace(TclError=RuntimeError))
        launcher.Launcher.light(window, card, 0.0)
        launcher.Launcher.light(window, card, 0.000001)
        self.assertEqual(card.glow, 0.000001)
        card.configure.assert_called_once()
        corner.itemconfigure.assert_called_once()
        launcher.Launcher.light(window, card, 1.0)
        self.assertEqual(card.configure.call_count, 2)
        self.assertEqual(corner.itemconfigure.call_count, 2)

    def test_log_burst_is_batched_without_reordering_lines_or_exit(self):
        events = []
        window = types.SimpleNamespace(
            ui_calls=queue.Queue(), output=queue.Queue(), root=mock.Mock(), drain_output=mock.Mock(),
            append=lambda text: events.append(('log', text)),
            coop_watch_line=lambda text: events.append(('line', text)),
            job=None, set_running=mock.Mock(), refresh_status=mock.Mock(),
            coop_game_ended=mock.Mock(), say_start_crash=lambda code: events.append(('exit', code)),
        )
        lines = [f'fixture line {i}\n' for i in range(100)]
        for line in lines:
            window.output.put(line)
        window.output.put((7,))
        with mock.patch.object(launcher.time, 'perf_counter', return_value=1.0), \
                mock.patch.object(launcher, 'game_is_up', return_value=False), \
                mock.patch.object(launcher, '_', side_effect=lambda english, *_: english):
            launcher.Launcher.drain_output(window)
        self.assertEqual(events[:100], [('line', text) for text in lines])
        self.assertEqual(events[100:], [
            ('log', ''.join(lines)),
            ('log', '\n— the game exited (code 7) —\n'),
            ('exit', 7),
        ])
        window.root.after.assert_called_once_with(100, window.drain_output)

    def test_callback_backlog_yields_to_window_events(self):
        window = types.SimpleNamespace(ui_calls=queue.Queue(), output=queue.Queue(),
                                       root=mock.Mock(), drain_output=mock.Mock())
        callbacks = [mock.Mock(), mock.Mock()]
        for callback in callbacks:
            window.ui_calls.put(callback)
        # Starting time, first callback allowed, then its work consumes the whole slice.
        with mock.patch.object(launcher.time, 'perf_counter', side_effect=[1.0, 1.0, 1.007]):
            launcher.Launcher.drain_output(window)
        callbacks[0].assert_called_once_with()
        callbacks[1].assert_not_called()
        window.root.after.assert_called_once_with(16, window.drain_output)


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


if __name__ == '__main__':
    unittest.main()
