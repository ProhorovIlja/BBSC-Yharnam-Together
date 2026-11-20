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

    def test_live_log_respects_scroll_position_and_keeps_the_line_cap(self):
        for position, follow in [((0.2, 0.5), False), ((0.8, 1.0), True)]:
            with self.subTest(position=position):
                log = mock.Mock()
                log.yview.return_value = position
                log.index.return_value = f'{launcher.MAX_LOG_LINES + 4}.7'
                launcher.Launcher.append(types.SimpleNamespace(log=log), 'new output\n')
                log.insert.assert_called_once_with('end', 'new output\n')
                log.delete.assert_called_once_with('1.0', '4.0')
                self.assertEqual(log.see.call_args_list, [mock.call('end')] if follow else [])
                self.assertEqual(log.configure.call_args_list, [
                    mock.call(state='normal'), mock.call(state='disabled'),
                ])

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

    def test_ready_marker_after_refusal_cannot_arm_close_on_play(self):
        window = types.SimpleNamespace(
            ui_calls=queue.Queue(), output=queue.Queue(), root=mock.Mock(),
            drain_output=mock.Mock(), append=mock.Mock(), status=mock.Mock(),
            app={'close_on_play': True}, process=object(), close_on_ready_job=None,
            output_ready=False, set_running=mock.Mock(), schedule_ready_close=mock.Mock(),
        )
        refusal = launcher.bbport_coop.REFUSED_LINE + 'account: sign in again\n'
        ready = next(iter(launcher.GAME_UP_LINES)) + '\n'
        def watch(line):
            if line == refusal:
                window.coop_new_id = 'give_up_account'
        window.coop_watch_line = watch
        window.output.put(refusal + ready)
        with mock.patch.object(launcher.time, 'perf_counter', return_value=1):
            launcher.Launcher.drain_output(window)
        window.append.assert_called_once_with(refusal + ready)
        window.schedule_ready_close.assert_not_called()
        window.set_running.assert_not_called()
        window.status.configure.assert_not_called()

    def test_coop_play_log_preparation_failure_clears_preparing(self):
        window = types.SimpleNamespace(
            coop_busy=True, play_button=mock.Mock(), set_running=mock.Mock(),
            status=mock.Mock(), process=None,
        )
        with mock.patch.object(launcher.bbport_coop, 'rotate_logs',
                               side_effect=PermissionError('log locked')), \
                mock.patch.object(launcher, 'start_game') as start, \
                mock.patch.object(launcher, '_', side_effect=lambda english, *_: english):
            launcher.Launcher.coop_start_game(window, {}, None, None, '')
        self.assertFalse(window.coop_busy)
        window.play_button.configure.assert_called_once_with(state='normal')
        window.set_running.assert_called_once_with(False)
        window.status.configure.assert_called_once_with(
            text='Could not prepare the game log: log locked', fg=launcher.BAD)
        start.assert_not_called()

    def test_stop_during_start_runs_after_start_and_suppresses_upnp(self):
        methods = launcher.Launcher
        window = types.SimpleNamespace(
            coop={'host_ip': '127.0.0.1'}, server_starting=False, server_stopping=False,
            server_stop_pending=False, server_status_epoch=0, coop_upnp=None, coop_help=None,
            coop_server_line=mock.Mock(), ui_calls=queue.Queue(),
            coop_firewall=mock.Mock(), coop_say=mock.Mock(), coop_open_router=mock.Mock(),
        )
        window.coop_stop_servers = lambda: methods.coop_stop_servers(window)
        jobs = []

        def thread(*, target, daemon):
            return types.SimpleNamespace(start=lambda: jobs.append(target))

        with mock.patch.object(launcher.threading, 'Thread', side_effect=thread), (
                mock.patch.multiple(launcher.bbport_coop, valid_ip=mock.Mock(return_value=True),
                                    is_this_pc=mock.Mock(return_value=True),
                                    start_servers=mock.Mock(return_value=[]),
                                    stop_servers=mock.Mock(return_value=1),
                                    server_state=mock.Mock(return_value='running'),
                                    wants_router=mock.Mock(return_value=True))), (
                mock.patch.object(launcher.bbport_upnp, 'close_ports')), (
                mock.patch.object(launcher, '_', side_effect=lambda english, *_: english)):
            methods.coop_start_servers(window)
            window.coop_stop_servers()
            window.coop_stop_servers()
            self.assertEqual(len(jobs), 1)
            jobs[0]()
            self.assertTrue(window.server_starting)
            window.ui_calls.get_nowait()()
            self.assertFalse(window.server_starting)
            self.assertTrue(window.server_stopping)
            methods.coop_start_servers(window)
            self.assertEqual(len(jobs), 2)
            jobs[1]()
            window.ui_calls.get_nowait()()
            self.assertFalse(window.server_stopping)
            window.coop_open_router.assert_not_called()
            launcher.bbport_coop.stop_servers.assert_called_once_with(launcher.PORT_DIR)
            window.coop_server_line.configure.assert_called_with(text='Stopped (1)', fg=launcher.MUTED)

    def test_server_probe_error_replaces_status_but_stale_result_does_not(self):
        window = types.SimpleNamespace(
            coop={}, server_starting=False, server_stopping=False, server_checking=True,
            server_status_epoch=1, coop_server_line=mock.Mock(), ui_calls=queue.Queue(),
        )
        with mock.patch.object(launcher, '_', side_effect=lambda english, *_: english):
            with mock.patch.object(launcher.bbport_coop, 'server_state', return_value='running'):
                launcher.Launcher.coop_check_server(window, window.server_status_epoch)
            window.server_status_epoch += 1
            window.ui_calls.get_nowait()()
            window.coop_server_line.configure.assert_not_called()
            window.server_checking = True
            with mock.patch.object(launcher.bbport_coop, 'server_state', side_effect=OSError('probe')):
                launcher.Launcher.coop_check_server(window, window.server_status_epoch)
            window.ui_calls.get_nowait()()
        self.assertFalse(window.server_checking)
        window.coop_server_line.configure.assert_called_once_with(
            text='Status unavailable', fg=launcher.CAUTION)

    def test_server_watch_captures_epoch_when_worker_is_scheduled(self):
        methods = launcher.Launcher
        window = types.SimpleNamespace(
            coop={}, server_starting=False, server_stopping=False, server_checking=False,
            server_status_epoch=1, coop_server_line=mock.Mock(), ui_calls=queue.Queue(),
            root=mock.Mock(), coop_watch_server=mock.Mock(),
        )
        window.coop_check_server = lambda *args: methods.coop_check_server(window, *args)
        with mock.patch.object(launcher.threading, 'Thread') as thread:
            methods.coop_watch_server(window)
        # A newer operation can finish before the original thread even starts.
        window.server_status_epoch = 3
        scheduled = thread.call_args.kwargs
        with mock.patch.object(launcher.bbport_coop, 'server_state', return_value='running'):
            scheduled['target'](*scheduled.get('args', ()))
        window.ui_calls.get_nowait()()
        self.assertFalse(window.server_checking)
        window.coop_server_line.configure.assert_not_called()

    def test_server_controls_recover_when_worker_cannot_start(self):
        methods = launcher.Launcher
        window = types.SimpleNamespace(
            coop={'host_ip': '127.0.0.1'}, server_starting=False, server_stopping=False,
            server_stop_pending=False, server_status_epoch=0, server_checking=False,
            coop_server_line=mock.Mock(), root=mock.Mock(), coop_watch_server=mock.Mock(),
            coop_check_server=mock.Mock(),
        )
        with mock.patch.object(launcher.threading, 'Thread') as thread, (
                mock.patch.multiple(launcher.bbport_coop, valid_ip=mock.Mock(return_value=True),
                                    is_this_pc=mock.Mock(return_value=True))), (
                mock.patch.object(launcher, '_', side_effect=lambda english, *_: english)):
            thread.return_value.start.side_effect = RuntimeError('worker unavailable')
            methods.coop_start_servers(window)
            self.assertFalse(window.server_starting)
            window.coop_server_line.configure.assert_called_with(
                text='Could not start server: worker unavailable', fg=launcher.BAD)
            methods.coop_stop_servers(window)
            self.assertFalse(window.server_stopping)
            window.coop_server_line.configure.assert_called_with(
                text='Could not stop server: worker unavailable', fg=launcher.BAD)
            methods.coop_watch_server(window)
        self.assertFalse(window.server_checking)
        window.coop_server_line.configure.assert_called_with(
            text='Status unavailable', fg=launcher.CAUTION)
        window.root.after.assert_called_once_with(launcher.SERVER_CHECK_MS, window.coop_watch_server)

    def test_start_server_probe_error_clears_starting_and_does_not_open_router(self):
        window = types.SimpleNamespace(
            coop={'host_ip': '127.0.0.1'}, server_starting=False, server_stopping=False,
            server_stop_pending=False, server_status_epoch=0,
            coop_server_line=mock.Mock(), ui_calls=queue.Queue(),
            coop_firewall=mock.Mock(), coop_say=mock.Mock(), coop_open_router=mock.Mock(),
        )
        jobs = []
        def thread(*, target, daemon):
            return types.SimpleNamespace(start=lambda: jobs.append(target))
        with mock.patch.object(launcher.threading, 'Thread', side_effect=thread), \
                mock.patch.object(launcher.bbport_coop, 'valid_ip', return_value=True), \
                mock.patch.object(launcher.bbport_coop, 'is_this_pc', return_value=True), \
                mock.patch.object(launcher.bbport_coop, 'start_servers', return_value=[]), \
                mock.patch.object(launcher.bbport_coop, 'server_state', side_effect=OSError('probe failed')), \
                mock.patch.object(launcher, '_', side_effect=lambda english, *_: english):
            launcher.Launcher.coop_start_servers(window)
            launcher.Launcher.coop_start_servers(window)
            self.assertEqual(len(jobs), 1)
            jobs[0]()
            window.ui_calls.get_nowait()()
        self.assertFalse(window.server_starting)
        window.coop_open_router.assert_not_called()
        window.coop_server_line.configure.assert_called_with(
            text='Status unavailable', fg=launcher.CAUTION)
        window.coop_say.assert_called_once_with(
            'Could not check local server status: probe failed', launcher.MUTED)

    def test_manual_stop_wins_over_already_scheduled_account_retry(self):
        window = types.SimpleNamespace(
            coop_new_id='retry', coop_playing=object(), installing=False, job=mock.Mock(),
            cancel_ready_close=mock.Mock(), coop_start_game=mock.Mock(),
        )
        launcher.Launcher.stop(window)
        launcher.Launcher.coop_game_ended(window)
        self.assertIsNone(window.coop_new_id)
        self.assertIsNone(window.coop_playing)
        window.coop_start_game.assert_not_called()

    def test_manual_stop_cancels_close_and_late_ready_cannot_rearm(self):
        window = types.SimpleNamespace(
            ui_calls=queue.Queue(), output=queue.Queue(), root=mock.Mock(),
            drain_output=mock.Mock(), append=mock.Mock(), status=mock.Mock(),
            app={'close_on_play': True}, process=object(), close_on_ready_job='timer',
            output_ready=False, set_running=mock.Mock(), installing=False,
            job=mock.Mock(), coop_watch_line=mock.Mock(), schedule_ready_close=mock.Mock(),
        )
        window.cancel_ready_close = lambda: launcher.Launcher.cancel_ready_close(window)
        launcher.Launcher.stop(window)
        window.root.after_cancel.assert_called_once_with('timer')
        window.job.terminate.assert_called_once_with()
        ready = next(iter(launcher.GAME_UP_LINES)) + '\n'
        refusal = launcher.bbport_coop.REFUSED_LINE + 'fixture late refusal\n'
        window.output.put('late log\n')
        window.output.put(ready + refusal)
        with mock.patch.object(launcher.time, 'perf_counter', return_value=1):
            launcher.Launcher.drain_output(window)
        window.append.assert_called_once_with('late log\n' + ready + refusal)
        window.coop_watch_line.assert_not_called()
        window.schedule_ready_close.assert_not_called()
        window.status.configure.assert_not_called()

    def test_server_key_mismatch_cancels_close_and_survives_ready_marker(self):
        for before_ready in (True, False):
            with self.subTest(before_ready=before_ready):
                window = types.SimpleNamespace(
                    ui_calls=queue.Queue(), output=queue.Queue(), root=mock.Mock(),
                    drain_output=mock.Mock(), append=mock.Mock(), status=mock.Mock(),
                    app={'close_on_play': True}, process=object(), close_on_ready_job=None,
                    output_ready=False, set_running=mock.Mock(), coop_playing=object(),
                )
                window.cancel_ready_close = lambda: launcher.Launcher.cancel_ready_close(window)
                window.schedule_ready_close = lambda: setattr(window, 'close_on_ready_job', 'timer')
                window.coop_watch_line = lambda line: launcher.Launcher.coop_watch_line(window, line)
                mismatch = launcher.bbport_coop.OTHER_KEY_LINE + '\n'
                ready = next(iter(launcher.GAME_UP_LINES)) + '\n'
                window.output.put(mismatch + ready if before_ready else ready + mismatch + ready)
                with mock.patch.object(launcher.time, 'perf_counter', return_value=1), \
                        mock.patch.object(launcher.bbport_coop, 'other_key', side_effect=lambda line: line == mismatch), \
                        mock.patch.object(launcher, '_', side_effect=lambda english, *_: english):
                    launcher.Launcher.drain_output(window)
                self.assertTrue(window.run_up)
                self.assertTrue(window.coop_key_mismatch)
                self.assertIsNone(window.close_on_ready_job)
                self.assertEqual(window.status.configure.call_args.kwargs['fg'], launcher.BAD)
                self.assertEqual(window.root.after_cancel.call_count, 0 if before_ready else 1)
                launcher.Launcher.reset_run_output(window, {})
                self.assertFalse(window.coop_key_mismatch)

    def test_sign_in_refusal_survives_post_exit_status_refresh(self):
        window = types.SimpleNamespace(
            ui_calls=queue.Queue(), output=queue.Queue(), root=mock.Mock(),
            drain_output=mock.Mock(), append=mock.Mock(), job=None, status=mock.Mock(),
            cancel_ready_close=mock.Mock(), set_running=mock.Mock(),
            coop_new_id='give_up_account', coop_playing=object(), say_start_crash=mock.Mock(),
        )
        window.refresh_status = lambda: window.status.configure(text='Ready')
        window.coop_game_ended = lambda: launcher.Launcher.coop_game_ended(window)
        window.show_coop_sign_in_required = lambda: launcher.Launcher.show_coop_sign_in_required(window)
        window.output.put((7,))
        with mock.patch.object(launcher.time, 'perf_counter', return_value=1), \
                mock.patch.object(launcher, '_', side_effect=lambda english, *_: english):
            launcher.Launcher.drain_output(window)
        self.assertEqual(window.status.configure.call_args_list, [
            mock.call(text='Ready'),
            mock.call(text='Sign in again (Co-op settings, the first step).', fg=launcher.BAD),
        ])
        self.assertIsNone(window.coop_new_id)
        self.assertIsNone(window.coop_playing)
        window.say_start_crash.assert_not_called()

    def test_account_recovery_exit_does_not_show_startup_crash(self):
        for reason in ('retry', 'give_up', 'give_up_account'):
            with self.subTest(reason=reason):
                window = types.SimpleNamespace(
                    ui_calls=queue.Queue(), output=queue.Queue(), root=mock.Mock(),
                    drain_output=mock.Mock(), append=mock.Mock(), job=None,
                    cancel_ready_close=mock.Mock(), set_running=mock.Mock(),
                    refresh_status=mock.Mock(), coop_new_id=reason,
                    coop_game_ended=mock.Mock(), say_start_crash=mock.Mock(),
                )
                window.output.put((7,))
                with mock.patch.object(launcher.time, 'perf_counter', return_value=1):
                    launcher.Launcher.drain_output(window)
                window.coop_game_ended.assert_called_once_with()
                window.say_start_crash.assert_not_called()

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
        launcher.Launcher.close_after_ready(window, current, 'old')  # canceled callback
        window.close_on_ready_job = 'current'
        launcher.Launcher.close_after_ready(window, old, 'current')  # from previous game
        window.root.destroy.assert_not_called()
        launcher.Launcher.close_after_ready(window, current, 'old')  # same process, obsolete timer
        window.root.destroy.assert_not_called()
        launcher.Launcher.close_after_ready(window, current, 'current')
        window.coop_release_server.assert_called_once_with()
        window.root.destroy.assert_called_once_with()

    def test_coop_key_and_refusal_in_one_log_read_both_reach_the_watcher(self):
        window = types.SimpleNamespace(
            ui_calls=queue.Queue(), output=queue.Queue(), root=mock.Mock(),
            drain_output=mock.Mock(), append=mock.Mock(), coop_watch_line=mock.Mock(),
        )
        key = launcher.bbport_coop.LEARNED_KEY_LINE + 'a' * 64 + '\n'
        refusal = launcher.bbport_coop.REFUSED_LINE + 'account: sign in again\n'
        window.output.put(key + refusal)
        with mock.patch.object(launcher.time, 'perf_counter', return_value=1):
            launcher.Launcher.drain_output(window)
        self.assertEqual(window.coop_watch_line.call_args_list, [mock.call(key), mock.call(refusal)])
        window.append.assert_called_once_with(key + refusal)

    def test_game_ready_markers_update_once_per_launch_phase(self):
        window = types.SimpleNamespace(
            ui_calls=queue.Queue(), output=queue.Queue(), root=mock.Mock(), drain_output=mock.Mock(),
            append=mock.Mock(), coop_watch_line=mock.Mock(), set_running=mock.Mock(),
            status=mock.Mock(), app={}, output_ready=False, run_up=False, cancel_ready_close=mock.Mock(),
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
        window.cancel_ready_close.assert_called_once_with()
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