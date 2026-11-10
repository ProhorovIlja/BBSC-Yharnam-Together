# Ultimate B66: isolated offline save snapshots from Windows-port research

Date 2026-11-10. Parent: B65 Draft #131. Source: [ProhorovIlja/bloodborne_pc_windows_port](https://github.com/ProhorovIlja/bloodborne_pc_windows_port) pinned master SHA 6486642d35418bd26c278bceadaf42e842daf4e4, specifically scripts/party_saves.py and src/runtime_savepolicy.c. Tracking [#130](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/130), P0 [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) and [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35).

## Why import selectively

The Windows port correctly separates solo savedata from multiplayer savedata_party. However its replace=True path in copy_solo_to_party copies the old party folder to a backup and then deletes the active party folder with shutil.rmtree(party) before renaming a staging directory. A crash, disk issue or antivirus lock in this gap can leave the active party directory missing. It uses size-only inventory verification and a fixed staging folder name. That source cannot be transplanted unmodified into Ultimate, whose host HomeWorlds and guest phantom-item P0 migrations remain unfinished.

## Code actually added in B66

New offline-only Python utility: tools/ultimate/port_save_quarantine.py.

The stage_snapshot(user_dir, solo|party) operation ONLY READS the selected active folder. It writes to a randomly named new folder inside user/save_backups/ultimate_quarantine, initially .partial and then .ready after validation. SHA-256 of source and copy, unchanged inventory and second-pass source checks are required. Original savedata and savedata_party are never removed, overwritten, renamed, linked into a network session or switched as active. Temporary .bbtmp files are excluded.

The verify_snapshot(snapshot) operation validates its manifest, byte sizes, hashes, relative paths, symlinks, duplicate names and extra files. Explicit rejection applies to symlinked source/backup roots, empty sources, suspicious metadata and files exceeding bounded size and count. Failed copies delete only the newly created random partial candidate; a failed post-promotion verification deletes only the new invalid ready candidate. Earlier verified snapshots remain unchanged. The CLI does not include a restore action or any automatic game launch.

Tests: tools/ultimate/test_port_save_quarantine.py, entirely synthetic temporary directories, include solo/party isolation, multiple snapshots, tampering, extra files, invalid manifest traversal, symlinks, locked/disk-full simulated failures, changed source during copy, and cleanup after a failed final verify. CI runs Python 3.12 on Windows 2022 and Ubuntu 24.04.

Important distinction: This is a protective archive/staging primitive, not a coherent multi-file live snapshot of a running game. Do not use during game writes. OS-level power-loss durability of all file and directory metadata is NOT established. There is no 1-click import, online save migration or rollback automation. B66 does NOT claim to fix the playable #22 host rollback or #35 phantom items: user saves must remain isolated until game-session/slot identity and filesystem transaction tests pass.

## B67 complementary actual Windows port change

The same source review led to a separate [Draft PR #89 in ProhorovIlja/bloodborne_pc_windows_port](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/89), where the existing launcher can actually request solo-to-party save replacement. This separate source branch implements unique pending backups, SHA-256, exclusive lock, recovery of interrupted promotions, support for visy's legacy `savedata_party.replaced` path, and a **real launcher pre-start recovery gate** that refuses to launch a party immediately after restoring an old backup. Windows/Linux synthetic save regressions: [B67 CI workflow](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/workflows/b67-party-save-rollback.yml). This is a complement, NOT evidence that the two incompatible YT and P2P save formats can be merged; no real save migrations or releases.

## Next integration decisions

- Compare Windows port save namespace and per-character side files with our Yharnam Together team world and save paths, requiring an explicit per-runtime profile and verified restores before making a launcher toggle.
- Port host HomeWorlds #554 and guest phantom ledger #548 through atomic durable transactions and live test rigs; no destructive upstream fallback.
- Inspect direct P2P/NAT implementation and Vulkan stability patches from the port with protocol negotiation, gameplay/latency benchmarking and 1.09 byte-checked patch sites, not blanket cherry-picking.
- Resolve GPL-3.0 source vs GPL-2.0-only previously imported boss header compatibility before any combined distributed binary. Respect other source licenses and game copyright.
- No Fornex, no real player saves, no proprietary game data, no public deployment.

Source-only draft. Full native client/gameplay and 2-5 player tests are separate gates.
