# Ultimate B64: non-destructive HomeWorlds policy intake and verified snapshot archive

**2026-11-10. Parent:** [B63 Draft #128](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/128). **P0:** [#22 host world rollback](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) and [#35 guest key item persistence](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35). **No deployment and no real save writes.**

## Evidence / why not a blind cherry-pick

[Upstream Yharnam Together #554](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/554), MERGED 2026-11-10, fixed a host playing its own team world alone but accidentally restoring an ancient personal-world snapshot. Its pure `HomeWorlds` policy stores per-slot home world IDs, last seen server version and whether the save played alone, and chooses: `Aside` (someone else's world), `Home` (host save owns this world, server copy leads) or `SaveLeads` (this host played alone and server version still equals last seen). **B64 additionally fixes a safety issue in upstream's 16-world limit:** rather than evicting the oldest known home world when creating a 17th, it refuses the new entry. Forgetting an old home would otherwise make a prior host world appear to be a foreign guest world, risking the rollback we are trying to prevent. Overfull manifests fail closed. Legacy slot hints can be classified Made/Visited/Unknown against a verified server lobby. The user wants *all* supported progression correctly preserved, not a temporary save fix.

Its production `RetireOwnWorld` still removes the old `personal_world_before_home` snapshot, then attempts to rename the `personal_world` file, then **deletes the source file if rename fails**. A failed rename must not destroy a last-known-good file. This exact sequence is unsafe for Ultimate's future migration. Therefore this PR introduces verified read-only policy and a non-destructive archive, not its unreviewed file migration.

## Implemented source, compilation and failure gates

1. **`emulator/src/core/bloodborne_team.h/.cpp`**: adapted the actual upstream `HomeWorlds` policy and parser, `WorldIdOfParty`, `TeamWorldTake`, `OldSavesWorld` with its owner/host rules. The file remains GPL-2.0-or-later; attribution to upstream PR #554 is explicit. The policy is **not yet wired** into `ApplyTeamWorldOnLoad`, so existing game behavior is not silently changed before tested migrations.
2. **`emulator/src/core/team_world_file.h`**: new `CopyVerifiedWorldArchiveNoClobber(source, archive)`, a small dependency-free production helper available to future save migration. Rejects missing/empty/oversized (>64 MiB)/symlink source, existing destination files/directories/dangling symlinks, non-same-parent destination and same-file copy. Uses `std::filesystem::copy_file(..., copy_options::none)` so an existing archive is NEVER overwritten, then compares both files in 4096-byte chunks to confirm exact copy. The original source is **never deleted, renamed, modified or replaced** even if the copy fails. If our just-created copy fails verification, only our candidate is removed. Caller must choose a **new versioned backup filename**; existing backups are not overwritten and incomplete unverified candidates must NEVER be auto-restored.
3. **`emulator/tests/bloodborne/test_team_world_file.cpp`**: real cross-platform C++20 filesystem test extends the pre-existing B28 test (which already validates personal-world writes) with binary-preserving archive and file equality, existing backup untouched, new revision coexisting, missing parent/occupied path, optional symlink rejection, empty source, directory source, source=target and original preservation after failures.
4. **`emulator/tests/bloodborne/test_bloodborne_team.cpp`**: new actual GoogleTest coverage for `HomeWorlds` 16-world limit, validated IDs and parse corruption, legacy server ownership and host/guest world-version decision matrix.

## Important remaining gates before REAL host-world behavior changes

- **No real HomeWorlds integration yet.** Need specific `bloodborne_server_world.cpp` work: stage and verify a manifest, classify legacy-world slot against authoritative lobby host, mark known home world without replacing original until verified, never restore ancient personal snapshot over a home world, safely advance version after host reports, and rollback on every failed transition.
- **Power-loss durability NOT established.** The no-clobber copy is non-destructive on normal process errors but does **not** fsync both file and directory on all operating systems. Only verified in-place backup copies and no-overwrite semantics can be claimed. Crash-durable commits and ordered save/ledger versioning are a separate step, not implied by `copy_file` success.
- **Guest key-item recovery #548 remains unported.** Upstream `std::ios::trunc` direct file writes are not safe enough for the last owed-items ledger copy; first design transaction/atomicity, fail injection and slot/character binding.
- **Live game rigs:** host creates world, spends hours in co-op, disconnects, plays solo, reconnects to same/different versions, host migrates, guest saves and returns, files are locked/unwritable, unexpected power loss, missing/corrupt manifest, updated game and same-slot new character. Two to five hunters + nine supported 1.09 CUSA, no live account or Fornex production work. Do not announce Ultimate playable/release-ready.

## Other-source radar

- [Upstream #548](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/548) MERGED: PhantomKeyItemLedger persists badges/goods after close; port only after checked file transactions.
- [Upstream #524](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/524) OPEN: Travel Together lock inversion; **already fixed in our B63** via separate inbox mutex, not duplicated.
- [droogie/bbhost #217](https://github.com/droogie/bbhost/pull/217) OPEN: signaling and spectator camera API, ABI/protocol incompatible without coordinated client/server migration.
- [CLSAMG22/BBSC #9](https://github.com/CLSAMG22/BBSC/pull/9) OPEN: boss wipe bar/respawn and stale recovery test candidates.
- [Upstream #559](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/559) OPEN: game server sign-in diagnostics, not a confirmed root cause.

**Status:** non-destructive primitives and pure host progression policy integrated into source; compilation/unit tests and complete game integration have distinct gates. No player saves, passwords or proprietary assets touched.
