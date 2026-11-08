# Ultimate B08: background retry of the newest failed guest-world snapshot

**Status:** experimental production-source candidate on top of B07 / PR #39. No complete client/server/launcher build and no player-save testing.

## Source-level defect

B06 avoids truncating existing per-character world metadata when a disk write fails. B07 prevents a delayed worker callback from overwriting a newer revision. But neither retained a **latest snapshot that failed to commit**. After a temporary disk-lock or full-disk event the old metadata remained intact, but a new world flag earned during that period could be missing after restart unless another game event caused a new write.

## B08 changes

- The existing per-file B07 `GuestWorldWriteState` now retains **only the latest failed snapshot**, tagged with its revision. A later successful write clears the failure; when the revision has advanced, an earlier failed snapshot is discarded as stale.
- An idle callback on the existing `CoopWorker` calls `RetryFailedGuestWorldWritesOnWorker` after reading the existing `coop-offmain.txt` controls. It retries at most **two paths per callback**, with a per-path delay of 2, 4, 8, 16, 32 seconds while the failure persists. Retries run off the game thread and still use B06's temporary-file replacement under B07's per-path commit lock.
- If a synchronous file write fails while `OffMainPart::WorldFile` is disabled, the fallback posts a no-op worker task to ensure that this idle recovery service starts. This does not change the user's off-main setting or add a server packet.
- State lookup copies a short list of path/state pointers under the index lock and never performs disk I/O under that global index lock.

## Verification

`tools/re/tests/test_guest_world_write_retry.py` compiles the **actual production C++** B06 staged writer plus B07/B08 revision/idle retry helpers. Synthetic paths simulate a blocked destination, preservation of old data, backoff, unblocking the path, retry success, stale revision supersession and two separate world files. Source assertions verify the worker is wired correctly.

CI also reruns the B07 newest-wins fixture, B06 atomic metadata replacement, B05 slot baseline, B04 reward owner, B03 readiness, B02 team lamps and B01 source regression. It verifies all source/test Git blobs and only the nine allowed changed paths. No game files, account credentials or private saves are included.

## Explicit limits

This is **not** process-termination durability, system `fsync`, a journaling system or a transaction over multiple files. The deliberately process-lifetime `CoopWorker` may still drop a final in-flight job when the client exits abruptly. Full-disk/antivirus stalls on the worker can delay other off-main tasks, and repeated failures keep one snapshot in memory until another change or recovery; real Windows timing must be measured. A future milestone should test a controlled shutdown flush separately, without blocking the game thread with unbounded I/O.

The separate [Supermedo 1.9.8.3 personal-world fix](https://github.com/Supermedo/bloodborne_pc/releases/tag/windows-v1.9.8.3) has **not** been ported: the GPL engine ZIP is publicly listed but its source contents could not be opened. The original [droogie/BBHost](https://github.com/droogie/bbhost) remains a full alternative runtime to benchmark, not an automatic patch donor.

**Before promotion:** private real Bloodborne 1.09 tests with 2/3/5 hunters, intermittent disk lock and full-disk injection, exit/restart, same-slot character changes, Chalice/DLC/boss/NPC progress, Link4 server/client fingerprints, and full Windows build blocker #31. [P0 #22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) and [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) remain open. No Fornex, live saves, package or installer deployed.
