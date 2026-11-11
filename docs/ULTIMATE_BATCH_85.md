# Ultimate B85 — stale local-target frame must never restart the live GameLink peer

Date 2026-11-11. **Actual playable Yharnam Together source**, branch `experiment/ultimate-batch-85-stale-target-game-link-restart-20261111` stacked on B84 #151. Inherited improvements B82 (bounded reliable resend CPU), B83 (never-sent ACK guard) and B84 (exact encoded header budget) are not removed. This is the custom YT co-op transport, not original BBSC Bells, and **not the separate no-eboot native-port mission**.

## Real source defect

Shared `server/coop/game_link.h`, compiled by client (`emulator/src/core/bloodborne_game_link.h`) and shadNet server, previously performed:

1. Observe incoming remote `frame.instance`.
2. If that number differs, invoke `RestartStreams`, potentially forgetting unacknowledged reliable world/control packets and replacing the known remote instance.
3. **Only then** reject an incoming frame with `frame.peer_instance != 0 && frame.peer_instance != local instance`, meaning a delayed frame for this game's *previous* run.

A stale datagram can arrive with a new/unrelated remote run number **but refer to the old local run**. It must not alter any current streams. Before B85 the code could reset current reliable retransmission state, zero counters, and contaminate the learned remote instance **before** discarding the stale packet. A later valid frame could induce another restart. This can manifest as join/world-head retransmission or reconnection stalls. This is a deterministic source invariant, **not** a claim of observing the bug on a live player rig.

## Minimal safe fix

Move the existing local run-target test and response ACK request before any `peer_instance` learning or stream reset. Stale packets still deliver **no inbound native game data** and still request a response to teach the sender the current run. Valid first-contact (`peer_instance == 0`) and legitimate remote restart retain their prior behavior; ACK effect, wire format, CPU budget, MTU accounting, original game packets, actual saves and server configuration unchanged.

## Regression scenarios (actual C++ production header, not a toy model)

- Establish host with genuine peer instance 2; send reliable world head seq0 and lose its ACK. Queue join hello seq1 but do **not** flush it. Inject late frame with remote instance 999, local target 123, impossible ACK 999, and inbound fake hello. Assert no delivery, no restart, both reliable packets kept.
- Receive valid ACK1 for seq0 from actual peer instance 2. Flush queued join seq1, verify its delivery by actual emulator game-link receiver and real ACK; no duplicate or reset.
- Before *any* genuine remote handshake, inject a stale frame targeting local instance 123. Verify response header has unknown peer instance 0, does not learn 999; after legitimate handshake, keepalive correctly reflects peer 2 and no restart.
- Existing B82/B83/B84 resend, multiple native entity packets, sender-wire budgets and restart/2–5 synthetic tests remain intact.
- Dedicated CI: Linux GCC+Clang C++20, Windows MSVC C++20, emulator production `GameLink` GTests C++23, source contract.

## Cross-source disposition

The [Yharnam Together documented server netcode](https://bloodborne.seamlesscoop.dev/docs/netcode) uses one UDP client-server transport, server-owned world, game's native packet channels, per-game reliable stream and fresh game-instance numbers. [Official YT source](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/blob/main/server/coop/game_link.h) was compared to actual B84 source; upstream's same ordering is a cross-source provenance point, not test evidence. [B84 external census](ULTIMATE_GLOBAL_SOURCE_SWEEP_20261111_B84.md) checked 586 upstream branch names (7 pages), own YT + port branches, relevant PRs, visy and droogie BBHost, Nightwatch, BBGL, both connected Drive accounts, issue screenshots, and public research. Branch *names* do not mean all code was exhaustively reviewed. Avoid porting P2P link mechanics into YT server-owned state without protocol comparison.

Follow-up P0 remains open: [#137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137) phantom badge/tool return after restart requires verified on-disk savedata ACK; [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) deferred boss/NPC rewards; [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) independent world progression; [#23](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/23) enemy sync; LAN/VPN, performance, launcher and HUD enhancements remain scoped. Private screenshot names/SHA mapping stay in **private gungrain Drive**, not public repository.

## Validation gate

Code/CI alone does not establish a lower ping or all fixes. Need real 2/3/5-client UDP reorder/loss/jitter, join during crash/rejoin, mismatched local run, valid remote restart, packet capture and saves integrity before any release. No production Fornex/server, retail game file, installer, or real player save altered.
