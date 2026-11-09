# Ultimate B28: preserve a guest's personal story flags if the backup write fails

**Date:** 2026-11-09. Accumulated B01–B27 parent branch: `experiment/ultimate-batch-27-world-load-reconnect-20261109`, Draft PR #59. Windows playable edition only; independent fully native port is not being claimed as finished.

## Directly observed source defect

In **real** `emulator/src/core/bloodborne_server_world.cpp`, `ApplyTeamWorldOnLoad` captures the guest's own world blocks into `personal_world_<slot>` before applying the host/team world's event flags via `SetWorldFlags`. But old `WriteWholeFile` returned **void** and only logged rename errors, while never checking open/write/flush/close errors. The guest's original world could fail to persist (disk full, read-only directory, filesystem errors, antivirus denial) and yet the game would continue to overwrite its original boss/door/lamp state with the borrowed host's world. After leaving the team, there may be no reliable personal-world backup to restore. This is a **source-proven data-loss risk**, not a demonstrated on-disk failure for this user's own save.

This is distinct from previously fixed `bloodborne_flags_store.cpp` **guest metadata writer** B06–B09, which had its own atomically staged writer, revision guard, retry and cross-platform tests. B28 targets the separate `personal_world_<slot>` backup made **immediately before team-world adoption**.

## B28 production change

- Introduce dependency-light `emulator/src/core/team_world_file.h` containing `BloodborneCoop::TeamWorldFile::WriteWholeFileChecked(path, text)`. It checks file-open, write, flush, close and destination rename, reports true only after all steps succeeded, cleans the staging file on a failed write/move and leaves the pre-existing destination alone on failure. It never modifies a real save in CI.
- Replace the previously unchecked local `WriteWholeFile` with a bool adapter logging failures, using that **exact production helper**.
- During `ApplyTeamWorldOnLoad`, when new original-world blocks must be captured, `if (!WriteWholeFile(...)) return;` **before** `SetWorldFlags(*store, target)` and **before** `team_world_blocks` or `team_world_taken` update. Leave those flags untouched, retry safely on a later load, and do not replace the player's personal story with host state if original flags were not backed up.
- On an intermediate personal-world restore write failure, return without throwing away the remaining original blocks; retain `personal_world_due` for another load.
- Preserve the existing mechanism for per-slot backup and restoration, including NG+ handling, owner migration, world/quest flags and original co-op wire protocol. No new save format, encryption, network packet or online service change.

## Native checks and source contracts

`emulator/tests/bloodborne/test_team_world_file.cpp` compiles the **actual production header** under Linux and Windows and exercises byte-exact binary save writes, replacement of existing slot file, staging failure preserving old snapshot, absent parent, and retry after obstruction. A source contract checks **real production** call-site ordering and prevents accidental bypass of `SetWorldFlags` gate. CI allows exactly six files from B27 and pins the three production/test blob hashes.

**Not proven:** Windows production game has been launched with a real encrypted Bloodborne save; full-emulator gameplay/release/packaging and real host/guest migration were not performed. Atomic rename does not imply full power-loss durability: filesystem caches and directory fsync are outside B28. A separate longer integration gate must reproduce restore after leave to solo, storage-denial/antivirus locking on Windows, character slots, DLC/NG+ and final save checksum.

## Independent source review

[Supermedo/bloodborne_pc Windows 1.9.8.3](https://github.com/Supermedo/bloodborne_pc/releases/tag/windows-v1.9.8.3), published 2026-11-08, documents a **different** bug where a returning guest's world could inherit the host's bosses/doors/chalice flags. This motivated checking our actual guest-world backup contract, but no source from the Supermedo release archive was imported, and the described Supermedo fix is **not claimed equivalent**. `droogie/bbhost` PR #217 handles a distinct NP signaling/lifecycle layer; avoid non-parity imports.

**Draft only.** No Fornex deployment, proprietary assets, personal saves, installer or native-port release.
