// SPDX-License-Identifier: GPL-2.0-or-later
// B90: execute production BbLayer::GpuMemory with Vulkan handles as opaque types.
// No GPU driver, real Bloodborne assets, save files or network involved.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <vector>

#include "bblayer_gpu_memory.h"

using u64 = std::uint64_t;
using BbLayer::GpuMemory;
using BbLayer::Span;
using BbLayer::Resolution;

namespace {
bool Translate(u64 va, u64* phys, u64* end) {
    if (va >= 0x1000 && va < 0x1080) {
        *phys = 0x2000 + (va - 0x1000);
        *end = 0x1080;
        return true;
    }
    if (va >= 0x1080 && va < 0x1100) {
        *phys = 0x2080 + (va - 0x1080);
        *end = 0x1100;
        return true;
    }
    if (va >= 0x1100 && va < 0x1200) {
        *phys = 0x3000 + (va - 0x1100);
        *end = 0x1200;
        return true;
    }
    if (va >= 0x4000 && va < 0x4100) {
        // Synthetic source close to the 64-bit end: its base+size would
        // wrap even though every requested byte lies inside the source.
        constexpr u64 base = std::numeric_limits<u64>::max() - 0xff;
        *phys = base + (va - 0x4000);
        *end = 0x4100;
        return true;
    }
    return false;
}
}

int main() {
    constexpr auto max = std::numeric_limits<u64>::max();
    static_assert(!GpuMemory::AddressRangeFits(max - 4, 10));
    static_assert(GpuMemory::AddressRangeFits(max - 4, 4));
    static_assert(GpuMemory::AddressRangeFits(0, max));

    GpuMemory& gpu = GpuMemory::Get();
    gpu.SetTranslate(&Translate);
    gpu.SetBlockShift(4);
    gpu.AddGuestSource(0x2000, 0x100, VK_NULL_HANDLE, 0, nullptr);
    gpu.AddGuestSource(0x3000, 0x100, VK_NULL_HANDLE, 0, nullptr);

    // Adjacent guest mappings that remain contiguous in physical memory
    // are one source; no extra draw splitting needed.
    auto span = gpu.ResolveInPlace(0x1070, 0x30);
    assert(span && span->source && span->va == 0x1070);
    assert(span->offset == 0x70 && span->size == 0x30);
    assert(gpu.Resolve(0x1070, 0x30).kind == Resolution::Kind::InPlace);

    // Crossing two *different* guest Vulkan buffers must never return a
    // single bindable GPU span (a known source of stretched geometry).
    auto prefix = gpu.ResolvePrefix(0x10f0, 0x30);
    assert(prefix && prefix->size == 0x10 && prefix->offset == 0xf0);
    assert(!gpu.ResolveInPlace(0x10f0, 0x30));
    assert(gpu.Resolve(0x10f0, 0x30).kind == Resolution::Kind::Mixed);
    std::vector<Span> pieces;
    gpu.ForEachInPlace(0x10f0, 0x30, [&](Span s) { pieces.push_back(s); });
    assert(pieces.size() == 2);
    assert(pieces[0].source && pieces[0].offset == 0xf0 && pieces[0].size == 0x10);
    assert(pieces[1].source && pieces[1].offset == 0 && pieces[1].size == 0x20);

    // After synthetic address overflow no wrapped GPU binding or callback
    // is allowed; the decoder must not interpret a high address as low VRAM.
    assert(!gpu.ResolvePrefix(max - 4, 10));
    assert(!gpu.ResolveInPlace(max - 4, 10));
    assert(gpu.Resolve(max - 4, 10).kind == Resolution::Kind::None);
    bool invoked = false;
    gpu.ForEachInPlace(max - 4, 10, [&](Span) { invoked = true; });
    assert(!invoked);

    // B91 regression: a mathematically valid range can end inside the
    // highest 4KiB virtual page. The old unbacked-VA fallback computed
    // (at | 0xfff) + 1, wrapped to zero, and failed to make forward progress.
    // Do not hang, iterate from VA 0 or fabricate a GPU-buffer span.
    std::vector<Span> top_page;
    gpu.ForEachInPlace(max - 31, 31, [&](Span s) { top_page.push_back(s); });
    assert(top_page.size() == 1);
    assert(top_page[0].source == nullptr && top_page[0].va == max - 31);
    assert(top_page[0].offset == 0 && top_page[0].size == 31);

    // Cross the penultimate/highest page: precisely two monotonically
    // advancing callback spans, no wrap, no additional low-address read.
    std::vector<Span> final_pages;
    gpu.ForEachInPlace(max - 0x100f, 0x100f, [&](Span s) {
        assert(final_pages.size() < 3);  // fail rather than silently loop
        final_pages.push_back(s);
    });
    assert(final_pages.size() == 2);
    assert(final_pages[0].source == nullptr &&
           final_pages[0].va == max - 0x100f && final_pages[0].size == 16);
    assert(final_pages[1].source == nullptr &&
           final_pages[1].va == max - 0xfff && final_pages[1].size == 0xfff);
    assert(final_pages[0].va + final_pages[0].size == final_pages[1].va);
    assert(final_pages[1].va + final_pages[1].size == max);

    // The zero-size request must not produce any callbacks, including at
    // the last possible address. An overflowed request is still rejected.
    std::size_t unexpected_callbacks = 0;
    gpu.ForEachInPlace(max, 0, [&](Span) { ++unexpected_callbacks; });
    gpu.ForEachInPlace(max - 31, 33, [&](Span) { ++unexpected_callbacks; });
    assert(unexpected_callbacks == 0);

    // A wrapped source must NOT get into the address map. A legal source
    // close to UINT64_MAX still splits safely at its actual last byte.
    gpu.AddGuestSource(max - 0x7f, 0x100, VK_NULL_HANDLE, 0, nullptr);
    assert(gpu.GuestSource(max - 0x7f) == nullptr);
    gpu.AddGuestSource(max - 0xff, 0xf0, VK_NULL_HANDLE, 0, nullptr);
    auto high = gpu.ResolvePrefix(0x4000, 0x50);
    assert(high && high->offset == 0 && high->size == 0x50);
    auto high_end = gpu.ResolvePrefix(0x40e0, 0x20);
    assert(high_end && high_end->offset == 0xe0 && high_end->size == 0x10);

    // One resident mirror cannot bind past the end of its own backing
    // Vulkan buffer even when the adjacent block is valid elsewhere.
    gpu.AddMirror(max - 0x7f, 0x100, VK_NULL_HANDLE, 0, nullptr);
    assert(!gpu.MirrorAt(max - 0x70));
    gpu.AddMirror(0x5000, 0x100, VK_NULL_HANDLE, 0, nullptr);
    gpu.MarkValid(0x5000 >> 4, 0x5100 >> 4);
    auto mirror = gpu.Resolve(0x5050, 0x20);
    assert(mirror.kind == Resolution::Kind::Mirror);
    assert(mirror.span.offset == 0x50);
    // A valid run above the mirror does not expand the mirror itself.
    gpu.MarkValid(0x5100 >> 4, 0x5120 >> 4);
    assert(gpu.Resolve(0x50f0, 0x30).kind == Resolution::Kind::Mixed);
    assert(gpu.Resolve(max - 4, 10).kind == Resolution::Kind::None);

    std::puts("B90_PRODUCTION_GPU_MAPPED_RANGE_BOUNDARIES_PASS");
}
