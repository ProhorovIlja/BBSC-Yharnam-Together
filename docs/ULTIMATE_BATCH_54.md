# Ultimate B54: fail-closed journey intent foundation

**Date:** 2026-11-10. **Issue:** #116. **Base:** B53 Draft #115.
This is a first *source-code* increment toward the user's optional Doll-triggered NG+ and defeated-boss rematches. It is NOT yet an available game menu, boss spawn or cycle transition.

## Source selection and licenses
- Bloodborne Enhanced (Nexus /bloodborne/mods/19) supplies useful UX examples: disable automatic NG+, manually advance at the Doll; beaten-boss rematches at lamps/Broken Lamp. Its asset modification/redistribution is permission-gated. **Do not copy its code or mod assets.**
- Jgamrot/yharnam-pc (windows/docs/ROADMAP.md) has experimental lamp rematches with only a Cleric Beast real gameplay run reported; compare for mechanics and game-version data, never assume co-op readiness.
- droogie/bbhost (GPL-3.0-or-later) has a boss-rush plugin, modded-instance isolation and native plugin structure. Its GPL-3 runtime and BBPort GPL-2+ need explicit license review for code reuse. No source from this project is copied here.
- Elden Ring/Sekiro reflections and other FromSoftware QoL offer gameplay design patterns only.

## This batch actually adds
`emulator/src/core/ultimate_journey_policy.h`: a dependency-light C++20 policy with **default-OFF, independent** manual-NG+ and boss-rematch toggles; verified game/version + character/save ID gates; offline-only, no matchmaking, PvP, transition or concurrent save; NG+ requires the Doll, the character's own ending eligibility and a verified backup; a rematch requires this character's own defeated flag and a prepared arena at the boss/Broken Lamp. A two-stage **Offer -> Confirm** single-use intent is bound to character, save revision, action and location. A stale, changed, denied or cancelled offer cannot commit; confirmation rechecks live conditions.

`tools/ultimate/ultimate_journey_policy_smoke.cpp` compiles the exact header and exercises disabled-by-default, all denial branches, no replay, revision changes, session changes, different character and refusal for unknown game installations. GitHub Actions builds/tests on GCC and Clang plus Windows/Ubuntu source checks.

## What this batch deliberately does NOT do
No ESD/Talk hooks yet; no automatic NG+ suppression, menu option, boss spawn, scripted enemy reset, rewards, per-session instance, save snapshot implementation, server protocol change or game-file edits. Policy `Allowed` is **not permission to modify the save**: future adapter must separately stage a tested atomic rollback-capable backup, validate story flags, call the correct per-CUSA game action and verify outcomes. `save_revision` must represent authoritative current save generation, not a timestamp or nonpersistent UI counter. Unknown data MUST deny. Boss rematch work should be a temporary instance, never clear first-kill/progression/NPC flags or emit an ordinary first-kill activity message.

## Release gates
1. Verify 1.09 game events / Doll ESD and ending flags for all supported CUSA; define explicit save transaction (write+fsync, backup and rollback) before enabling any trigger.
2. Full Windows build of adapter and real game rig: solo and 2–5 players, B51–B53 Doll regression, NG+ lifecycle, guest/host mismatched cycles, lockouts, save reload, quick travel, game crash.
3. Boss lamp/arena map matrix including all main game/DLC/chalice bosses, deaths, double clear, no duplicate rewards, quest isolation, mod conflict matrix, opt-in party policy and no invasion leakage.
4. Isolated parity/performance measurements and copyright/license approvals.
No Fornex deployment or user saves modified. Draft only.
