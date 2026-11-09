# Ultimate B32: an NPC quest story flag is not delivered until the game actually applies it

**Date:** 2026-11-09. Parent [B31 Draft PR #65](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/65). Continues cumulative playable/online server/client/launcher B01–B31 improvements. Native non-eboot PC port remains a separate project.

## Source-proven failure mode

In `emulator/src/core/bloodborne_server_world.cpp::FollowTeamStory`, B31 correctly diffed host NPC story flags in overlapping world blocks. But the function advanced `team_story_followed = std::move(target)` **before the game's native `SetEventFlag` call** and never checked whether the game actually took the new quest flag. A temporary game rejection (script loading, NPC state transition, missing actor ownership or other unmet engine condition) meant the next 2-second tick saw the same host report, calculated an empty delta and **never tried the previously rejected change again**. A real NPC could therefore remain in an old story state until the next map load, despite the server's current world being correct.

This is a **proven source-level dropped retry path**, not proof that the user's specifically reported Eileen/Henryk invisibility in Tomb of Oedon was caused by it.

## B32 code changes

- Define `TeamStoryRetriesForWorld(pending,current,flags_per_block)` beside `TeamStoryToFollow` in real production `emulator/src/core/bloodborne_team.cpp`. It retries only global NPC/story flags in a **currently covered block** whose desired boolean value still agrees with the **current** host world. If host changed the quest stage again, changed world or retired a block, stale entries are discarded.
- After the native `PartyGhostSetEventFlagOffset` function is invoked, query `EventFlagOn(flag)` again. Only if the value is still incorrect, record `(flag,wanted)` as **unconfirmed**, not as delivered. Native `void` return is not a success acknowledgement. If already correct, skip the native write and do not retain a retry.
- Keep `team_story_retries` bounded to at most 512 distinct entries, held only in memory under the existing `team_mutex`. At each normal 2-second game tick, merge a bounded, deduplicated, still-current retry set with the newest host delta.
- Clear retries and advance `team_story_context_generation` at all new team, new save, leave team and on-load world replacement boundaries. After releasing the mutex and calling the game function, requeue only if the **context generation is unchanged**, the guest is still in session and the **latest host snapshot still asks for that exact value**. This avoids replaying another team's state even if a host change arrives mid-callback.
- Preserve B31's shared-block filtering and every per-player NPC dialogue reward exclusion; never add map actor flags, time of day or item flags to this generic NPC story follow path.

## Regression tests

- Extend real `emulator/tests/bloodborne/test_bloodborne_team.cpp` with tests for failed host NPC writes, same snapshot retry, changed-host rejection, lost block, duplicate dedup, personal Iosefka gift flag, map flag and time-of-day exclusion.
- Add `tools/re/tests/test_npc_story_write_retry.py`: extracts and **actually compiles the unchanged production C++20 classifier, story delta and retry helper** under GCC/Ubuntu and MSVC/Windows; uses a synthetic game that rejects the first write. Source audit verifies real code reads flag **after** invoking the native setter, bounds retries and resets team context.
- CI checks exactly nine changed files against B31, hashes of all six production/test blobs, cross-platform native execution plus B31's updated source-exact NPC coverage fixture, which now checks that ResetTeamStoryTracking clears both the old world snapshot and failed-write retry queue.

No full emulator, game binary, server or installer rebuild. No real files/saves or Fornex accessed. Live game verification still mandatory.

## Open NPC/gameplay issue gates

- [P0 #63](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/63) Eileen + Henryk Tomb of Oedon and other NPC quest actor spawn/visibility/dialogue. B31/B32 cover **host story flag delta propagation**, not NPC actor creation. Need 1.09 save-stage/quest conditions and actual 2/3/5 PC playtest.
- [P1 #64](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/64) new hunter starting in Iosefka's Clinic after joining Cathedral Ward progressed host and seeing Small Celestial Emissary / Impostor Iosefka. May be valid host stage. Do not revert host flags to satisfy new hunter's prologue; personal dialogue/reward events must be verified separately.
- [P1 #66](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/66) external CLS report: Vicar Amelia guest unable to examine the skull, personal sunset-to-night transition stuck. Separate time-of-day and interaction action; no proof same bug present in Ultimate. Don't alter 9800–9802 from B32 generic NPC retry.
- [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) personal solo world must not inherit foreign quest or boss progress.
- [#9](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/9) master ultimate backlog.

**Important limitation:** immediate in-memory readback and synthetic native C++ tests cannot establish on-disk save durability, successful NPC actor spawn, eventual progression on real game scripts or multiplayer parity. Retry state is deliberately not saved and dropped on map/team changes. All PRs stay Draft until full stack/game validation.
