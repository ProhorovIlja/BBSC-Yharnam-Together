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

    def test_custom_resize_coalesces_motion_and_flushes_release(self):
        root = mock.Mock()
        root.winfo_width.return_value = 800
        root.winfo_height.return_value = 600
        root.minsize.return_value = (640, 480)
        root.after.return_value = 'resize'
        with mock.patch.dict(launcher.os.environ, {'BB_LAUNCHER_CUSTOM_CHROME': '1'}):
            chrome = launcher.WindowChrome(types.SimpleNamespace(root=root))
        point = lambda x, y: types.SimpleNamespace(x_root=x, y_root=y)
        chrome.resize_start(point(400, 300))
        for x in range(410, 510):
            chrome.resize_move(point(x, 330))
        root.after.assert_called_once()
        root.geometry.assert_not_called()
        root.after.call_args.args[1]()
        root.geometry.assert_called_once_with('909x630')
        chrome.resize_move(point(600, 340))
        chrome.resize_end(point(0, 0))
        root.after_cancel.assert_called_once_with('resize')
        self.assertEqual(root.geometry.call_args_list, [mock.call('909x630'), mock.call('640x480')])
        chrome.resize_move(point(700, 400))
        self.assertEqual(root.after.call_count, 2)

    def test_custom_resize_cancel_leaves_geometry_untouched(self):
        root = mock.Mock()
        root.winfo_width.return_value = 800
        root.winfo_height.return_value = 600
        root.after.return_value = 'resize'
        with mock.patch.dict(launcher.os.environ, {'BB_LAUNCHER_CUSTOM_CHROME': '1'}):
            chrome = launcher.WindowChrome(types.SimpleNamespace(root=root))
        point = types.SimpleNamespace(x_root=0, y_root=0)
        chrome.resize_start(point)
        chrome.resize_move(types.SimpleNamespace(x_root=50, y_root=50))
        pending = root.after.call_args.args[1]
        chrome.resize_end()
        pending()  # An obsolete scheduled callback cannot write geometry.
        root.after_cancel.assert_called_once_with('resize')
        root.geometry.assert_not_called()

    def test_status_line_skips_identical_text_spinner_and_wrap_work(self):
        line = launcher.StatusLine.__new__(launcher.StatusLine)
        line.ui = types.SimpleNamespace(px=lambda n: n)
        line.text, line.glyph, line.spinner = mock.Mock(), mock.Mock(), mock.Mock()
        line._text_state = line._glyph_state = None
        line._busy = False
        line.wraplength = 240
        for width in (244, 244, 500, 500):
            line.wrap(types.SimpleNamespace(width=width))
        line.text.configure.assert_called_once_with(wraplength=496)
        line.text.configure.reset_mock()
        for _ in range(30):
            line.set('Checking', busy=True)
        line.text.configure.assert_called_once_with(text='Checking', fg=launcher.TEXT)
        line.spinner.start.assert_called_once()
        line.glyph.pack_forget.assert_called_once()
        for _ in range(30):
            line.set('Ready')
        line.spinner.stop.assert_called_once()
        line.glyph.pack.assert_called_once()
        line.glyph.configure.assert_called_once()
        self.assertEqual(line.text.configure.call_count, 2)

    def test_banner_uses_latest_width_and_cancels_pending_paint_on_destroy(self):
        header = mock.Mock(painted_width=0)
        header.after.return_value = 'paint'
        app = types.SimpleNamespace(paint_street=mock.Mock())
        launcher.Launcher.bind_street_resize(app, header)
        resize, destroy = (call.args[1] for call in header.bind.call_args_list)
        for width in range(640, 740):
            resize(types.SimpleNamespace(width=width))
        header.after.assert_called_once()
        delay, paint = header.after.call_args.args
        self.assertEqual(delay, 16)
        app.paint_street.assert_not_called()
        paint()
        app.paint_street.assert_called_once_with(header, 739)

        header.painted_width = 739
        resize(types.SimpleNamespace(width=739))
        header.after.assert_called_once()
        resize(types.SimpleNamespace(width=740))
        destroy(types.SimpleNamespace(widget=object()))
        header.after_cancel.assert_not_called()
        destroy(types.SimpleNamespace(widget=header))
        header.after_cancel.assert_called_once_with('paint')

    def test_wrapped_labels_skip_identical_effective_widths(self):
        label = mock.Mock()
        app = types.SimpleNamespace(px=lambda n: n, label=mock.Mock(return_value=label))
        self.assertIs(launcher.Launcher.flow(app, object(), 'News'), label)
        configure = label.bind.call_args.args[1]
        for width in range(1, 85):
            configure(types.SimpleNamespace(width=width))
        for _ in range(100):
            configure(types.SimpleNamespace(width=640))
        configure(types.SimpleNamespace(width=650))
        self.assertEqual(label.configure.call_args_list, [
            mock.call(wraplength=80), mock.call(wraplength=636), mock.call(wraplength=646),
        ])

    def test_rebuilt_banner_reuses_only_last_photo_for_same_art_and_size(self):
        art = object()
        photo = object()
        app = types.SimpleNamespace(street_art=art, _street_photo_cache=None,
                                    render_street_photo=mock.Mock(return_value=photo))
        def banner(height):
            header = mock.Mock(painted_width=0)
            header.cget.return_value = str(height)
            return header

        old, rebuilt, taller, wider, back = (banner(h) for h in (180, 180, 190, 190, 190))
        launcher.Launcher.paint_street(app, old, 640)
        launcher.Launcher.paint_street(app, rebuilt, 640)
        app.render_street_photo.assert_called_once_with(art, 640, 180)
        rebuilt.itemconfigure.assert_called_once_with(rebuilt.picture, image=photo)
        launcher.Launcher.paint_street(app, taller, 640)
        launcher.Launcher.paint_street(app, wider, 650)
        launcher.Launcher.paint_street(app, back, 640)
        self.assertEqual(app.render_street_photo.call_args_list, [
            mock.call(art, 640, 180), mock.call(art, 640, 190),
            mock.call(art, 650, 190), mock.call(art, 640, 190),
        ])
        app.street_art = replacement = object()
        launcher.Launcher.paint_street(app, banner(190), 640)
        app.render_street_photo.assert_called_with(replacement, 640, 190)

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
            cancel_ready_close=mock.Mock(), coop_game_ended=mock.Mock(), say_start_crash=lambda code: events.append(('exit', code)),
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

    def test_status_refresh_uses_one_game_lookup_and_stops_after_first_save(self):
        def saves():
            yield Path('SPRJ0005')
            self.fail('status does not need to enumerate the remaining saves')

        window = types.SimpleNamespace(
            coop_game_info=mock.Mock(return_value=('fixture', '01.08')),
            var=mock.Mock(return_value=mock.Mock(get=mock.Mock(return_value=''))),
            checks={k: mock.Mock() for k in ('game', 'saves', 'gpu', 'fsr4')},
            gpu_text='GPU', gpu_checking=False, upscaler_notice=None,
            process=None, installing=False, play_button=mock.Mock(), status=mock.Mock(),
        )
        window.summary = lambda info: launcher.Launcher.summary(window, info)
        with mock.patch.object(launcher, 'COOP_INSTALL', True), \
                mock.patch.object(launcher, 'fsr4_missing', return_value=False), \
                mock.patch.object(type(Path()), 'glob', return_value=saves()), \
                mock.patch.object(launcher, '_', side_effect=lambda english, *_: english):
            launcher.Launcher.refresh_status(window)
        window.coop_game_info.assert_called_once_with()
        self.assertIn('Saves found', window.checks['saves'].set.call_args.args[0])
        self.assertTrue(window.status.configure.call_args.kwargs['text'].startswith('30 FPS'))

    def test_new_launch_resets_readiness_and_fences_stale_close(self):
        old, current = object(), object()
        window = types.SimpleNamespace(
            process=current, root=mock.Mock(), coop_release_server=mock.Mock(),
            output_ready=True, close_on_ready_job='old',
        )
        window.cancel_ready_close = lambda: launcher.Launcher.cancel_ready_close(window)
        launcher.Launcher.reset_run_output(window, {})
        window.root.after_cancel.assert_called_once_with('old')
        self.assertFalse(window.output_ready)
        self.assertFalse(window.run_up)
        launcher.Launcher.close_after_ready(window, current)  # canceled callback
        window.close_on_ready_job = 'current'
        launcher.Launcher.close_after_ready(window, old)  # from previous game
        window.root.destroy.assert_not_called()
        launcher.Launcher.close_after_ready(window, current)
        window.coop_release_server.assert_called_once_with()
        window.root.destroy.assert_called_once_with()

    def test_game_ready_markers_update_once_per_launch_phase(self):
        window = types.SimpleNamespace(
            ui_calls=queue.Queue(), output=queue.Queue(), root=mock.Mock(), drain_output=mock.Mock(),
            append=mock.Mock(), coop_watch_line=mock.Mock(), set_running=mock.Mock(),
            status=mock.Mock(), app={}, output_ready=False, run_up=False,
        )
        lines = [*launcher.GAME_UP_LINES, 'restarting through run.py', *launcher.GAME_UP_LINES]
        # FollowLog may deliver the entire ready/restart/ready sequence at once.
        window.output.put(''.join(line + '\n' for line in lines))
        with mock.patch.object(launcher.time, 'perf_counter', return_value=1):
            launcher.Launcher.drain_output(window)
        self.assertEqual(window.set_running.call_args_list, [
            mock.call(True), mock.call(True, preparing=True), mock.call(True),
        ])
        self.assertEqual(window.status.configure.call_count, 3)
        self.assertTrue(window.run_up)
        self.assertTrue(window.output_ready)
        window.append.assert_called_once_with(''.join(line + '\n' for line in lines))

    def test_failed_worker_callback_does_not_stop_output_polling(self):
        for error in (ValueError('invalid result'), queue.Empty()):
            with self.subTest(error=type(error)):
                window = types.SimpleNamespace(
                    ui_calls=queue.Queue(), output=queue.Queue(), root=mock.Mock(),
                    drain_output=mock.Mock(), append=mock.Mock(), coop_watch_line=mock.Mock(),
                )
                following = mock.Mock()
                window.ui_calls.put(mock.Mock(side_effect=error))
                window.ui_calls.put(following)
                window.output.put('ready\n')
                with mock.patch.object(launcher.time, 'perf_counter', return_value=1), \
                        mock.patch.object(launcher, 'game_is_up', return_value=False):
                    launcher.Launcher.drain_output(window)
                following.assert_called_once_with()
                report = window.root.report_callback_exception
                report.assert_called_once()
                self.assertIs(report.call_args.args[1], error)
                window.append.assert_called_once_with('ready\n')
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