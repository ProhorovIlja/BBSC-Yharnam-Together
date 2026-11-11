# Ultimate B93 — bounded GPU/VRAM idle-use tracking, zero-length and invalid range isolation

Date: 2026-11-11. Stacked on [B92 Draft #159](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/159). This changes the **existing Yharnam Together Ultimate** integrated BBPort Vulkan renderer/graphics memory layer. The YT native co-op system and cumulative B82–B92 source improvements are retained. The independent no-eboot Windows port remains a separate effort.

## Observed production source defect

Source `bbport/gpu/shadps4/video_core/buffer_cache/buffer_cache_layer.cpp::BufferCache::NoteDirectUse` tracks when groups of 2 MiB of copied VRAM were last directly bound, to prioritize recycling older idle mirrors under GPU memory pressure. Prior to B93 it computed:

```cpp
const u64 last = std::min<u64>((address + size - 1) >> USE_GROUP_BITS, layer_group_use.size() - 1);
for (u64 group = address >> USE_GROUP_BITS; group <= last; ++group) {
    layer_group_use[group] = now;
}
```

The function did not check `size == 0`, the finite table's emptiness or arithmetic overflow. A **zero-length** range with `address == 0` makes `address + size - 1` underflow to `UINT64_MAX`. If the table is initialized, this can touch **every entry** despite no actual VRAM usage, penalizing the CPU and making *genuinely unused VRAM groups appear recently used* during memory-pressure eviction. If the table is empty, `size()-1` also underflows and indexing it risks an out-of-bounds access. An invalid high-range request can otherwise produce a truncated or wrong group count. This is a deterministic source-level fault; it is **not** a claim that the game currently calls `NoteDirectUse(0,0)` during normal gameplay or that actual stutters were reproduced.

Related VRAM-idle scans in `LayerProcessIdle` and `LayerYieldToImages` indexed `group_use[group]` / `layer_group_use[group]` without bounds checks. A malformed or stale guest GPU valid-block range exceeding the initialized table could access an invalid group index or fail to make progress if an overflowing block-boundary calculation returned `group_end <= block`. Those call sites now conservatively stop scanning the invalid portion rather than risking a crash or an infinite scan.

## Precise B93 changes

- Add an inexpensive **real production** constexpr `GpuMemory::GroupRangeForBytes(address,size,group_shift,group_count)` beside B90/B91's existing `AddressRangeFits` in `bbport/gpu/layer/bblayer_gpu_memory.h`. Returns no groups for empty, overflowing or invalid address ranges, shift >=64, missing table or a first group outside the table; otherwise returns an inclusive pair clamped to the actual finite table size. This is a pure helper, no heap allocation and no new GPU fence/readback.
- `BufferCache::NoteDirectUse` calls this exact production helper before any entry access. Valid two-MiB groups are visited exactly as before; no zero-length wakeups. Ordinary valid render bindings incur only a few constant-time checks.
- `BufferCache::LayerProcessIdle` and `LayerYieldToImages` check the available table size and forward progress `group_end > block` before indexing an idle-use group. A malformed range is skipped conservatively; this does not eagerly evict unverified VRAM data.
- Actual compiled `bbport/tests/test_gpu_memory_boundaries.cpp` now includes constexpr and runtime regression cases: 10,000 empty/overflowed requests (zero group writes), group crossing (exact two entries), clipping at last tracked group, out-of-range first group, empty table, invalid shift, near-maximum 64-bit byte addresses. Inherits all previous B90 GPU bounds, B91 last-page no-hang and B92 source/mirror overlap tests.
- Dedicated `.github/workflows/ultimate-batch-93-gpu-idle-use-bounds.yml` source-checks the precise real renderer call sites, then compiles/executes **the actual production GpuMemory module** plus the enlarged tests under Linux GCC+Clang UBSan and Windows MSVC with a timeout/watchdog. The renderer itself remains compiled by cumulative full Windows native-client CI, not by this test-only opaque Vulkan stub compilation.

## Why this improves stability without fabricated claims

It eliminates a definite **zero-byte range underflow and unwanted table-work mechanism** and prevents idle-group indexing outside a finite table. The new helper does not alter real VLAN/Vulkan buffer contents, shader compilation, renderer concurrency policy, GpuReadbacks default (`Relaxed`), DLSS/FSR, game save data or team co-op. It is not a measured CPU/FPS/VRAM improvement until profiling on a real game build. NVIDIA Reflex still requires genuine SDK/Streamline/NVAPI integration and latency markers; do not advertise it as already available.

### Separate source concern retained (not silently declared solved)

B92's overlap rejection `GpuMemory::AddMirror` returns `void`; the renderer can enqueue its own mirror after an invalid request without observing registration failure. Normal renderer call sites remove old sources before merging and should satisfy the overlap contract. However a genuinely malformed overlap would need **explicit registration success signaling and recovery/rollback** to keep renderer-owned `layer_mirrors` and `GpuMemory::mirrors` synchronized. Do not assume B93 resolves that remaining failure-reporting design issue. It needs source review and failure-injection tests before release.

## Actual release gates

- Real graphics and FaceGen validation: Bloodborne 1.09 clean/modded, identical save copies/hardware, NVIDIA/AMD/Intel drivers, cold/warm shaders, scene-specific vertex explosions/missing floors, Vulkan validation/RenderDoc traces and device-loss inspection, p50/p95/p99 frametimes, VRAM/RSS slope and 1–2-hour sessions. Compare [shadPS4 FaceGen/readback findings](https://github.com/shadps4-emu/shadPS4/issues/1232), [readback tradeoffs](https://jackblazes.net/posts/2025-03-19-bloodborne.html), [deadinside v0.7 split-heap note](https://github.com/deadinside28/bloodborne_pc/blob/main/docs/CHANGES_0.7.md) and [B89 performance audit](ULTIMATE_PERFORMANCE_GRAPHICS_NETWORK_SOURCE_AUDIT_20261111.md). Independent fixes are not interchangeable without exact code/ABI/license compatibility.
- Preserve correct custom YT coop (not BBSC Bells), and verify 2/3/5 players with latency, packet loss, FPS, CPU/RSS and save/quest/item progression. [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22), [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35), [#73](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/73), [#137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137), [#25](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/25), launcher [#77](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/77) remain open P0/P1.
- Cumulative full Windows client executable must pass at B93 head, not merely prior B91 [full-build SUCCESS](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/43029937031). Dedicated native tests are **game-free** and are not proof of hardware results.
- Production Fornex and original player saves, game assets, private screenshots/Discord, credentials and installer/release binaries remain untouched. All PRs stay Draft. Scope is a regression-safe quality step, **not an already complete Ultimate**.
