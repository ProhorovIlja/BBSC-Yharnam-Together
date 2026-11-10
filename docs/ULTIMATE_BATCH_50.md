# Ultimate B50 | preserve player saves across installer updates

2026-11-10. Stacked on [Ultimate B49 Draft #108](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/108). Upstream source reference: official Yharnam Together [PR #554](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/554), **open/not merged** at this checkpoint; contains separate host-progress fix that is NOT merged here.

## Confirmed source-level hazard and scope

- Our `tools/release/setup.iss` had one recursive `[Files]` entry that excluded player-controlled `bbport.ini`, `mods.json`, `patches.json`, but not the **`user`** or **`savedata`** directories. Although `tools/release/check_release.py` prohibits these directories in published release input, a mis-staged installer could still recursively overwrite files in them. This was a missing defense-in-depth guard, **not proof that the installer caused any particular reported rollback**.
- Actual Inno Setup `[Files]` `Excludes` specification (https://documentation.help/Inno-Setup/topic_filessection.htm) describes matching a backslash-prefixed pattern against the start of the relative source path; the pattern `\user\*` excludes only that top-level source directory and `\savedata\*` does likewise. This precise exclusion strategy was also proposed in YT upstream PR #554.
- Changed the single recursive file entry to `Excludes: "bbport.ini,mods.json,patches.json,\user\*,\savedata\*"` so the installer will not include player save files even if a packager accidentally stages them. This doesn't need to read any private save, user account or game asset.
- No changes to how the game serializes its world flags, owner/guest role, character inventory, backups or auto-update. In particular **this does NOT fix** the separate P0 host-home-world rollback and phantom key-items-after-quit issues.

## New regression tests

- `tools/release/tests/test_setup_saves.py`: parse all Inno script sections (case-insensitive), require every `[Files]` source has exclusions for `\user\*`, `\savedata\*` and existing player settings; `[InstallDelete]`/`[UninstallDelete]` are restricted to shortcuts, `[Code]` cannot call direct deletion functions.
- Parse the launcher's `MADE_FOLDERS` uninstall cleanup constant to assert only `out` and `event-patch` are removed, never `user`, `savedata` or the game's original source. Negative staged-build fixture deliberately removes savedata exclusions and detects loss of protection.
- Windows/Linux Python tests and a separate manifest guard run in GitHub Actions. A passing source test proves the manifest's protection but is not equivalent to a real signed Inno installer update/uninstall on Windows; that runtime gate is still required before shipping.

## High-priority remaining upstream work

- [#554 upstream](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/554): host's personal save reload may restore a weeks-old personal world when its home team world progressed, losing boss/lamp/NPC flags. Needs safe test-save migration for home-world ownership and server version. Do not transplant save migration without reproducible backup/rollback tests.
- [#548 upstream](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/548): guest may lose Sword Hunter Badge/Blood Gem Workshop Tool when game quits before personal inventory is restored. Needs durable per-slot ledger, atomic writing, idempotent grant and 2–5 game test.
- Both are tracked in our main [Issues #22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) and [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) and the [canonical cross-chat ledger](ULTIMATE_CROSS_CHAT_REQUIREMENTS_MASTER.md).

## Release safety

Only an experimental Draft PR; no Fornex, no deployment, no installer is published, no user saves or protected game files touched. The actual Windows game-free compilation gate through B49 and user multiplayer integration remain separate checks.
