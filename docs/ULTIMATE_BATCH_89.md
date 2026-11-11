# Ultimate B89 — malformed PM4 draw/dispatch protection in the actual graphics command processor

Date: 2026-11-11. Stacked on B88 [Draft #155](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/155). This is the existing **Yharnam Together Ultimate** source, including the bundled `bbport/gpu` runtime and launcher, not the wholly separate future no-eboot native Windows port. No fallback to old BBSC Bell co-op.

## Actual source defect in Ultimate

`bbport/gpu/cp/cp_decoder.cpp::Cursor::Next` correctly rejects a Type-3 PM4 packet if its *declared* total size runs beyond the command buffer. But before B89 it did **not** check that the declared body has enough operands for the opcode which follows. `Packet::Word(i)` deliberately returns zero for a missing operand, so a Type-3 draw/dispatch/indirect command containing fewer than its required words could be silently interpreted as a valid-looking command with fabricated zero values, alter graphics registers or reach the render sink. This is an actual deterministic source contract gap; no GPU/model user reproduction is claimed.

## Precise fix

`MinimumDecodedBodyWords(Op)` now rejects these actual decoded opcodes when they have too few words: `DrawIndex2` (5), `DrawIndexOffset2` (4), `DrawIndexAuto` (2), `IndexBase` (2), `DispatchDirect` (4), `DispatchIndirect` (2), `IndirectBuffer` (3), `CondExec` (3). Unknown/variable-length opcodes are not assigned guessed minimum sizes and retain the parser's existing behavior. This check runs inside `Cursor::Next`, **before** register writes, `OnPacket`, `OnDraw`, `OnDispatch` or indirect-buffer resolution. One small switch, no new allocations, no GPU sync, no external libraries or shader cache invalidation.

`bbport/tests/test_cp_decoder.cpp::MalformedDrawAndDispatchOperands` now injects each short command (whose own PM4 header length is internally consistent) followed by a valid draw, then verifies: 1 bad packet; **zero** phantom draws, dispatches or indirect buffers; **zero** registered or externally reported packets; no modified index/base registers; a scoped diagnostic; later commands are not executed. It repeats the check through both `Decode` and the direct `Cursor` API. Previously existing positive tests for valid draw/dispatch, nested indirect buffer, register changes, CLEAR_STATE and conditional execution remain.

Dedicated CI compiles and **runs this production CP decoder** with actual unit tests on GCC, Clang and Windows MSVC. Compiling a test is not proof of fixes to renderer/Vulkan/shader cache in-game, frame-time improvements, or actual vertex artifacts.

## Requested broad Ultimate quality and performance constraints

[Cross-project source audit and measurable roadmap](ULTIMATE_PERFORMANCE_GRAPHICS_NETWORK_SOURCE_AUDIT_20261111.md) covers:

- Vertex cache / FaceGen explosions vs stale GPU-visible vertex data and separate heap-chunk boundary bugs; actual baseline-specific reproduction, GPU memory barriers, readbacks, artifacts, cached shader pipeline.
- NVIDIA Reflex as a **real optional SDK integration task**, not a fake checkbox: Windows/NVAPI/Streamline backend, GPU-capability negotiation, render thread marker and sleeping placement, framegen compatibility, test input-to-photon and p99 frame pacing. FSR/DLSS and FG in a different engine fork may not be directly transferable. No license-invalid binary redistributions.
- CPU/GPU memory and leakage over 1–2 hours, Vulkan device-loss, renderer parallelization, pipeline compilation, texture/geometry streaming, ring-buffer lifetime after presentation, VRAM under pressure. Preserve low-end fallbacks and opt-in risky modes.
- Network: RTT/jitter/p95/p99, B82 reliable resend overhead, B83 ACK, B84 actual frame encoding budget, B85 stale old-run frames, server-owned world low packet-rate sync, 2–5 hunter loss/reorder tests; avoid trading network smoothness for extra bandwidth and CPU.
- Launcher: startup/exit critical path, unblock Tk GUI, multiple profiles, cache/settings validation, reliable update/rollback and no scan of huge folders on each keystroke; no contradictory settings.
- Production gates: reproducible clean/modded 1.09 test, 9 CUSA regions, GPUs NVIDIA/AMD/Intel, Windows/Linux, measured `p50/p95/p99` frametimes/RTT, CPU/RSS/VRAM use, save checks, crash/reconnect and security controls. **Zero change to live Fornex/player saves**.

### Not yet fixed

The user's reported graphical missing floors, vertex explosions, stutters, random freezes and source-specific frame-gen leakage are not declared solved by this PM4 guard. Relevant source causes are different and need scene/driver/capture validation. Compare [original GPU-issue #25](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/25) and [map-collision issue #75](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/75). A full renderer replacement is **not** a safe cherry-pick: eFMann shadPS4 0.21 threaded Vulkan renderer has a very different cache API from the bundled Ultimate emulator/port tree. Original [deadinside28 renderer](https://github.com/deadinside28/bloodborne_pc) and independent [droogie BBHost](https://github.com/droogie/bbhost) use different internal code and/or network stacks. Compare precise function semantics first; test and verify licensing before any transfer.

**Release remains blocked** until all required native Windows build, renderer P0, save-integrity and game-rig gates are actually passed. Draft PR and CI green means source improvement, not final Ultimate quality.
