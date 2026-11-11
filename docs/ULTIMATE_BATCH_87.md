# Ultimate B87 — restore guest's own pickups before crash/rejoin baseline

Date: 2026-11-11. Source: actual Ultimate client branch B87 on B86 [#153](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/153). **This is Yharnam Together's existing coop runtime; not BBSC's old Bells, not the future no-eboot Windows port.**

## Original observed defect and source provenance

The official [Yharnam Together #566](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/566) was **merged** after its `pickup-after-guest-crash` rig reproduced a guest taking a map item by the first Central Yharnam lamp (flag 52410140), closing the game, restarting directly in the host's session and seeing their own pickup flag off again. The host's world must not transfer personal pickup flags. The upstream patch put `SetGuestPickedFlags()` into the joined guest's periodic `KeepGuestProgress` path **before** its initial observation baseline.

Compared with current Ultimate B86 code: `SetGuestPickupsBeforeMapItems` does restore personal pickups on some map-creation paths, and `KeepGuestProgress` restores them at home, but **did not** restore them during the active session before its baseline. The map-creation hook is rate limited and may execute before a late host-world overwrite, while the periodic observer continues in-session. That specific gap is now addressed.

The original upstream #566 also changed P2P packet-loss rig infrastructure. It is deliberately **not** copied into the Ultimate's server-owned GameLink path; B82–B85 preserve reliable native packet behavior independently.

## Exact B87 changes

1. `emulator/src/core/bloodborne_flags_store.cpp::KeepGuestProgress`: after confirming the existing guest role and two-second `GuestProgressInterval`, reapply personal pickup flags in an active session **before** creating/refreshing the observation baseline. Reuses the existing native `SetGuestPickedFlags` that only sets currently missing flags and verifies the game readback. Calls it **before** taking `guest_picked_mutex` for the observer, avoiding nested lock/deadlock. Does not grant any item lot or create rewards; it sets only previously recorded per-hunter pickup flags.
2. `bloodborne_team.cpp/.h::ShouldReplayGuestPickupsInSession`: live owner/scope check: no replay out of session, with an unknown slot, or invalid generation. On first process start an unobserved slot may restore its persisted pickup flags; a known changed slot or character generation **does not replay in its first tick**, and only the next matching observation can replay.
3. `GuestPickedFlags` in-memory cache is now keyed by **both** slot and live character generation. The existing solo `ForgetSlotIfNewCharacter` path retains its archive and metadata-clear behavior, incrementing generation when it identifies a new hunter; B87 cannot reuse the prior generation's in-memory vector.
4. Real emulator `GuestPickupReplay.CrashRejoinRestoresCurrentHunterButNotOldSlot` GoogleTest source checks initial process bootstrap, normal rejoin, non-session, unknown slot, zero generation, slot switch, same-slot generation switch and recovery. `tools/ultimate/test_batch_87_guest_pickup_rejoin.py` checks the **actual source call-site ordering**, cache-keying, owner reset and the preserved map-load path. CI compiles the **production owner scope function extracted from bloodborne_team.cpp** under GCC/Clang/MSVC with elementary type stubs. This is a narrow native unit test, not the full running emulator.

## Safety boundaries and known remaining risk

- **Important:** a live generation is not a durable globally unique per-character identity. Existing game-side `ForgetSlotIfNewCharacter` runs before map-item creation only when not in an active session. A completely different hunter loaded into the *same slot in a new game process* without a validated stable character identity cannot be conclusively distinguished by B87's startup rule. Accordingly **this PR must not be described as fully solving every cross-process slot-reuse risk**; require a stable save/hunter fingerprint and 2/3/5-player game testing before release.
- This corrects the *crash/rejoin duplicate map pickup* mechanism from #566. It does **not** establish that every reported empty chest, no-open-prompt, item-lot award, or visually missing object in [Ultimate #73](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/73) shares this cause. Those remain separately open.
- Still-open [#137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137) requires verified on-disk Bloodborne savedata ACK for phantom badge/tool debt; [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) deferred NPC/boss lots require real native grant observation; [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) also awaits upstream #554 HomeWorlds migration integration and live guest-world tests.
- No live Fornex restart or deployment, no client release, no installer, no game executable or decrypted game assets, and **no modifications to real player saves**. Historical screenshots/Discord information are private in gungrain Google Drive.
- Full shadPS4 Windows build and full game GoogleTests are tracked in inherited workflow B46; unit smoke tests on B87 do not substitute for them.

## Verification plan (real client rig, not performed here)

Using an isolated **baseline save copy** (never an original), stage two separate hunters in different save slots and one new hunter replacing a previous hunter in the same slot. Test normal pickup, map load, force-crash, direct session rejoin, second restart, solo load, immediate team rejoin, and host taking/not taking the same item. Read native flag 52410140 and inspect inventory exactly once, then repeat over 2/3/5 hunters and packet loss/reorder. The official [#566 rig scenario](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/566) is a grounded starting point but must be adjusted to Ultimate's server-owned team and tested on a clean 1.09 game, including modded vs clean if relevant.

## Global source discipline

Compared exact merged upstream #566 implementation with B86, B64 save safety and B82–B85 transport. Consulted existing [B84 global source sweep](ULTIMATE_GLOBAL_SOURCE_SWEEP_20261111_B84.md) and [P0 source parity register](ULTIMATE_P0_UPSTREAM_SOURCE_PARITY_20261111.md). A branch-name census is not exhaustive code review. Do not blend incompatibly different BBHost/BBGL P2P stacks into server-owned co-op.
