// SPDX-License-Identifier: GPL-2.0-or-later
// Executes the extracted production CPU HLE function. The interfaces below are test doubles;
// they record reads, copies and dirty ranges. No Vulkan driver or actual GPU synchronization.
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <span>
#include <utility>
#include <vector>
#include "bbport_copy_shader.h"
using u32 = std::uint32_t;
using u64 = std::uint64_t;
using VAddr = u64;
constexpr u64 operator""_KB(unsigned long long n) { return u64(n) * 1024; }
template<class... T> void Log(T&&...) {}
#define LOG_WARNING(...) Log(__VA_ARGS__)
#define LOG_TRACE(...) Log(__VA_ARGS__)
constexpr int Render_Vulkan = 0;
namespace vk {
using DeviceSize = u64;
struct BufferCopy { u64 srcOffset, dstOffset, size; };
}
struct Span { u64 address, size; };
static std::vector<Span> mapped_ranges, reads, dirty;
static std::vector<vk::BufferCopy> submitted;
static std::vector<BbCopyShader::Control> controls;
static unsigned obtains;
namespace Core {
struct Memory {
    static Memory* Instance() { static Memory m; return &m; }
    u64 ClampRangeSize(VAddr address, u64 size) {
        for (const auto& r : mapped_ranges)
            if (address >= r.address && address - r.address <= r.size &&
                size <= r.size - (address - r.address)) return size;
        return 0;
    }
    void ReadBacking(VAddr address, void* out, u64 size) {
        reads.push_back({address, size});
        if (size > controls.size() * sizeof(BbCopyShader::Control)) std::abort();
        std::memcpy(out, controls.data(), static_cast<std::size_t>(size));
    }
};
}
namespace AmdGpu {
struct Buffer {
    VAddr base_address;
    u32 stride, data_format, num_format, num_records;
    u32 GetStride() const { return stride; }
    template<class T> Buffer GetSharp(const T&) const { return *this; }
};
struct ComputeProgram { u32 dim_x; };
}
namespace Shader {
struct Info { std::array<AmdGpu::Buffer, 3> buffers; u64 pgm_hash = 0xfefebf9f; };
}
namespace VideoCore {
enum class ObtainBufferFlags { IgnoreStreamBuffer };
}
struct Runtime {
    void CopyBuffer(int*, int*, std::span<vk::BufferCopy> copies) {
        submitted.insert(submitted.end(), copies.begin(), copies.end());
    }
};
struct Cache {
    std::pair<int*, u64> ObtainBuffer(VAddr, u64,
        VideoCore::ObtainBufferFlags = VideoCore::ObtainBufferFlags::IgnoreStreamBuffer) {
        ++obtains; static int buffer; return {&buffer, 64};
    }
    void MarkRegionAsGpuModified(VAddr address, u64 size) { dirty.push_back({address, size}); }
};
struct Rasterizer {
    Runtime runtime; Cache cache;
    Runtime& GetRuntime() { return runtime; }
    Cache& GetBufferCache() { return cache; }
};
static bool MultiCopy(Rasterizer&, int*, int*, std::span<vk::BufferCopy>) { return false; }
#include "copy_hle.inc"
static void Check(bool ok, int line) {
    if (!ok) { std::fprintf(stderr, "HLE safety failure line %d\n", line); std::exit(1); }
}
#define CHECK(v) Check((v), __LINE__)
int main() {
    // Fixed synthetic guest addresses; control reads go through the fake backing interface.
    constexpr u64 ctl = 0x100000, src = 0x200000, dst = 0x300000;
    Shader::Info info{{AmdGpu::Buffer{ctl,12,13,4,2}, {src,4,4,4,1000}, {dst,4,4,4,1000}}};
    const auto reset = [&] {
        reads.clear(); dirty.clear(); submitted.clear(); obtains = 0;
        mapped_ranges = {{ctl,24},{src,4000},{dst,4000}};
        controls = {{100,200,9},{990,990,63}};
    };
    Rasterizer rasterizer;
    const auto run = [&](u32 groups=2) { CHECK(ExecuteCopyShaderHLE(info,{groups},rasterizer)); };
    reset(); run();
    CHECK(reads.size()==1 && reads[0].address==ctl && reads[0].size==24);
    CHECK(submitted.size()==2 && submitted[0].size==40 && submitted[1].size==40);
    CHECK(dirty.size()==2 && dirty[0].address==dst+400 && dirty[1].address==dst+3960);
    CHECK(dirty[0].size==40 && dirty[1].size==40);

    reset(); info.buffers[0].stride=16; run();
    CHECK(reads.empty() && submitted.empty() && dirty.empty() && obtains==0);
    info.buffers[0].stride=12;
    reset(); mapped_ranges.erase(mapped_ranges.begin()); run();
    CHECK(reads.empty() && submitted.empty() && dirty.empty() && obtains==0);
    reset(); mapped_ranges.pop_back(); run();
    CHECK(reads.size()==1 && submitted.empty() && dirty.empty() && obtains==0);
    reset(); controls={{1000,0,0xffffffff},{0,1000,0xffffffff}}; run();
    CHECK(submitted.empty() && dirty.empty() && obtains==0);
    reset(); info.buffers[0].num_records=1; run(0xffffffff);
    CHECK(reads[0].size==12 && submitted.size()==1 && dirty.size()==1);
    info.buffers[0].num_records=2;
    reset(); run(0); CHECK(reads.empty() && submitted.empty() && dirty.empty());
    reset(); info.buffers[2].base_address=~u64{0}-100; run();
    CHECK(submitted.empty() && dirty.empty() && obtains==0);
    info.buffers[2].base_address=dst;
    // An unmapped batch does not suppress a later independently mapped batch.
    reset(); info.buffers[1].num_records=100000; info.buffers[2].num_records=100000;
    controls={{0,0,0},{20000,20000,0}};
    mapped_ranges={{ctl,24},{src+80000,4},{dst+80000,4}}; run();
    CHECK(submitted.size()==1 && dirty.size()==1 && dirty[0].address==dst+80000);
    CHECK(dirty[0].size==4 && obtains==2);
    std::puts("production HLE: 9 memory/copy/dirty-range scenarios passed");
}
