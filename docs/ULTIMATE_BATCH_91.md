# Ultimate B91 — last-page GPU span enumeration must terminate

Date: 2026-11-11. Base is B90 [Draft PR #157](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/157), retaining the full B82–B90 work. This is the **existing playable Yharnam Together Ultimate**, not the old BBSC Bell flow, and not a claim to have finished the separate no-eboot native port.

## Reproduced from actual code, not a generic GPU optimization claim

`bbport/gpu/layer/bblayer_gpu_memory.h::GpuMemory::ForEachInPlace` walks every piece of a valid 64-bit guest GPU virtual-address range. B90 added protection against **wrapped request ranges**. But a request that legitimately ends at `UINT64_MAX`, starting in the final **4-KiB page**, passes that check. When the guest translation fails (unmapped VA), the pre-B91 fallback computed:

`std::min(end, (at | 0xfff) + 1)`

When `at | 0xfff == UINT64_MAX`, adding 1 wraps to zero. The iteration callback receives an invalid underflowed size and the loop moves `at = 0`, meaning it can scan an unrelated low address space or hang indefinitely. This bug was missed by B90 because its high-VA test used a **wrapped** request, which is rejected earlier. The new B91 tests exercise **non-wrapped** requests within the highest page.

No user gameplay capture proves that normal Bloodborne 1.09 graphics actually generates such near-maximum VA. This is a deterministic arithmetic/forward-progress correctness issue and a potential invalid-input hang, **not** evidence that all reported FaceGen vertex explosions, GPU crashes, missing floors or freezes have been fixed.

## Exact implementation

- In `bbport/gpu/layer/bblayer_gpu_memory.h::ForEachInPlace`, after a failed address translation, obtain `page_last = at | u64{0xfff}` and choose `next = (page_last < end ? page_last + 1 : end)`. This safely clips to the valid **exclusive** end without ever calculating `UINT64_MAX + 1`. The loop always advances for `at < end`; it cannot wrap or issue a callback spanning an incorrect lower memory region. No extra allocations, Vulkan barriers, readbacks or synchronizations.
- The **real** `bbport/tests/test_gpu_memory_boundaries.cpp` (using actual compiled production `GpuMemory`, test-only opaque Vulkan handles) now checks an unmapped 31-byte valid interval in the highest page: exactly one `Span{nullptr,0,max-31,31}`, never a low-address callback or wrap. Another valid interval crosses the penultimate and highest pages: exactly two monotonic callbacks (16 and 4095 bytes). Also confirms no callback for zero size and rejection of a truly overflowed request. Earlier B90 contiguous/split sources/mirror-boundary tests stay intact.
- New `.github/workflows/ultimate-batch-91-top-page-forward-progress.yml` compiles and runs **real** C++ module under Linux GCC and Clang with undefined-behavior sanitizer plus Windows MSVC. Both platforms have explicit per-executable timeouts/watchdogs so that an inadvertently regressed infinite loop fails quickly. Existing B90 production test workflow and B89 GPU/SendPace workflow are inherited on this branch.

## Validation and remaining tasks

Code source contracts and native tests are reproducible, but **full target Windows client and Vulkan driver/GPU/gameplay rig are distinct**. Require 1.09 clean+modded GPU captures for NVIDIA/AMD/Intel, source-specific FaceGen/buffer-cache reproductions, VRAM/RSS growth, frame-time p50/p95/p99, input-to-photon measurement, renderer device-loss logs and 2–5-player connection quality before treating the user-requested Ultimate performance/stability outcome as complete.

Reflex requires genuine optional NVIDIA SDK / Streamline / NVAPI integration plus capability check; it is not enabled by B91. Existing YT co-op networking/SendPace, launcher settings and gameplay save issues [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22), [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35), [#73](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/73), [#137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137), rendering [#25](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/25) and collision [#75](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/75) remain independent release gates. Do not assume a source guard actually eliminates in-game bug reports without real reproduction.

Reference: [B90 mapped GPU source test and cross-fork provenance](ULTIMATE_BATCH_90.md), [B89 GPU/CPU/network performance-source audit](ULTIMATE_PERFORMANCE_GRAPHICS_NETWORK_SOURCE_AUDIT_20261111.md), [cross-chat requirements master](ULTIMATE_CROSS_CHAT_REQUIREMENTS_MASTER.md). Direct source review of the precise call site here; no false claim to have reviewed every GitHub fork/branch or every internet page.

No live Fornex deployment or restart, no real game/player saves, private Discord screenshots, installers, decrypted game assets, or release binaries changed. Keep Draft until all checks pass.
