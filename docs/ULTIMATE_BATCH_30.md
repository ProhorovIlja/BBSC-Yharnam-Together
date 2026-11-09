# Ultimate B30: NPC death drops are per character generation, not per save-slot number

**Date:** 2026-11-09. Parent [B29 Draft PR #61](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/61). This continues the cumulative B01–B29 playable client, server and launcher chain. The fully native PC port without PS4 eboot is separate.

## Source-confirmed defect

The existing [P0 guest reward issue #35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) was partially addressed by B03/B04: a **deferred boss lot or dialogue NPC gift** already tracks the save-slot number **and** `deferred_reward_character_generation` (bumped when `ForgetSlotIfNewCharacter` recognizes a different character in that slot).

However, a separate **NPC death-drop path** `emulator/src/core/bloodborne_flags_store.cpp::GiveNpcDeathDrops` kept a function-static `given_slot` and `std::set<s32> given`. The cache was cleared **only when the numeric slot changed or the character left a multiplayer session**. If a new character reused the same numeric slot while `in_session == true`, a death flag still in the old character's cache could prevent the new hunter receiving their own NPC death drop. Worse, the path could run with `slot == -1` (unknown save) and still award to that unowned world, unlike B04's deferred queues.

This is source-proven policy divergence, not field-reproduced in a real Bloodborne save.

## Production change

Add a small production `RefreshNpcDeathDropLedger(current, in_session, recorded, awarded)` helper next to B04's `DeferredRewardOwner`, using exactly its existing `slot + generation` identity. The real `GiveNpcDeathDrops` now:

- refreshes the cache for **every** current owner, including same-slot/different-generation changes, and for multiplayer-session leave;
- declines to process a death drop if the current save slot is unknown;
- keeps same-character/same-session dedup unchanged for the NPC death flags;
- inserts a death flag into `given` only **after** the actual native `AwardItemLot` function is called. Its return is `void`, so this is not a guarantee of successful game inventory changes;
- continues to verify `MapItemMan`, guest role, game player and trade state using existing guards.

No protocol changes, boss lot timing changes, persisted on-disk reward format or new dependency. Existing B04 deferred queues are not reset by this change.

## Tests

`tools/re/tests/test_npc_death_drop_owner.py` extracts **the exact real production** `DeferredRewardOwner` type and `RefreshNpcDeathDropLedger` function from `bloodborne_flags_store.cpp`, compiles and executes them under C++20 GCC on Linux and MSVC on Windows. The synthetic test mimics five hunters, verifies same-owner once-only dedup, different slots and same-slot changed generation resetting, leaving/rejoining a session, unknown slot refusal. A source audit checks the actual game call-site guard before attempting lot-grant and that recording happens after native call.

The workflow enforces only the five changed files from B29 and SHA-pins the real game source and test, then reruns B04's production owner C++ fixture and B03's readiness fixture on Linux. No full Windows client/server rebuild for this small patch.

## Open release blockers

B04's generation counter changes **only after** the existing per-character load detector `ForgetSlotIfNewCharacter` runs. A character replaced in the same slot **before** that detector settles is still a risk. The game item-lot API is `void`; `given.insert` after calling it is not proof of an item in inventory. There is no durable crash-persistent pending lot journal or exactly-once delivery ack. Real game testing on Bloodborne 1.09 across two, three and five peers, map loads, NPC deaths, NG+, host migration, same-slot character replacement and end-to-end item inventory/save backups remains mandatory.

Independent [CLSAMG22/BBSC #46](https://github.com/CLSAMG22/BBSC/pull/46) proposes static boss-reward table rows (Logarius Crown and m35 Celestial Dial); it was closed unmerged, and its description states the PR slice was not independently played. That different data path is **not** silently imported into the Yharnam Together dynamic guest death-drop hook. Original [droogie/BBHost #217](https://github.com/droogie/bbhost/pull/217) is a separate signaling/lifecycle stack that would change network compatibility.

Draft-only. No private game assets, real saves, live Fornex, release artifacts or passwords accessed.
