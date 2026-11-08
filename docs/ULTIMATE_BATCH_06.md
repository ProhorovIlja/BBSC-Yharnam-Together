# Ultimate B06: prevent partial guest-progress metadata writes

**Experimental source patch, not a shipped client or a proven game-save repair.**

## Exact source-level issue

On the B05 base, `SaveGuestProgress()` and `SaveGuestWorldChanges()` opened their per-character text records with `std::ios::trunc`. `ForgetSlotIfNewCharacter()` and `ConfirmGuestPickupsInOwnWorld()` did likewise for owner and confirmed pickup records. The previous file was truncated **before** a new write could complete, so a write failure, full volume or interruption could leave a partial/empty record and confuse per-character progression.

## Patch

The four records now call `ReplaceGuestMetadataFile`. It stages the new text in a sibling `.tmp-<pid>-<counter>` file, flushes/closes it, then asks `std::filesystem::rename` to replace the destination on that same filesystem. If staging or replacement fails, the existing destination remains untouched and the temporary is removed. The old destination is **never** deleted as a workaround for an inaccessible Windows file.

If the owner metadata cannot be committed, the new-character transition aborts before it clears the old slot's lists. This favors preservation over continuing with an inconsistent owner record. No user's actual PS4 game save files are modified by the test.

The world file still uses the existing serial background writer. The patch changes its disk commit helper, not game-thread scheduling or the encrypted network protocol.

## Synthetic verification

`tools/re/tests/test_guest_metadata_atomic_replace.py` compiles the **actual production C++ helper** with a tiny test-only shim for constructing the temp name. Tests include successful replacement, empty replacement, an invalid parent directory, a destination that is itself a nonempty directory (rename failure), old data retained, and cleanup of temporary files. Source checks assert all four write paths use the helper. The package's dedicated CI also re-runs the earlier B01-B05 targeted tests and checks precise source Git blob hashes.

No full client, launcher, server, portable ZIP, installer or real Bloodborne 1.09 game session is built for this small source batch.

## Explicit non-guarantees

- An `ofstream::flush` is **not fsync**. This is process-crash/failed-replacement mitigation, not guaranteed power-loss durability or an atomic transaction over four metadata files.
- A changed list whose new write failed may need a retry trigger: the old file stays intact, but the **new** pickup may still be missing after a hard stop. Delayed/asynchronous world commits also require separate teardown and fault-injection checks.
- Real Windows NTFS/antivirus behavior, concurrent operations, private saves and a full five-hunter session have not been tested.
- This is independent of the separate [Supermedo 1.9.8.3](https://github.com/Supermedo/bloodborne_pc/releases/tag/windows-v1.9.8.3) claim about host-world flags persisting in a guest save. The public GPL seamless engine ZIP was identified but **not read/imported**. YT 1.4.0 behavior must be verified independently.
- B06 does not address Link4 integration, DBNO, GPU performance or the still-failing late Windows compilation in [PR #31](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/31).

See [P0 #22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22), [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35), [B05 #37](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/37), and the exact-source manifest. **Fornex remains unchanged and no release may be shipped from this PR.**
