# Ultimate B22: Windows Tk launcher timer lifecycle and clean close

**2026-11-09.** Cumulative Ultimate B01–B21 playable-source branch. Real B19 Windows C++ compilation was successful, B15 server 12 Docker suites/five synthetic clients passed, and B21 transitive Windows DLL closure synthetic tests passed. B22 addresses a **different observable launcher GUI regression** from [P1 graphics/perf/launcher Issue #25](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/25), not gameplay engine performance.

## Reproduced source problem from earlier authentic Windows GUI CI

Historical [2026-11-08 Windows smoke 42499250350](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42499250350) emitted Tcl callback warnings `invalid command name "...drain_output"` and `"...back"` after a Tk root/test window was torn down. The actual 1.4.0 launcher previously had 13 **bare** `root.after(...)` and one `root.after_idle(...)` schedules inside `Launcher`: output polling every 100ms, game-server status every few seconds, controller polling, pending web UI, update handover, delayed copied-label restore, install hide, game-close timer. `Launcher.close()` previously closed only the animation timer resolution and then destroyed the root, leaving the Tcl `after` callback commands pending. `Motion.close()` also released timeBeginPeriod without canceling its own tick.

This is a concrete cleanup bug in the source, not a proved direct explanation for all user-perceived launcher drag lag or in-game FPS decay.

## Production fix

- `Launcher.after_owned(delay, callback)` wraps each launcher-owned delayed or idle callback and records the genuine Tk `after` ID. Once it fires, the ID is removed. After close, no new timer can be scheduled and pending callbacks are canceled before Tk widgets are destroyed.
- `Launcher._root_destroyed` handles a **direct** `root.destroy()` (used during automatic handover after PLAY, update handoff, or test cleanup) as well as the explicit Close button. Child-widget destruction **must not** close the entire launcher.
- `Motion.close()` cancels its own Tk tick, clears queued animation closures, disables new ticks and releases the process's Windows 1ms timer resolution. It remains idempotent.
- `Launcher.drain_output` and `coop_watch_server` now always reschedule using owned timers. The 2s "Copied" label, controller polling, install hide, and update/launch handover use the same owned lifecycle instead of leaving orphan Tcl callbacks.
- The original close-on-game-ready behavior (only after the graphics window says ready, not during mod or shader preparation) is preserved and its existing mock regression updated for the new timer ownership method.

## Actual tests and acceptance

`bbport/tests/test_launcher_timer_lifetime.py` uses **real Windows Tk** and production `Launcher.after_owned` / `Motion.close` methods, creating a minimal launcher object instead of starting the game. It checks: multiple pending delayed/idle Tk command IDs are truly canceled on direct root destroy; destroying a child widget does not cancel the parent; explicit close is idempotent and prevents new timers; a completed callback is removed from ownership; and the Motion tick is removed with the root.

The dedicated Windows 2022 CPython 3.12 job installs pinned Pillow, compiles Python source, runs that real Tk suite, the inherited `test_launcher_close.py` output/close-on-play regressions and prior `test_launcher_lag.py` co-op card input responsiveness. A short source gate enforces the exact **six-file B21→B22 diff**, pinned production blob hashes, and confirms there are no bare `root.after` calls remaining in the production Launcher outside the scheduling method. It performs **no Windows native game engine rebuild, installer build, live login, game launch or public release**.

## Remaining release gates

One successful Tk close/open fixture is not proof of all UI or performance concerns. Actual clean Windows packaged `BLauncher.exe` needs close/reopen, drag latency/frametime and after-callback warning monitoring with graphics driver and server conditions. B21 package import closure still has to run on the real staged DLLs; then full authenticated five-person Bloodborne 1.09 with isolated saves must pass. Server Fornex and private screenshots/saves are untouched. The genuine no-PS4-ELF native port is a separate project.
