# Ultimate B79: block unverified phantom-key debt retirement

Date: 2026-11-11. Stacked on [B78 Draft #144](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/144). Relevant to [P0 #137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137) phantom-earned items lost after quit/restart. Independent deferred boss/NPC native item lots [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) still separate.

## Verified gap: native item grant and save completion are not equivalent

Actual `emulator/src/core/bloodborne_re.cpp::NoteSaveFileOpened` obtains `character_slot` from `CharacterSlotOfSavePath(guest_path)` and raises `NewCharacter` on slot changes. The generation in `bloodborne_flags_store.cpp` is bumped by an in-process event-flags/new-character heuristic. These hooks do not establish an immutable per-hunter ID over process restarts and do not provide success of a *disk write*. The item manager's `AddTradeItems` / nested `GiveItems` returns `void`, so observing goods in a live inventory is not durable savedata evidence. External corroboration: [shadPS4 issue #4803](https://github.com/shadps4-emu/shadPS4/issues/4803) reported a game session that could LOAD a Bloodborne save, but permission-denied failures prevented later `userdata0000`/`userdata0010` WRITES. This is a public user report, **not a reproduction on the Ultimate rig**.

The B68–B78 **offline-only** immutable file journal `emulator/src/core/phantom_key_ledger_file.h` treated empty debt strings as valid tombstones, and `CreateNewRevision(root, Revision{slot, fingerprint, seq, ""})` unconditionally wrote them. A plausible caller could infer "paid" from a volatile own-inventory observation and irrevocably commit an empty record *without save confirmation*. On restart, `ScanLatest` previously treated it as paid and could silently erase the remaining debt. No trusted game savedata ACK provider exists in this project.

## Concrete B79 code fix

- `CreateNewRevision` now **refuses ALL empty debt revisions before taking the filesystem writer lock**. Only nonempty canonical debt can be appended through this API. No new attempt is made to invent a successful game-save acknowledgement.
- `ScanRevisionsUnlocked` returns `Blocked` when a committed `.ready` revision has empty debt, rather than accepting it as `Ready` or replaying earlier debt. This is deliberately a fail-closed behavior for any preexisting tombstone lacking a trustworthy proof path. It does not rewrite or delete the old record. `Decode` and `ReadReady` still recognize its bytes for manual inspection. Future support for legitimately paid records needs a **separate authenticated/validated game-save ACK protocol**, not a generic `bool acknowledged` argument.
- Real `emulator/tests/bloodborne/test_phantom_key_ledger_file.cpp` now exercises: failed creation of tombstone before lock/directory effects, a successful next *nonempty* sequence, injection of an externally fabricated valid legacy tombstone file, readable metadata but blocked recovery, no silent fallback and no newer commit allowed while blocked. Existing revision gaps, corruption, lock races, symlinks, bounded files and 0–9 slot rules remain tested.
- Dedicated `.github/workflows/ultimate-batch-79-save-ack-retirement.yml` verifies exact production C++20 filesystem tests under Ubuntu GCC and Clang and Windows MSVC, plus source-only audits on both OSes. Inherited B68/B70/B73 and B78 CI must remain green. No real game's save data accessed.

## Still blocked

**This cannot prove a disk save acknowledgement**, identify a stable hunter over separate processes, perform a write-before-grant game transaction, ensure power-loss `fsync` ordering or safely replay an ambiguous native `GiveItems`. A conservative reader `Blocked` means **human/safe recovery needed**; it is not an automatic item restoration. It intentionally makes offline debts non-retirable until a future reliable save ACK interface exists. The journal is still disconnected from `GiveBackPhantomKeyItems` and still uses a checksum for detection, not authentication. User backups and Fornex production stay untouched. No real 2/3/5-player Windows game rig or standalone no-eboot native port was completed.

## Whole-project candidate intake

Reviewed current open upstream Yharnam Together PRs #577 party settings, #575 friendly fire, #574 join trip, #571 Linux, #559 login diagnostics, #524 travel lock fix and merged #548 phantom ledger; independent droogie/bbhost #236 FSR/PE, #221 mod text, #231 input glyphs, #141 renderer; separate owner native PC port #84 partial 9955 AOT leaf funcs and #89 save migration. These remain compatibility/licensing/ABI/real-performance candidates, not blindly bulk-merged features.
