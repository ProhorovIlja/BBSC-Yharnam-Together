# Ultimate B90 — GPU virtual/physical range and split-source safety

Date: 2026-11-11. Base: B89 [Draft #156](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/156). This changes the existing **playable Yharnam Together Ultimate** `bbport/gpu/layer` memory module. It preserves YT's own custom co-op (no original BBSC Bell matchmaking), earlier B82–B89 reliability/performance fixes, and keeps the independent no-eboot native PC port separate.

## Evidence-backed cause analysis — what is and is NOT known

The independent [deadinside28/bloodborne_pc v0.7 change log](https://github.com/deadinside28/bloodborne_pc/blob/main/docs/CHANGES_0.7.md) reports stretched Hunter's Dream railings caused by a vertex buffer crossing two parts of a grown GPU heap. [shadPS4 #1232](https://github.com/shadps4-emu/shadPS4/issues/1232) reports a separate FaceGen-associated vertex explosion path. The current Ultimate already has `GpuMemory::ResolvePrefix` / `ResolveInPlace` which refuse to bind a range crossing **different physical guest sources** as a *single* Vulkan buffer. Hence the deadinside fix must NOT be transplanted blindly. We located **a distinct verified source arithmetic defect** in that same production module.

Before B90, the original `GpuMemory::Resolve` computed `va + size - 1` and `va + size` without overflow protection. An invalid draw with a very high VA and oversized length can wrap the address range and make block/mirror searches appear to refer to unrelated low addresses. `GpuMemory::ResolvePrefix`, `ForEachInPlace` and source/mirror lookup also used `base + size` additions that could wrap for improperly declared ranges. A wrapped buffer offset must be rejected instead of becoming a Vulkan bind/copy that reads the wrong buffer. This is a deterministic source-level safety gap; the observed in-game user vertex explosion has **not** been reproduced or attributed to this arithmetic error.

## Production changes

- `bbport/gpu/layer/bblayer_gpu_memory.h` includes an inexpensive constexpr `GpuMemory::AddressRangeFits(start,size)` check; `ForEachInPlace` declines any wrapped range instead of iterating across an overflowed endpoint; physical-source clipping uses subtraction after verifying the source contains the starting address.
- `bbport/gpu/layer/bblayer_gpu_memory.cpp::ResolvePrefix` and `Resolve` reject wrapped guest address requests **before** calculating mirror blocks, offsets or binds. `AddGuestSource` and `AddMirror` reject zero-sized and overflowing source registrations; mirror containment and overlap checks are written as offset-and-subtraction comparisons rather than `base+size` that can overflow.
- `bbport/gpu/shadps4/video_core/buffer_cache/buffer_cache_layer.cpp::BufferCache::LayerMirrored` was found to **bypass `GpuMemory::Resolve`** and do `addr + size - 1` directly on the high-frequency cache lookup path. B90 applies the same fail-closed `AddressRangeFits` check before any mirror-block computation or memo use. The dedicated CI source contract checks this exact production call-site order; complete Vulkan renderer compilation remains a separate build gate.
- Preserves existing behavior for valid ranges, including **contiguous guest VA mappings that stay within one physical source**, split VA across **two distinct Vulkan buffers** (must return `Mixed` and two spans), and a fully valid mirror that ends before requested geometry.
- No GPU synchronization fences, readback-policy changes, extra per-frame heap allocations, forced shader-cache purge or new GPU settings; the added hot-path checks are constant-time integer guards.

## Test rigor

`bbport/tests/test_gpu_memory_boundaries.cpp` compiles **actual production** `GpuMemory` (not a duplicate resolver) with a minimal **test-only opaque Vulkan type header** `bbport/tests/test_support/vulkan/vulkan_core.h`. Vulkan is not initialized and no GPU is claimed tested. Cases: contiguous VA mappings, split physical chunks (do not merge), address overflow (reject), registration with wrapped physical source/mirror (reject), legitimate near-max physical source (clip at its size) and valid/overflowed mirror residency (do not bind beyond backing buffer).

`.github/workflows/ultimate-batch-90-gpu-range-boundaries.yml` runs this real C++ test under Linux GCC/Clang and Windows MSVC, plus a source-call-site contract. Dedicated workflow CI is **NOT** the same as compiling the full Windows client or running real Bloodborne on NVIDIA/AMD/Intel.

## Remaining P0 and performance scope

- Distinguish in the real game: FaceGen stale GPU readback (already `BB_READBACKS=Relaxed` default in this Ultimate source); split-heap geometry from another renderer; invalid PM4 packet guard B89; null V# handling B01. Capture original unmodded 1.09 Bloodborne and specific map/entity/driver, RenderDoc/Vulkan validation, p50/p95/p99 frametimes, Vulkan device loss, GPU VRAM/RSS and retry map reload/1-2 hours. No claim B90 fixes the observed vertex explosion without reproducing.
- NVIDIA Reflex still requires a real capability-checked SDK backend, not a fake checkbox; DLSS/FG performance and input-to-photon measurements must be separately verified.
- Network B82–B89's resend, ACK, stale-frame and co-op SendPace changes remain. Actual dedicated server CPU, 2–5-player RTT/loss/jitter, reconnect and stable session/savedata rigs remain to be measured.
- [Graphics issue #25](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/25), [collision #75](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/75), HomeWorlds P0 #22, guest chest #73, deferred boss/NPC reward #35 and phantom savedata-ACK #137 are **open**, not marked fixed by this PR.
- Detailed [B89 cross-source audit](ULTIMATE_PERFORMANCE_GRAPHICS_NETWORK_SOURCE_AUDIT_20261111.md) and [cross-chat requirement ledger](ULTIMATE_CROSS_CHAT_REQUIREMENTS_MASTER.md) remain the cumulative record. Branch/fork name discovery is not comprehensive diff analysis.

No real player save files, decrypted game assets, installer, private Discord screenshots, credentials or live Fornex production services were read/altered for this change. Keep PR Draft until target Windows full build and GPU/game rig testing.
