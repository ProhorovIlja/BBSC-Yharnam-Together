# Ultimate B84 — exact encoded GameLink frame budget (2026-11-11)

**Branch:** `experiment/ultimate-batch-84-variable-sender-wire-budget-20261111`, based strictly on **B83** head `fc1a1e45164791c277879f078c11d1737e916fbe`. This is the existing Yharnam Together shared client/server transport, not old BBSC Bell matchmaking.

## Production-source defect and minimal fix

`GameLinkPeer::Flush` split native game messages using `GameLinkDetail::FrameHeaderBytes = 1+1+16+4+4+4+2`. However, `EncodeGameFrame` writes a one-byte sender length and **the actual first min(sender.size(),255) UTF-8 bytes**. The fixed 16-byte estimate matched only sender IDs of precisely 16 bytes. A sender ID longer than 16 could produce an encoded frame **larger than** `Settings::frame_bytes`, increasing UDP fragmentation risk. A sender shorter than 16 could waste remaining frame capacity.

The shared header now computes `FrameHeaderBytesWithoutSender + min(self.size(), 0xFF)` when beginning each encoded frame. No protocol revision, packet changes, sequence reordering, missing enemies, ACK changes, extra thread, altered resend policy, or new launcher option. Existing intentionally oversized **single** native packets remain alone per documented policy; this change does not magically bound an entry bigger than the budget.

## Actual C++ regression coverage

- Native `server/tests/test_game_link_resend.cpp` and emulator `GameLink` GoogleTests send three *distinct* channel-4 native packets with sender lengths 0, 16, 32, 255, 300 (encoder caps sender to 255).
- `frame_bytes=96` for short names and 320 for longer names verifies the exact encoded `EncodeGameFrame(frame).size()` stays within the budget whenever a single entry fits; checks frame splits, roundtrip decode, and all three packets surviving.
- Independent oversized native packet test preserves standalone behavior.
- Dedicated GitHub Actions: Linux GCC and Clang compile/execute the actual client/server C++20 transport; Windows MSVC compiles/executes the same code; emulator C++23 GoogleTests execute the actual game-link header. Runtime-game and actual network-latency measurements are explicitly **not** claimed.

## Beyond first search result — sourced technical intake, no blind code merge

Cross-checked the existing [B83 source matrix](ULTIMATE_BATCH_83.md), [canonical cross-chat requirements](ULTIMATE_CROSS_CHAT_REQUIREMENTS_MASTER.md), actual current [official Yharnam Together](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together), upstream PRs #577/#575/#548/#566/#569/#549 and the independent [visy Windows port](https://github.com/visy/bloodborne_pc_windows_port) including [patches for forks](https://github.com/visy/bloodborne_pc_windows_port/blob/master/docs/PATCHES_FOR_FORKS.md). Independently tracked [droogie's bbhost](https://github.com/droogie/bbhost), shadPS4, Supermedo, Nightwatch, and fork/license/ABI issues. The Yharnam Together server owns team world state and forwards original game packets; independent P2P party solutions are design candidates only, not directly swappable implementations.

Google Drive gungrain account history verified under `Bloodborne — Seamless Hunt — HANDOFF / 01-HISTORY-MD` (30 prior archives before this turn's upload). The latest uploaded markdown chat was saved separately on 2026-11-11. The drive also has a **private** Discord bug-screenshot folder containing 7 PNGs plus technical intake and manifest. Preserve screenshots only in private Drive, not public GitHub, and do not claim all prior chat images are independently present until each has been reconciled against archived messages.

Follow-up cross-source gates (not implemented by B84): upstream guest item persistence #548/#566 and disk-save ACK; upstream party settings #577, friendly fire #575, enemy scaling #569, GPU frame pacing #549; visy VPN/NAT alternatives; public server onboarding, invite/join reliability, screenshot-backed bugs; real 2/3/5 hunter gameplay and loss/jitter/MTU tests. Priority to actual compatibility and reproducible defects. No production Fornex deploy, live save mutation, or public release.
