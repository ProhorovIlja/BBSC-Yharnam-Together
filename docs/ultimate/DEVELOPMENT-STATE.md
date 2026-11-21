# Yharnam Together — development state

Last reviewed: **2026-11-21 UTC**. This file is a navigational snapshot of verified source changes, not a product-completion or live-deployment assertion. Update it when PRs land, tests change, or acceptance evidence is added. The authoritative record remains GitHub PRs/issues and their exact CI runs.

## Current mission

Focus on the **existing playable launcher + game client + ShadNet server**, not the experimental no-eboot native port. Preserve game and player save data. The playable target is Bloodborne 1.09 with multiple retail regions, up to five co-op hunters, separate duel/invasion compositions, hybrid direct encrypted P2P with relay fallback, and server-authoritative sync-critical events. Treat these as requirements until actual end-to-end testing proves them.

## Landed in main

| PR | Scope | Evidence | Important limit |
|---|---|---|---|
| [#285](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/285) | Copied-installation local/server IDs separated | Windows/Ubuntu regression reported in PR | Two installed clients still unverified; issue #284 open |
| [#286](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/286) | Atomic individual co-op settings/rules migration | Windows/Ubuntu CI reported in PR | Cannot prove all older profiles |
| [#287](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/287) | Typed coop.json, shared firewall deadline and UTF-16 output | [Run 44942761070](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/44942761070) | No installed Windows firewall/UAC acceptance |
| [#288](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/288) | Local server Start/Stop serialization, stale UI results, PLAY recovery | [Run 44943292921](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/44943292921) | No measured actual game startup/Alt+F4 |
| [#289](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/289) | HTTPS account-response validation, 64 KiB cap, robust form recovery | [Run 44943777708](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/44943777708) | Real public auth/TLS acceptance pending |
| [#291](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/291) | Unicode desktop .lnk via Win32 Shell Link (no interpolated PowerShell), source --play | [Run 44945230305](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/44945230305) and launcher matrix 44945230156; merge `d73be73` | Installed Windows shortcut launching game unverified |
| [#292](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/292) | Suppress POSIX SIGPIPE on local RPC sends, keep EPIPE failure handling | [Run 44945495461](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/44945495461); merge `ba2bb24` | Linux real socketpair regression, not retail game or macOS runtime |
| [#290](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/290) | Retire stale server RPC tunnels/queued TCP on lost/gone/replaced authenticated endpoint | [Tests 44945018137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/44945018137), [Docker image 44945018142](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/44945018142); merge `34d01ac` | Retail encrypted game-client replacement and VPS staging unverified; #282 open |
| [#294](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/294) | Validate portable ZIP/download, unique staging, install locking and per-file atomic copy | [Windows/Ubuntu 44946292005](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/44946292005); merge `f58cbf9` | Whole installation rollback and installed update unverified; #283 deliberately open |
| [#295](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/295) | Bound local RPC TCP sends to stuck game readers; retain SIGPIPE protection | [Windows/Linux 44946482482](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/44946482482); merge `0ea481e` | Source/socket tests only, not live 1.09 login, half-close or client exit |
| [#296](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/296) | POSIX `poll` instead of unsafe `FD_SET` on high client descriptors | [Ubuntu/macOS 44946739699](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/44946739699); merge `9dad2ae` | In-game high-FD/stress behavior unverified |

## Active work and release gates

- [#278](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/278) **draft**, larger client/server RPC backpressure/lifecycle stack; do not wholesale merge without full compatibility review, 1.09 game sign-in, half-close/reconnect tests.
- [#275](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/275) **draft/stacked**, launcher UI, portable updates and other fixes; merge only independent tested backports where appropriate. #291 was an independent backport.
- [#265](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/265) **draft**, guest reward/phantom ledger safety. Filesystem unit tests do **not** show item committed in actual 1.09 save. Never silently replay uncertain grants or alter original saves.
- **No production VPS cutover, published release, Windows installer acceptance, or five-client encrypted gameplay acceptance was performed by these commits.** Before publishing or deploying: exact manifest and client/server fingerprints, clean account/TLS, save-slot isolation and crash recovery, five-hunter replication/boss/wipe, region matrix, rollback rehearsal, owner approval.

## Priority queue

Read [ISSUE-TRIAGE.md](ISSUE-TRIAGE.md) for issue ownership/duplication/closure gates. Start with P0 data integrity: own-world progression, private save slot and guest rewards; then player visibility/hot join/AI, authenticated networking and disconnect, launcher start/update/TLS, and benchmark-driven performance. Use representative upstream repos (Amanises YT, droogie bbhost, deadinside/Supermedo bbport, shadPS4, Nightwatch, LanternEngine) for compatible evidence, never blindly mix engines, wire formats, licenses, or proprietary assets.

## Continuity

Private user-authorized research, bug registry and full conversation archive are held in restricted Google Drive, **not** in this public repository. Never copy secrets, screenshots, personal data, retail game/DS3 assets, encrypted save content or raw private reports into GitHub. Link only sanitized public tickets, pinned source revisions, reproducible tests and CI. When information is incomplete, record *unverified*, not *fixed*.
