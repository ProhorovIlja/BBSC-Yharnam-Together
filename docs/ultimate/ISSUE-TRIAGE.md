# Playable edition — issue triage and closure rules

Snapshot date: **2026-11-21**. This is a non-exhaustive, actionable index of existing public issues and acceptance gates. The owner-authorized private register is larger and remains private; this file neither duplicates its raw reports nor claims to have reproduced every case.

| Priority | Public issues | Current evidence and remaining action |
|---|---|---|
| **P0 — personal progression/saves** | [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22), [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35), [#72](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/72), [#137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137) | Test separate character/slot generations and host/guest worlds through travel, unique pickup, crash, save reload. #265 is a draft, not proven 1.09 savedata durability. |
| **P0 — hunter visibility, hot-join/NPC state** | [#21](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/21), [#23](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/23), [#63](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/63) | Use actual five-client 1.09 cases in Dream, late join, boss wipe, travel, DLC and chalice. Distinguish missing actor from rendering or collision. Existing screenshot/issue triage covers reports; do not create duplicates by symptom alone. |
| **P0 — TLS and authorization** | [#24](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/24), [#280](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/280) | #289 merged and synthetic TLS tests passed; reproduce successful and failed sign-in against authorized live test account/server, including certificate chain and redirects. |
| **P1 — RPC session/half-close/reconnect** | [#279](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/279), [#281](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/281), [#282](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/282) | #290 and #295–#296 merged for server session retirement, bounded local sends and POSIX high-FD readiness; #278 remains the draft end-to-end client integration. Still need real encrypted backend, slow ACK, half-close, old-vs-new session, shutdown and five-hunter reconnect. |
| **P1 — launcher startup/install/update** | [#77](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/77), [#192](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/192), [#242](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/242), [#283](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/283), [#284](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/284) | Source fixes #285–#289, #291 and #294 merged. #283 was reopened after automatic closure: no installed portable update or full transactional rollback yet. Need packaged Windows launch, non-Latin paths, preserved saves/mods and exact rollback, two independent machines for copied identity. |
| **P1 — netcode goals and load** | [#3](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/3), [#9](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/9), [#80](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/80) | Preserve Hosted=false where specified; measure direct-vs-relay routing, packet loss, p95/p99 frametime and latency before claiming optimization; do not replace proven transport with incompatible upstream protocol. |

## When to change an issue

1. **New issue only for a distinct, reproducible defect** absent from existing issue bodies or the private register; link symptoms to an umbrella instead of duplicating it.
2. Every claimed fix needs a pinned build/SHA, regression or gameplay reproduction, affected platform, severity and scope. Distinguish **candidate**, **source-tested**, **merged**, **packaged**, **installed**, and **live-verified**.
3. **Close as completed** only when the exact acceptance criteria are fulfilled and linked to reproducible evidence. Merged source alone does not justify closing a broad issue requiring installed game, five players, or save-durability confirmation.
4. Mark actual duplicates with a pointer to the canonical tracker; do not delete issue history and do not publish private evidence. If no safe reproduction exists, retain the issue with precise blockers rather than claiming fixed.
5. Never deploy production, edit player saves or expose private archival sources as a side effect of issue triage.

## Near-term verification checklist

- Windows packaged launcher: PLAY versus OPEN LAUNCHER parity, Cyrillic/Greek/CJK paths, Unicode shortcut, update and rollback, offline mode.
- Real account flow: TLS chain, valid/invalid passwords, 64 KiB error handling, login after server outage, reconnect, no leaked secrets.
- Five co-op hunters: boss wipe, late join, invisibility, revive/spectator UI, AI/quest flags, Travel Together and personal-world restoration.
- Persistent rewards: character/slot identity, partial write and crash, save acknowledgement, 1.09 real disposable saves, no duplicate key items.
- ShadNet: ordered 512 KiB RPC reply after stalled ACKs, TCP half-close, session replacement, direct P2P/relay failover, actual deployed test endpoint only.
