# Ultimate B35: built-in cheats only for offline patch builds

**2026-11-09.** Stacked on [Draft B34 #81](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/81), which made *saved custom-character stats/items* acceptable as a multiplayer starting baseline. B35 changes a different layer: **game startup patch selection**. The owner's requirement is that a character edited offline must still play online, but the **editing/cheat mechanisms themselves** must not be active in a multiplayer session.

## Source-proven limitation

In the current B34 source, `bbport/scripts/patches.py::effect_patches` checks `scripts/build_info.json` (production) rather than the **game's launch mode** and drops `DEV_TOOL_KEYS` on all production launches, including offline. Meanwhile a development build could select those exact cheat patches even online. A manually supplied `--extra` patch name or an external XML patch sharing a built-in name could reach the patch compiler even when the saved `bbport.ini` toggle was filtered. In the standalone launcher `game_environment` copied `os.environ` and the custom `extra_env` and only set `BB_ONLINE=1` if chosen, **without clearing inherited online/co-op flags** for an offline start. This could cause wrong patch policy and accidental network configuration.

## Exact code changes

1. In the real `bbport/scripts/patches.py`, define `online_game(env)` from **`BB_ONLINE=1` OR `SHADPS4_BLOODBORNE_SEAMLESS_COOP=1`**. `bbport_coop.game_environment` always sets both for co-op Play, so the existing co-op launch cannot enable these startup patches. Offline runs (even packaged production) may select the built-in cheats. An explicit launch-mode check applies to dev builds too, rather than dev=always allowed.
2. The `DEV_TOOL_KEYS` list (built-in no-death, stealth, silent, no-rally-decay, enemy control and debug camera/menu) is compiled into `OFFLINE_TOOL_PATCH_NAMES`. `effect_patches(settings,production,online)` now filters by actual online status; `production` is retained as a compatibility argument. Existing non-cheat `TWEAKS` are unaffected by this narrow gate, subject to separate online safety classification.
3. `filter_online_dev_patches` also checks the **raw `--extra` list** and external XML *when named identically to a built-in offline-only patch*, before writing compiled `patches.bin`. This closes alternative selection of known built-in patch names. A third-party patch with a different name or arbitrary code **is NOT verified safe by this filter**; [Issue #70](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/70) must add a reviewed online mod/patch policy.
4. In `bbport/launcher/bbport_launcher_win.py::game_environment`, an explicit offline launch clears stale/inherited `BB_ONLINE`, `SHADPS4_BLOODBORNE_SEAMLESS_COOP` and stored server/password/link-key values from the child environment before optionally applying the newly selected online credentials. The co-op launcher subsequently rebuilds its own online environment; no change to real accounts or saved settings.

## Evidence and native coverage

- Real production `patches.py` imported/executed under Python 3.12 on **Ubuntu 24.04 and Windows 2022** in `bbport/tests/test_patch_mode_guard.py`.
- Existing `bbport/tests/test_patches.py::DebugPatchTests` checks the new rule: offline production allows built-in cheats, online production and online dev disallow them, while known tweaks remain.
- Unit tests cover co-op marker alone, old saved flags, independently named `--extra` patches, XML shadowing with a built-in name, inherited online variables, and non-cheat tweak preservation. Seven precise B34→B35 changed files and four pinned Git source blobs are CI-gated.

## Not yet complete

B35 intentionally **does not yet expose the hidden production Cheats tab** or recover the historical 1.3.1 **Save stat/item/outfit editor**, so ordinary co-op release users cannot yet invoke an explicit offline sandbox from their co-op-only Play path. This work still requires a safe offline Play button, launcher state/UI synchronization, save editor provenance and real Bloodborne 1.09 smoke tests. It also does not promise protection against all unknown third-party code, a modified external client, game-time online toggling or active memory cheats. The B34 watcher remains diagnostic, not server enforcement. An online gameplay mod classification and active server-side validation must be built separately.

No Fornex, user saves, game binaries, installer or release artifacts touched. Keep Draft.
