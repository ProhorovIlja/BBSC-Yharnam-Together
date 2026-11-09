# Ultimate B13: keep earned boss Insight with its actual hunter

**Scope:** playable Yharnam Together 1.4.0 client. This is a new source-level player/reward isolation fix on top of B12 PR #44, **not** a native eboot-free Bloodborne.exe milestone, live server deployment, full client build or game playtest.

## Verified production failure mode

`emulator/src/core/bloodborne_travel.cpp::GiveEncounterInsight` used one process-global `static s32 points_due` while handing out boss discovery Insight one at a time, every 300 ms. The boss 'found' flag was set as the points were queued, but `points_due` was never tied to the `character_slot` / saved hunter generation. It also continued its payment loop after the team session ended. A hunter switching saves while points were still due could therefore cause the pending Insight from the old character to be granted to the new loaded player.

The existing B04/B05 deferred **items** already use a character slot and replacement generation. That previous work did not protect this distinct **Insight** tally. We found the actual path by auditing [upstream YT Issue #508](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/508) (shop purchases appearing to exhaust another party member's stock) and the connected [our #22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) personal-world tracker. **We are not claiming this Insight bug is the cause of the shop stock report.**

## Production changes

- `bloodborne_party.h` adds `EncounterInsightPayout`, a limited (at most 200 points per owner) game-thread ledger keyed by **save slot + replacement generation**.
- Change of owner resets `EncounterInsightWatch`'s observed boss flags, so the previous hunter's event history cannot leak across saves. Unknown owner (`slot=-1`) cannot accumulate or receive Insight.
- A pending payout stays associated with its original hunter when switching between ordinary save slots **within the same process**; switching back resumes its due points. A new character replacing a slot (generation changes) does **not** inherit the old character's awards.
- The original one Insight point per **300 ms**, original `AddSpEffect` virtual call and `once_flag` write, boss detection and all network/server protocols stay unchanged.
- `bloodborne_re_internal.h` exports the **existing** `deferred_reward_character_generation` shared signal to travel.cpp; no duplicate counter or new save format is introduced.

## Tests

Five new engine GTest cases in `test_bloodborne_party.cpp`: switching two players, replacing a character in the same slot, invalid owner/no amount, 300-ms pacing, and repeated-event capacity bound. The dedicated `tools/re/tests/test_encounter_insight_owner.py` extracts the exact `EncounterInsightPayout` C++ class directly from the real header, compiles and runs it with C++20 **on Linux and native Windows CLANG64**, and ensures the real travel call site uses the owner guard rather than the old `static points_due`. It also checks that the new real-engine GTest cases exist. A B13-only CI workflow pins actual production Git blobs, verifies the **eight-file** B12-to-B13 diff and runs inherited B01–B12 source regressions, not a redundant full game build.

## Important limitations / open questions

- This **does not solve or verify YT #508 shop purchase stock sharing**. Current source already has `FlagTable` per-player rules for badges, shop weapons and gifts, with `KeepLocalFlagsFromOthers` and `KeepLocalEventsFromOthers` hooks; the user's reported Yharnam Hunter Set stock remains un-reproduced on a current exact commit. Do not change all shop flags blindly. In actual 1.09 five-client tests verify independent merchant purchase availability and one-time stock with distinct saves, different host world, session leave/reconnect and modded/unmodded `ShopLineupParam`.
- While Insight remains queued **within the current running process** across character switches, a crash, full process exit or replaced-character generation can invalidate unpaid points. This batch does **not** make the queue disk-durable. The game's native `AddSpEffect` returns void; synthetic checks cannot confirm award success or refund on failure.
- Real gameplay must include multiple boss discoveries with 1–5 Insight points, rapid switch, quit/relaunch, guest death/wipe, changing bosses, map travel and full save backup comparison. Validate only on private copied saves.
- The B12 Windows/Linux C++ helper tests passed, but **a complete integrated 1.4.0 Windows client/launcher/server game build remains open**, including #31 compiler diagnostics, CPU/GPU performance and 5-player Link4. Native AOT Windows port is a separate equal mission.
- No private game/DS3 files, live Fornex, user saves, credentials or installable release touched.
