# Ultimate B58: Blood Level and compact build names in Discord Rich Presence

**2026-11-10.** Stacked on [B57 Draft PR #121](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/121). User-requested cosmetics, preserving B56/B57 state machine, party counts, privacy controls and source-only change gates.

## Implemented in production source

- `bbport/gpu/bbcoop/discord_presence_policy.h`: the level is shown as `BL 25` (Blood Level), **not `Lv 25`**, when the existing independent level privacy flag is ON. The **location remains visible even during a known boss encounter**, if location visibility is enabled. Encounter details then use `Boss: <known name> | <current location> | BL <level> | <compact build>`. Outside fights: `In <current location> | BL <level> | <compact build>`. When location is disabled, boss information will not reintroduce the location (and vice versa); when boss is disabled, both its name and fight-only timer are hidden. No guessed information on missing game snapshot.
- `bbport/gpu/bbcoop/build_archetype.h`: single authoritative `Mask` with STR/SKL/BLT/ARC threshold **18 inclusive** remains unchanged; new `DiscordShort(mask)` maps **all 16** combinations without affecting the full English/Russian names in game HUD and other surfaces.
- `bbport/gpu/bbcoop/discord_status.cpp`: real Discord IPC path invokes `BbHunterBuild::DiscordShort` on game-thread-cached offensive stats, not static examples. The cached level and area continue to be provided through B56. The user must opt in to both level and build separately with B57 launcher settings, which default OFF.

## Complete short label mapping

| Mask | Stat(s) at 18 or above | Discord |
| --- | --- | --- |
| 0 | none | UNF |
| 1 | STR | STR |
| 2 | SKL | SKL |
| 3 | STR + SKL | QLT |
| 4 | BLT | BLT |
| 5 | STR + BLT | STR/BLT |
| 6 | SKL + BLT | SKL/BLT |
| 7 | STR + SKL + BLT | QLT/BLT |
| 8 | ARC | ARC |
| 9 | STR + ARC | STR/ARC |
| 10 | SKL + ARC | SKL/ARC |
| 11 | STR + SKL + ARC | QLT/ARC |
| 12 | BLT + ARC | BLT/ARC |
| 13 | STR + BLT + ARC | STR/BLT/ARC |
| 14 | SKL + BLT + ARC | SKL/BLT/ARC |
| 15 | STR + SKL + BLT + ARC | OMNI |

`QLT` means Quality (STR+SKL), `UNF` means Unfocused (no offensive stat at 18), `OMNI` means all four qualify. A stat of 17 does not count. Invalid stats outside the game's 1–99 range return no build rather than a fabricated one; level only displays when in validated range 4–544.

## Example status presentation (not a verified Discord screenshot)

- `In Central Yharnam | BL 25 | STR/ARC`
- `In Cathedral Ward | BL 90 | QLT`
- `Boss: Cleric Beast | Central Yharnam | BL 25 | STR/ARC` and boss elapsed timer (only when the named-boss adapter is eventually verified).
- `In co-op session (2 of 5)` when Discord renders `party.size`, with `(2/5)` a tested formatter fallback. No duplicate count from B57.

## Verification and limitations

- `bbport/tests/test_discord_activity.cpp`: all 16 mappings at exactly 18, existing descriptive labels remain intact, BL 25, boss/area combined detail, independent visibility, boss-only timer suppression, unknown/invalid fallback and group count regression.
- CI checks production header/IPC source contracts on Windows/Linux, compiles same C++20 policy tests with GCC and Clang; does not constitute a game run.
- Existing B56 game-thread snapshot still depends on verifying each supported 1.09 CUSA. A **precise boss-name adapter** is not implemented in runtime; a boss encounter can display the generic `Boss fight`. Do not mistake test fixture `Cleric Beast` for live verified identification.
- The Ultimate Discord Application ID remains unregistered/unconfigured by default. Actual live Discord desktop, cumulative Windows BBPort native builds and 2–5 player trials are required before distribution.
- No Fornex production changes, no player saves, game binaries or third-party copyrighted mod assets touched. See [issues #119](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/119), [#122](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/122) and the master ledger.
