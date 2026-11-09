# Ultimate B29: fail closed on personal-world and invasion-home recovery

Date: **2026-11-09**. Stacks on B28 [Draft PR #60](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/60), hence the entire B01–B28 playable line. The native PC port without eboot remains a separate longer-term track.

## Real source-proven risks

1. **Guest return from team to solo:** `ApplyTeamWorldOnLoad` restored personal flags, then called `std::filesystem::remove(PersonalWorldFile(slot), error)` but ignored the error and set `personal_world_due = false`. If the old snapshot still existed, a later team join could treat those stale flags as the latest original world rather than capturing new solo progress. This threatens bosses/doors/lamps and cross-session persistence.
2. **Unreadable personal snapshot:** the same restore function called `ReadWholeFile`, which returns an empty string for both **missing** and **unreadable** snapshots, then cleared `personal_world_due`. In the parse-error path it also used `personal_world_due = own.has_value()`, incorrectly treating a malformed existing backup as if nothing needed restoring. On a subsequent team load, the capture path used `ParseWorldFlags(...).value_or(WorldFlags{})` and could overwrite a previously unreadable/corrupt backup with borrowed-state-derived content.
3. **Invader's home before PvP:** `SaveInvasionHome` called `WriteWholeFile(path, FormatInvasionHome(home))`, ignored the boolean added by B28, logged success and returned true. The game could begin its invasion without having backed up its original world/respawn.
4. **Invader return after PvP/crash:** `RestoreInvasionHome` treated an unreadable/empty file as no original home, and if `ParseInvasionHome` failed it actually **deleted the existing backup** and returned true. A delete failure after applying flags was also ignored. This could discard the last copy of the invaded player's original state or falsely complete a recovery.
5. **NG+ transition:** the prior personal snapshot removal ignored errors before clearing `next_playthrough_due`, allowing stale previous-playthrough flags to potentially return after a later guest session.

## B29 production fixes

- Extend the exact dependency-light production header `emulator/src/core/team_world_file.h` with `ReadExistingFileChecked` (binary, optional success; callers explicitly distinguish nonexistent files using `std::filesystem::exists(path, error)`) and `RemoveWorldFileChecked` (checks actual removal, safely idempotent for verified absent files).
- **Guest restoration:** distinguish a verified *missing* personal backup (no restoration needed) from an unreadable/empty/corrupt **existing** file. Retain `personal_world_due` on read or parse failure, never auto-delete unparseable originals, and clear pending only after confirmed snapshot removal. An unreadable existing file also blocks adopting another team world; avoid overwriting it. B28's must-write-before-host-flags gate remains unchanged.
- **NG+:** do not clear `next_playthrough_due` when old `personal_world_<slot>` cannot be safely retired.
- **Invader safety:** on starting an invasion, verify any pre-existing home file is actually parsable, and return false if the original world cannot be safely written. `TickInvasion` already withholds travel while `SaveInvasionHome` is false. On returning home, refuse absent/invalid read treated as success, preserve malformed/unreadable copies for recovery, and return success only when restoration was applied and snapshot removal succeeded. An early-ended invasion does not drop `home_kept` on failed recovery.
- Per-character `SlotFileName(..., slot)` preserved. No protocol, world file format, account, launcher, or gameplay reward change.

## Evidence and focused verification

- Real code file: `emulator/src/core/bloodborne_server_world.cpp`; exact Git blob pinned.
- Existing portable test `emulator/tests/bloodborne/test_team_world_file.cpp` now additionally checks binary reads, a missing backup, a present-but-empty backup, a refused delete of a nonempty recovery directory without changing original bytes, confirmed delete and idempotent repeat. Compile/run the **actual production helper header** under both Windows Server 2022 MSVC and Ubuntu GCC. Real game call-site source ordering is additionally verified.
- CI allows only six files from B28. No full client/game recompile per small patch. B27's independent real server Docker twelve suites and B28's Windows/Linux file write tests both completed SUCCESS in their own workflows.

## Limits and safe rollout

This prevents known destructive or false-success source code paths, **not** proof of successful restoration in an actual Bloodborne game. A corrupted backup is deliberately preserved for recovery and might need player-visible diagnostics/manual intervention. A completed rename or deletion does not guarantee durability through sudden power loss. Before any release, reproduce real solo→guest→solo and solo→invade→home on multiple save slots, intentionally blocked backups, NG+/Chalice state, live actor sync and reward integrity. Never run fault injection on real saves.

[Supermedo Windows 1.9.8.3](https://github.com/Supermedo/bloodborne_pc/releases/tag/windows-v1.9.8.3) independently reports a world contamination fix, but its root cause and proprietary/runtime architecture were not assumed identical. Review its GPL source separately before any source transplant. No production Fornex, personal saves, private game assets, installer, or public release were accessed.
