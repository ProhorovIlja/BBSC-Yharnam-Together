# Ultimate B33: don't follow an unverified host night/blood-moon story stage

**2026-11-09**. Stacked after [B32 Draft PR #67](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/67) in the cumulative B01–B32 playable client/launcher/server stream. The separate fully native non-eboot PC port is unchanged.

## Source-confirmed inconsistency: two ways to set time of day

Bloodborne's event flags **9800 (evening), 9801 (night, e.g. Vicar Amelia skull) and 9802 (blood moon)** influence NPC placements, sky/time and some quest-stage conditions at map load. A guest can load a different scene from the host, so Yharnam Together already contains two paths:

- `ApplyTeamTimeOfDayOnLoad` passes `WorldFlagsOf(*team_world)` into `TeamTimeOfDayAtLoad`; the helper checks that the host snapshot *covers* the time-of-day flag block before forcing on/off states.
- `FollowTeamTimeOfDay` previously copied **only** the 980x IDs from `team_world->on()` and called `TimeOfDayToFollow(team,EventFlagOn)`; it **never read or validated** `team_world->blocks()`, nor the live `FlagStore.flags_per_block`. A partial/oddly updated TeamWorld with a time-stage flag in its `on` list but without authoritative coverage for that stage could advance a guest's time/NPC stage in a scene while the host had not actually established this block. This is source-proven **missing validation**, not proof that such malformed/partial reports were the cause of the user's clinic screenshot.

Additionally `ApplyTeamTimeOfDayOnLoad` cached a `static u32 flags_per_block` over future loads. This layout belongs to the currently readable game's store, and shouldn't be treated as a lifetime constant across different save slots, new-game or NG+ load boundaries.

## Exact patch

1. Change `TimeOfDayToFollow(team, flags_per_block, on)` to require **known non-zero block geometry** and the presence of the affected flag's current host block before advancing the guest's stage. Preserve the existing **forward-only between-map-loads** rule: an advanced guest isn't blindly rolled backward while live.
2. `FollowTeamTimeOfDay` uses `WorldFlagsOf(*team_world)` (including `blocks`), checks the game isn't still loading, and takes `ReadFlagStore().flags_per_block` from the **current** game instance each tick. A source `on` value without the host's block coverage never forces 9800/9801/9802.
3. `ApplyTeamTimeOfDayOnLoad` removes the process-static geometry cache and reads live `flags_per_block` on **each load**, returning safely when the store is unreadable.
4. `TeamTimeOfDayAtLoad` checks coverage **for each of the three flags** rather than assuming one check for 9800 proves all three blocks are loaded. Real 1.09 geometry normally has all three in one block, but this avoids unchecked assumptions when the store layout changes.
5. No new flags or world ownership overrides, no host stage forced to a newcomer's first-visit clinic, no NPC actor spawn/change of native cutscene logic, no wire protocol, server or save format change.

## Tests and evidence

- `emulator/tests/bloodborne/test_bloodborne_team.cpp` GTests cover host reports with 9800/9801/9802 `on` but **no covered block** (do nothing), block geometry missing (do nothing), valid host blocks (advance guest), later guest blood moon (don't roll back between loads) and small-block synthetic geometry where 9802 has separate coverage from 9800/9801.
- `tools/re/tests/test_time_of_day_host_coverage.py` extracts and **compiles the actual production C++20** `TimeOfDayToFollow` and `TeamTimeOfDayAtLoad` under Ubuntu GCC and Windows MSVC; exercises real helper code with synthetic worlds. It audits the actual `FollowTeamTimeOfDay`/load call sites to ensure checks are used and the static cache is absent. No public game scripts or private saves are needed.
- Eight changed files compared with B32, pinned exact Git blob SHA for all 5 source/test files, plus B31/B32 source/native fixtures rerun on Linux. No full Windows client or Fornex rebuild.

## Unresolved gameplay acceptance gates

- [P1 #66](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/66) **Vicar Amelia skull**: reported in a different BBSC fork. Requires real host/guest skull interaction, cutscene, event flag on both characters, leaving session and observing personal sunset→night progress. B33 makes **flag coverage** consistent and is NOT a fix for the physical skull action, missing cutscene or another player's solo state.
- [P1 #64](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/64) **new hunter at Iosefka's Clinic** with a progressed Cathedral Ward host may legitimately see **Small Celestial Emissary / Impostor Iosefka**. Need vanilla solo vs early/late host stage and protected new character save. The patch refuses unverified host stage, but **does not pretend** to restore the first-visit clinic when the host's story stage is verified.
- [P0 #63](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/63) **Eileen/Henryk** requires real actor visibility, quest event and dialogue flags, and quest completion in Tomb of Oedon. B31/B32/B33 are limited flag consistency fixes.
- [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) solo progression and save isolation, [#9](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/9) master track.

Keep Draft until genuine 2/3/5 player Windows 1.09 gameplay and load/save/quest outcomes are validated. No Fornex writes, no personal savedata, no proprietary game files, no installer.
