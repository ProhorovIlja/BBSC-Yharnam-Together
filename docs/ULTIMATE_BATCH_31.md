# Ultimate B31: keep NPC/story changes when host world coverage changes

2026-11-09. **Draft candidate**, parent B30 [#62](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/62). The playable client/server/launcher improvements accumulate through B01–B30; separately planned native PC port without eboot is unaffected.

## Direct code defect in the existing 1.4.0-derived client

Production `emulator/src/core/bloodborne_team.cpp::TeamStoryToFollow` originally returned an empty list whenever `before.blocks != after.blocks`. Flag-block coverage legitimately changes when the host game loads a new map, advances quests or WorldFlags captured by the server gains/loses blocks. The test that compares whole lists caused the guest to skip **all** global NPC/quest-story flag changes in already-covered blocks, despite both reports knowing those blocks. A guest who remained in a scene without reloading could miss an NPC quest stage transition until their next map load. This is a **source-confirmed synchronization gap**; the actual Eileen/Henryk reported game bug is **not proven caused by this exact path**.

The client also reused `team_story_followed` across title/start, join/leave and switched team contexts in some paths. Reusing a previous team's world snapshot as a delta baseline is unsafe; the original global "different blocks" check happened to suppress some unintended effects but was overly broad.

## Change and boundaries

1. Add an explicit `flags_per_block` argument to `TeamStoryToFollow(before, after, flags_per_block)`. Zero / unknown block geometry returns no changes.
2. When both sides contain a block, continue to apply its changed **global NPC story flags**, even if the host additionally loaded or dropped another map block. A flag in an added or removed block is ignored live and left for the game map load; never force a speculative NPC spawn/despawn from a partial snapshot.
3. Preserve `IsTeamStoryFlag` exclusions: map-scoped 12M–13M flags, item flags 50M–53M, per-player gift/dialogue, time of day, special session rules, and flags with dedicated `FlagTable` rows remain outside this delta path.
4. Derive `flags_per_block` from the **actual current client FlagStore** (`ReadFlagStore().flags_per_block`) rather than assuming a fixed game layout. If unknown, do not update the baseline.
5. Clear `team_story_followed` when adopting a new party or team, leaving to solo or starting a new title save, so another team's NPC history cannot become the new one's delta baseline. Existing `ApplyTeamWorldOnLoad` seeds a coherent baseline only when it actually takes that team world.

No packet format, server persistence, game assets, installer, user save metadata or personal flag ownership is changed.

## Tests and evidence

- Extend real `emulator/tests/bloodborne/test_bloodborne_team.cpp` GTests to expect common-block NPC flags to propagate through coverage changes, but leave different blocks untouched.
- Add `tools/re/tests/test_npc_story_block_coverage.py`: extracts and compiles **the exact production** C++20 `IsTeamStoryFlag` and `TeamStoryToFollow` on Windows MSVC and Linux GCC using synthetic flags (global NPC story 1100/1121/1205/1300 vs per-player Iosefka 72410300, time of day, map events). Its tiny RowFor mock models rule exclusion and does **not** prove individual vanilla scripts.
- Source checks verify new title/party baseline resets, valid store scaling and exact eight-file SHA pins.
- No full client build, game replay or physical five-hunter multiplayer test is claimed.

## Two separate new bug reports

- [P0 #63 NPC quests/Eileen + Henryk](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/63) requires the missing NPC/quest-stage reproduction at Tomb of Oedon, character actor spawn, wrong quest/event flags, vanilla control, host/guest, host migration and real reward handling. B31 fixes one **potential contributing story-delta gap**, not the requested NPC spawn path itself.
- [P1 #64 new hunter at advanced-host clinic](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/64): new character may see Small Celestial Emissary and Impostor Iosefka behind the closed clinic door when joining a Cathedral Ward-progressed host. This can be correct host-story representation, yet conflict with personal first-visit tutorial and rewards. **Do not force the host world backward**. Compare scenario with new save solo, host-before/after Cathedral Ward, post-Rom, session join and save return.

## External review leads

- [Official YT releases](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/releases) include an already-addressed story-NPC bug: a guest appearing near a guest while host was elsewhere could see NPCs hidden by the host story, such as Eileen near Grand Cathedral. Check exact 1.4.0 code before duplicating.
- [visy bloodborne_pc_windows_port ERSC parity notes](https://github.com/visy/bloodborne_pc_windows_port/blob/master/docs/party/ERSC_PARITY.md) describe test-aided, single-machine Henryk/Eileen hostile-actor synchronization and NPC fight team state. These aren't automatically compatible or a true two-machine proof for the YT client.
- [Bloodborne Wiki Iosefka](https://www.bloodborne-wiki.com/2015/03/iosefka.html) and [Impostor Iosefka](https://www.bloodborne-wiki.com/2015/07/impostor-iosefka.html) distinguish real and impostor NPC stage. Vanilla location appearances are prerequisites, not proof of Ultimate bug root cause.

## Unresolved acceptance gates

Real protected Bloodborne 1.09 client tests at known story flags, Henryk spawn/Eileen dialogue, early clinic NPC stages, actor HP/visibility, two/three/five players, late join, map travel, host migration, new char vs NG+, and solo→team→solo personal world hashes. The host's NPC state cannot poison an unrelated guest's own save, and no personal reward may be lost or doubled.

**No changes to Fornex, copyrighted games, private saves or production launcher.** Promotion requires end-to-end client/server protocol verification and real gameplay evidence.
