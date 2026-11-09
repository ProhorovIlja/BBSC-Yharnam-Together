"""Real Windows Tk lifecycle regressions for the production launcher timers.

The historical GUI test emitted Tcl "invalid command name ...drain_output"
and "...back" after its window was destroyed. Tests run against genuine Tk
after/after_idle/after_cancel and production Launcher/Motion methods, without
starting Bloodborne, opening a connection, or creating any player saves.
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

if sys.platform == "win32":
    import tkinter as tk
    import bbport_launcher_win as launcher


@unittest.skipUnless(sys.platform == "win32", "requires actual Windows Tk")
class LauncherOwnedAfterLifecycle(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        # Use actual production scheduler and Motion implementation, but avoid
        # spawning the full launcher UI/background status checks in a unit test.
        self.app = launcher.Launcher.__new__(launcher.Launcher)
        self.app.root = self.root
        self.app.tk = tk
        self.app.motion = launcher.Motion(self.root, tk.TclError, False)
        self.app._pending_after = set()
        self.app._closing = False
        self.app.installing = False
        self.app.coop_flush = lambda: None
        self.app.collect = lambda: None
        self.root.bind("<Destroy>", self.app._root_destroyed, add="+")

    def tearDown(self):
        if not self.app._closing:
            self.app._stop_after_jobs()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def pending_tcl_timers(self):
        return set(self.root.tk.call("after", "info"))

    def test_destroy_cancels_all_pending_tk_commands_including_idle(self):
        ran = []
        delayed = self.app.after_owned(10_000, lambda: ran.append("output"))
        restored_button = self.app.after_owned(9_000, lambda: ran.append("back"))
        idle = self.app.after_owned(None, lambda: ran.append("idle"))
        self.assertEqual(len(self.app._pending_after), 3)
        self.assertTrue({delayed, restored_button, idle} <= self.pending_tcl_timers())
        # This is an external destroy, not Launcher.close().
        self.root.destroy()
        self.assertTrue(self.app._closing)
        self.assertFalse(self.app._pending_after)
        self.assertFalse({delayed, restored_button, idle} & self.pending_tcl_timers())
        self.root.tk.call("update")
        self.assertEqual(ran, [])

    def test_child_widget_destroy_does_not_close_launcher(self):
        child = tk.Frame(self.root)
        child.destroy()
        self.assertFalse(self.app._closing)
        job = self.app.after_owned(10_000, lambda: None)
        self.assertIn(job, self.pending_tcl_timers())
        self.app.close()
        self.assertTrue(self.app._closing)
        self.assertNotIn(job, self.pending_tcl_timers())

    def test_normal_close_cancels_timers_and_later_scheduling_fails_closed(self):
        scheduled = self.app.after_owned(15_000, lambda: self.fail("late callback"))
        self.app.close()
        self.assertNotIn(scheduled, self.pending_tcl_timers())
        self.assertIsNone(self.app.after_owned(1, lambda: self.fail("post-close")))
        self.assertFalse(self.app._pending_after)
        self.app._stop_after_jobs()  # idempotent teardown

    def test_completed_callback_does_not_leak_registration(self):
        events = []
        job = self.app.after_owned(None, lambda: events.append("done"))
        self.assertIn(job, self.app._pending_after)
        self.root.update()
        self.assertEqual(events, ["done"])
        self.assertNotIn(job, self.app._pending_after)
        late = self.app.after_owned(10_000, lambda: None)
        self.root.destroy()
        self.assertNotIn(late, self.pending_tcl_timers())

    def test_motion_tick_is_canceled_on_destroy_without_surviving_tcl_command(self):
        self.app.motion.enabled = True
        self.app.motion.loop("banner", 33, lambda _at: None)
        tick = self.app.motion.job
        self.assertIsNotNone(tick)
        self.assertIn(tick, self.pending_tcl_timers())
        self.root.destroy()
        self.assertNotIn(tick, self.pending_tcl_timers())
        self.assertIsNone(self.app.motion.job)
        self.assertFalse(self.app.motion.enabled)
        self.assertFalse(self.app.motion.loops)
        self.assertFalse(self.app.motion.tweens)


if __name__ == "__main__":
    unittest.main()
