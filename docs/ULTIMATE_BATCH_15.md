# Ultimate B15: genuine two-parent merge of client fixes and dedicated server

Checkpoint 2026-11-09. Source tree for the **playable Ultimate** only. The separate truly native Bloodborne PC port that does **not** load original PS4 ELF/eboot at runtime remains an independent mission.

## Commit lineage, not copy-pasted fixes

B15 combines the full cumulative B01–B14 client, graphics, gameplay, account/launcher fixes **and** both stacked server PR histories:

- First parent: B14 `c298d66de8afafb9138a804377e36afb0b7332e3` ([Draft PR #46](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/46)).
- Second parent: server hardening/world privacy `db8597ad3800770fc8cdcd1d7b2190fe29083961` ([Draft PR #7](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/7) and [#8](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/8)).
- Real two-parent merge commit `6bac40e706821461a95620b2760e93fa8b4b0cf9` with an explicit 18-file server source tree overlay. Its source server files are **exact** Git blobs from #8, not reconstructed excerpts.

The original server main-based CI source allowlists do not apply to an accumulated client+server tree. B15 scopes them to their original PR branches **and adds a new explicit integration workflow** with its own exact B14→B15 source guard and real native server / Docker tests. This is not disabling tests to obtain a green badge.

## Source and network compatibility gate

- The linked client and server retain byte-identical `server/src/shadnet.proto` blob `7dd51bc90891c454f004e0bc102a7c562a7000f5` and `server/coop/coop.proto` blob `92791f8ad3ca4e57fc601497b41a0cb0c672ce61`.
- Preserve B14's newer `server/coop/game_link.h` blob `a51259f3228966ef0a75c2da4a082020c91913f7` over server #8's older same-path `5029581251bfe5decf562c19a10bdd079150cdad`. B14 tracks sender/instance and queued timestamps to keep the join hello (channel `0x42`) and subsequent reliable packets for a newly restarted game. Porting the old header over it can reintroduce lost first world snapshots and hanging hot joins.
- Other shared `coop_messages.cpp`, `world_log.cpp`, `link_crypto.cpp`, and `coop_stream.h` blobs match the server branch. No protocol message type, field number, auth credential, data schema or game packet bytes changed in B15.
- Server #7/#8 contributes admission limits, multi-owner/bounded 5-player load-generator, server world writer durability, protected world membership, hosted admin diagnostics, and more isolated tests. The source is integrated; end-to-end behavior is **not assumed verified** until tests complete.

## Meaningful CI acceptance gates

1. B15 source provenance checks exact merge parents and server file SHA pins, upstream/client protocol identities, 5-player bounds and server authenticated-world admission.
2. Linux native C++20+Qt6 executable tests of `admission`, encrypted `server_link`, watchdog, and client GameLink restart fixture. Shared save-world and deferred reward C++ regression fixtures must remain green.
3. An isolated Docker builder runs the **actual server verification-test target** with existing 12 suites, then builds the real disposable server and load-generator images. The five synthetic players use one isolated Docker network, with 3 enemy owners, teams of 5, 55-second test, no public ports, no real accounts, and no production Fornex access. Validate five connected/playing peers, zero refusals and nonzero packets. A synthetic client rig **is not 5 real Bloodborne players**.
4. The Windows game-free compiler B14 is an upstream separate gate. The old first-build issue repeated even after stages `net`, `gpu`, `final` each said PASS: the script exited before completion and no PE header validation ran. B14/Windows release remains red until explicit source-to-output copying diagnostic and a successful first pass.
5. A future **single** integrated artifact milestone will verify launcher, client, server, Win64 PE/DLL dependency closure, real 1.09 gameplay, 2/3/5 hunters, DBNO, hot joins, friends, privacy, invasion/duel splits, NVIDIA/AMD/Intel render and p95/p99 performance. Do not mark the project playable based only on source CI or Docker simulation.

## Release safety

No game assets, private CUSA03173/DS3 bytes, proprietary DLC, server credentials, real player saves, Fornex SSH, service restarts, download files, public binaries or production DNS changes. All work stays in a **Draft PR**. Main/release and private Drive remain untouched. For all issues and screenshots, report **source fixes, compiler checks and actual in-game validation** separately.
