# Ultimate B57: concise co-op session Rich Presence and visible 18+ hunter builds

**Date:** 2026-11-10. **Stacked on:** B56 Draft PR #120. **User request:** prefer `In co-op session (2/5)` to `In co-op (2 out of 5)`; show builds in Discord with the same >=18 offensive-stat classifier as the launcher/game.

## Actual code in this batch

1. `bbport/gpu/bbcoop/discord_presence_policy.h`: the guest status is now **`In co-op session (N/M)`**; for unknown or invalid counts, it says only **`In co-op session`**, never fake membership. The boss encounter takes precedence in Discord's one details row, but an explicitly shared local **level and build remain appended** during the fight. With boss visibility disabled, both boss identity and fight-only timer are omitted to avoid privacy leakage. A spectator (especially a player dead in an active boss fight) is **`Spectating`** even if a stale duel flag is present. Other roles keep B56 semantics: `Hosting`, `Invading`, `In Team Duel`, `In-duel`.
2. `bbport/gpu/bbcoop/build_archetype.h` from B45 remains authoritative: STR/SKL/BLT/ARC independently qualify at >=18, masks 0-15 render meaningful 16 labels, invalid 0 or >99 stats reject the label. `bbport/tests/test_discord_activity.cpp` now checks **all 16 masks**, threshold boundaries, build retention in boss fights, privacy and exact `2/5` and `3/5` strings. This is *reuse*, not a second competing classifier.
3. `bbport/launcher/bbport_coop.py`: independent persisted preferences in `user/coop.json`: `discord_show_area` and `discord_show_boss` default ON; `discord_show_level` and `discord_show_build` default OFF until the player opts in. They map to `BB_DISCORD_SHOW_AREA`, `BB_DISCORD_SHOW_BOSS`, `BB_DISCORD_SHOW_LEVEL`, `BB_DISCORD_SHOW_BUILD` only while Discord RPC itself is ON. On other launches all child-env status and privacy keys are cleared, including stale parent values. The ID of the user's registered Discord application may be supplied via a **numeric 17-20 digit** `BB_DISCORD_APP_ID` in the launcher environment; invalid inputs are rejected. No third-party app ID is hijacked.
4. `bbport/launcher/bbport_launcher_win.py`: when a valid Discord application ID is configured, the co-op settings show independent **Location / Level / Build (stats 18+) / Boss and fight timer** options next to the existing overall Discord RPC toggle. The options persist through existing `coop.json` saving, and are not global/team-authoritative.
5. `bbport/tests/test_coop_launcher.py`: tests on/off, no app ID, public-vs-home join eligibility, default preferences, independent controls, clean environment after disabling, and save/load settings persistence.

## Examples (format, not captured live-game proof)

- In Central Yharnam | Lv 90 | Strength/Arcane **·** In co-op session (2/5)
- Boss: Cleric Beast | Lv 90 | Quality **·** Hosting; Discord elapsed time uses the ongoing fight start
- In Fishing Hamlet | Lv 120 | Skill/Blood **·** Spectating (if watching the fight)
- Solo: `Solo hunter`, invader: `Invading`, team duel: `In Team Duel`

Actual boss name detection still requires a validated encounter-to-name game adapter; the B56 runtime currently says `Boss fight` rather than guessing a boss. The examples illustrate the formatter with supplied *verified* names, not a promise of that adapter.

## Important blocker, not hidden

The mainline `bbport_coop.DISCORD_APP_ID` placeholder is blank. Without a Discord-issued application ID, **Rich Presence cannot connect**, so no launcher switch is offered. The env-configured ID path is now supported for test/deployment configuration, but public Ultimate must register and package its own legitimate app ID before shipping. Do not reuse another project's application ID.

## Unfinished work / QA

- Full Windows native BBPort/launcher build, actual Discord desktop screenshot/IPC inspection, 1–5 player game rig, Unicode/localization and all supported CUSA 1.09 parity.
- Confirm the 18+ stat snapshot is refreshed on every character switch/level up and not stale during world reload. Confirm the boss-start detection tolerates short boss flag pulses (B56 uses ~2-second Discord polling); boss name map remains unimplemented.
- Extend server to multiple invaders, actual faction-filtered HUD and down/revive by hit (B56 pure policy only); do not turn on multi-invader DBNO based solely on these RPC tests.
- Preserve `docs/ULTIMATE_CROSS_CHAT_REQUIREMENTS_MASTER.md` and tracked issues #9/#119; no Fornex production changes, no player saves or copyrighted assets touched.

**Truthfulness:** Passing source/CI checks is not a complete packaged gameplay release. This batch targets precisely scoped Discord/personal-privacy improvements.
