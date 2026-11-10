# Ultimate B48: prevent guest kill replay / false map respawn (actual game source)

2026-11-10, stacked on [Draft B47 PR #106](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/106). Tracks [#23 P0 enemy synchronization](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/23). **Exact verified upstream source:** [YT PR #564](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/564), `merged=true`, with author's 2-player rig before/after demonstration and ctest 1475/1475 at their revision.

## Symptom and proven source cause

An enemy killed by a guest can remain reported alive on the host's board while the game/server propagates the kill. Old `BroughtBackByTheHost()` assumed 'alive at host and dead for 3 seconds at guest' was sufficient reason to force a game respawn. That could resurrect a fresh guest kill; generator respawn in turn wakes other dead enemies, duplicates echoes, and corrupts the apparent enemy state. This exact old branch was still present in our B47 ancestor `emulator/src/core/bloodborne_party.cpp` and `bloodborne_kills_hp.cpp`; it was not already included.

## Surgical adaptation in production C++

- `bloodborne_kills_hp.cpp`: per-map-visit `host_dead[handle]` captures an enemy *seen dead on the host's board*. It resets whenever the host map visit token changes. Real generator revivals are thereby distinguished from delayed guest-only kills.
- `bloodborne_party.h`: `HostDeadBeforeCopyMs = 15'000`; `BroughtBackByTheHost` now receives the observed host-death timestamps.
- `bloodborne_party.cpp`: only resurrect a dead guest copy if the host is currently alive AND was observed dead in the same map visit no earlier than 15 seconds before the guest copy died. Retain all other safeguards: boss never regenerated, `party_kills` exclusion, hidden/distant/disabled host actors, `BringBackAfterMs` and deterministic handle sort.
- `test_bloodborne_party_death.cpp`: update existing generator/boss GTests and add the exact bug fixture `AGuestNeverBringsBackItsOwnKillTheHostHasNotSeenYet`. Upstream was based on its own current `main`, so this integration uses exact matching local function anchors rather than blindly applying 6 file patches.

## Test and release gate

- Windows/Linux Python source contracts verify the real engine call site, map visit reset and new GTest; a Linux GCC+Clang harness extracts **the real production `BroughtBackByTheHost()` function** and compiles its exact implementation in isolation against safe stand-in PODs. Test fresh guest-only kill, valid revival, stale death, strict 15-second boundary, boss immunity, member kill, hidden enemy and no-host-death evidence. No duplicated re-implementation in fixtures.
- This synthetic C++ compile is NOT equivalent to full shadPS4 Bloodborne CMake build or a 2–5 game playtest. Still require true multi-client session with network delay and regeneration (Hemwick Mad Ones, bell maiden skeletons), repeated wipe and duplicate Blood Echo prevention. The prerequisite cumulative B46 Windows build is separate and may need its own compiler fixes.

## Other newly discovered upstream candidates

- [YT #554](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/554) OPEN: host home-world progression rollback when playing alone. P0 user requirement #22; source and saved-game migration need careful per-slot identity tests.
- [YT #548](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/548) DRAFT: key items gained as phantom reappear after game closes; P0 #35, must not lose/duplicate items across slots.
- [YT #561](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/561) DRAFT: chalice-wipe warp into void/closed doors. User map collision/travel #75/#72; needs real chalice 1.09 fixtures.
- [YT #549](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/549) DRAFT: 60->30 FPS frametime cliff in co-op, 60Hz late-flip presentation changes; needs frame-pacing benchmarks.
- [YT #546](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/546) MERGED: all nine CUSA game editions instead of hardcoded CUSA03173; verify against this fork's pre-existing separate CUSA check PR #92 before import.
- [YT #563](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/563) OPEN: short-circuit null GPU resource-table pointer walks and improve failure reports. Does not fix the underlying null pointers; investigate source and GPU microbench.

**No Fornex, passwords, private Bloodborne/DS3 game files, individual saves, installer or release touched.**
