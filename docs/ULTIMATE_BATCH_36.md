# Ultimate B36: explicit PLAY OFFLINE on the co-op launcher, with *the same saved characters*

**2026-11-09**, stacked on [B35 Draft #82](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/82), source chain B01–B35. Following [#69](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/69), **a user may edit a character offline and then play that already modified character online**. B34 adapted cheat-watch baseline diagnostics; B35 allowed known built-in startup cheat patches only when not online, but the *co-op release itself* still exposed a Play button that always logged in and loaded co-op events. B36 makes the offline mode actually selectable in that launcher.

## Actual source findings

- `bbport/launcher/bbport_launcher_win.py::play_coop` always invokes network preparation: firewall, public shard discovery, account/server and co-op `game_environment`.
- `bbport/launcher/bbport_coop.py::game_environment` deliberately sets `BB_ONLINE=1`, ShadNet server/identity/password and `SHADPS4_BLOODBORNE_SEAMLESS_COOP=1`. It cannot be re-used verbatim for an offline game.
- `bbport_coop.prepare` creates a merged Bloodborne 1.09 game view and co-op `event-patch`; `copy_events` writes these to sibling `CUSA03173-mods`. `bbport/scripts/mods.py::user_layers` *automatically imports sibling `CUSA03173-mods`* when mods are on. Merely removing server credentials from the game environment therefore leaves co-op story/NPC EMEVD files in the offline game. This is the specific issue B36 isolates.
- The normal user save directory of the co-op install is `<install>/user`. Offline sandbox must use that same path per owner permission, with a backup before playing, rather than silently forcing a different blank character.

## Exact patch

1. **Visible** co-op **PLAY OFFLINE / ИГРАТЬ ОФЛАЙН** footer button, independent from normal PLAY. It checks game folder only, not account/team/server readiness. It does not run firewall checks, DNS, shard discovery, server login or online crash report upload.
2. `bbport_coop.prepare_offline_game` builds/reuses only the 1.09 game+update file view, not generating/writing/overlaying party boss or NPC event scripts. It validates the version and returns the updated game view; original private game files are never uploaded or copied into source control.
3. `bbport_coop.offline_game_environment` scrubs ShadNet secrets, member/party state, P2P, online flags and co-op HUD; sets `BB_GAME_DIR`, `BB_CONFIG`, `BB_DATA_DIR`, `BB_USER_DIR=<install>/user`, `BB_IGNORE_LEGACY_GAME_MODS=1`, `BB_PARTY_HUD=0`. Preserves separately selected user mods and patch configuration.
4. `bbport/run.py::game_view` forwards `--ignore-legacy` to `bbport/scripts/mods.py`, which skips the auto-detected **co-op sibling EMEVD overlay** without globally disabling all user mods. Online Play still runs with standard co-op event overlay and server world.
5. The production launcher Cheats page now **displays offline-only built-in Cheat toggles** alongside Gameplay Tweaks, with a visible offline-only warning. B35's compiler prevents these built-in cheat codes from applying during online Play. The legacy **Save editor for stats/items/outfits is not yet restored** and requires a separate source/provenance audit and game save guard.

## Tests

Run `bbport/tests/test_coop_offline_sandbox.py` on Ubuntu and Windows: exact offline env with old online secrets wiped, **same** user saves, test-only fake Bloodborne game/update path, correct no co-op event generation, selected visual user mods preserved while sibling co-op mods omitted, and real `run.py`→`mods.py` flag path. `test_launcher_production.py` checks the actual production launcher Cheat choices; B35's real patch selector tests run again on both OSes. Exact nine changed files compared to B35 and six SHA-pinned source/test blobs.

## Remaining limitations

- No real full Windows 1.09 game test, screenshot-backed GUI interaction, NPC quest completion, or physical 2/3/5 player test. This is a Draft feature whose code and policy are verified only by synthetic tests.
- No stat/item/outfit Save editor has been restored yet; the old 1.3.1 implementation and offsets still require compatibility and license review before changing personal savedata.
- External unreviewed third-party patches/mods may still be gameplay cheats in online modes. B35 only blocks the built-in known names; honest online fair-play enforcement/false-positive handling is separate [#70](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/70).
- Both play modes deliberately share savedata. Always back up a test copy before trying any new UI build; offline edits are permitted online but save corruption/quest flag integrity is an unresolved separate problem [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22).
- Host Fornex server is unchanged, no release installer was built and no proprietary game archives were copied.

Do not merge into main before a real Windows gameplay acceptance rig verifies both independent startup modes and save continuity.
