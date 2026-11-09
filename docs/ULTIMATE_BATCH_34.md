# Ultimate B34: offline-edited saves are allowed, active in-session changes still tracked

**2026-11-09.** Stacked on [Draft B33 PR #68](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/68), cumulative source chain B01–B33. The user explicitly **revised** the offline/online policy in the latest conversation: a player may edit their character's stats, items, level and outfits offline, then use that saved character ONLINE; only **live cheat tools and active runtime patches** must be unavailable in online multiplayer. The previous mandatory clean-copy save separation proposal is superseded. Source requirements are in [#69](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/69) and [#70](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/70).

## Exact source audit that prompted this narrow patch

- `bbport/launcher/bbport_launcher_win.py::build_cheats` contains real `CHEATS` and `TWEAKS` definitions but hides Cheats on a production release. `bbport/scripts/patches.py::effect_patches` independently suppresses all cheat/debug patch keys if `scripts/build_info.json` has `production=true`. Merely showing an offline tab does not make game cheats actually work. The old Save editing panel code is **not yet located**; “Restore saves” in current launcher restores backups only.
- `emulator/src/core/bloodborne_server_world.cpp::SendServerCharacterSheet` sends level, attributes, echoes, insight, production status, cheat patch settings and `save_edits` counter. The server cannot establish when an offline save was modified from those values alone.
- `server/coop/cheat_watch.h` already explicitly documents that it **ONLY logs** findings and adds suspects to server logs; it does **NOT ban/refuse players**. Despite this, `Limits` labeled **pre-existing** changed stats, inconsistent level and echoes as `Suspicion::Certain`. `Build` labeled `save_edits>0` Certain even if editing had happened offline before the first network sheet. These are false descriptions of **active cheating** under the owner's new permission model.
- `CheatWatch::Changes` already compares **consecutive sheets** within the same game run, tracking level/attribute discrepancies, free leveling, echoes and insight jumps. It is diagnostic only, not an authoritative server prevention mechanism.

## What this batch changes

1. `server/coop/cheat_watch.h::Limits` still records nonvanilla outliers by kind, but tags them as **Informational**, explicitly permitted offline-edited saved state. Likewise `Vitals` marks unusual persistent counts informational; it must not call them proven active cheats based on an initial value.
2. Remove unconditional `save-editor` Certain on nonzero `save_edits` in the first sheet. A save edited offline earlier in the same process is allowed online.
3. If a **later sheet in this connected game run** shows the editor counter **increased compared with the accepted baseline**, add `save-editor-active` finding, `Suspicion::Likely`. This is a signal, **not cryptographic proof** of an editor or a server ban. Reset baseline on a new character, fresh game hello or `StartOver`.
4. Preserve `Build`'s active cheat patch diagnostic as `Certain` and `Changes`'s in-session stat, level and resource delta alerts. Keep trade bound reporting and other data-safety checks intact. This batch does **not** change server acceptance, packet format, network actions, launcher or live patch selection.

## Real source tests

The existing `server/tests/test_cheat_watch.cpp` is extended, not replaced. It checks a high-level pre-edited character with out-of-vanilla attributes, echoes/insight and `save_edits` at first handshake, repeated identical sheet, save-edits increase within the same session, subsequent session reset, active no-death cheat patch, plus all earlier clean/default level-up, bloodstain, trade and in-session change cases. The current production `server/coop/cheat_watch.h` is compiled and the actual test binary is run on **Windows (MSVC)** and **Linux (GCC)**. Exact five-file B33→B34 diff and two SHA-pinned source/test files gate CI.

**Not yet implemented:** offline Save UI restore; client-side mode transition which truly uninstalls/blocks cheats; trustworthy active-gameplay anti-cheat enforcement, party-only build compatibility, actual Bloodborne 1.09 save/load and 2/3/5-person game tests. The owner permits an offline-customized PvP build, so vanilla stat fairness cannot be assumed. P2P migration #80 is independent.

No Fornex, no user saves, no proprietary assets, no release/installer. Keep Draft until integrated full game/system tests pass.
