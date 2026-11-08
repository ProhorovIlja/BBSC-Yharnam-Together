# Ultimate B07: prevent delayed worker snapshots from overwriting newer world progress

**Status:** Draft C++ source candidate, no complete game build or real save tests.

## Root cause in the Yharnam Together 1.4.0-derived code

`SaveGuestWorldChanges()` copied the guest's world flags and normally posted a file write to the long-lived `CoopWorker`. When `Post(write)` returns false (eight pending jobs), or `OffMainPart::WorldFile` is disabled, it executes the **newer** snapshot synchronously. An **older** already-queued closure could execute *after* the direct write, replacing the new data with older state. B06 protected each individual file replacement against partial/truncated writes, but it did **not** prevent this write-order inversion.

The worker's normal FIFO does not help when synchronous fallback bypasses its queue. This is an actual source-order hazard, not a demonstrated diagnosis of a historical screenshot.

## B07 patch

- `GuestWorldWriteStateFor(path)` returns stable state for each individual per-slot guest-world file. A small map-index mutex is held only for lookup/creation, **not** during disk writes.
- Every snapshot is assigned a monotonically increasing revision **before** it is posted. The worker and synchronous fallback share the exact same revision and closure.
- `CommitLatestGuestWorldSnapshot` serializes each file's commit under its own mutex and skips stale revisions; an older closure can no longer rename over a more recent committed world snapshot.
- Two different save slots retain independent revision state, so changing character does not discard a previous slot's pending write solely because another slot changed.
- The B06 staged-file helper, B05 per-character pickup reset, and B04 deferred reward-owner rules remain in place.

## Verification

`tools/re/tests/test_guest_world_write_order.py` compiles the **actual C++ commit fence and B06 staged writer** against synthetic files, including delayed old callback after a newer sync commit, multiple older callbacks, separate slots, empty world and failing file replacement. The CI reruns B06 filesystem fault-injection plus B05, B04, B03, B02, B01 tests. No game assets, personal files, live server, launcher build or full client compilation.

## Boundaries and open risks

The latest **pending** job can still be lost if the game exits abruptly before the worker processes it; the co-op worker deliberately lives until process termination. B07 prevents stale **overwrites**, not guaranteed on-exit flushing, retry after latest I/O failure, disk fsync/power-loss durability, or transactions spanning multiple files. The queue-full fallback can still do synchronous disk IO (as before), so tail-latency behavior needs measurement on the real rig.

The separate [Supermedo 1.9.8.3](https://github.com/Supermedo/bloodborne_pc/releases/tag/windows-v1.9.8.3) fix of guest personal-world ownership is **not claimed as imported**. Public release ZIP metadata and SourceForge archive listings are confirmed; direct source ZIP bytes were not accessible in this environment. Do not transplant guessed CLS code into YT 1.4.0.

**Release gates:** private Bloodborne 1.09 saves, 2/3/5 players, slot switches, late joins, team travel, restart, NPC/Chalice/boss states, and Link4-compatible server. Windows compiler PR #31 and original droogie/BBHost benchmark remain open. P0 [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) and [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) remain open. Fornex and live saves remain untouched.
