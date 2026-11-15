// SPDX-License-Identifier: GPL-2.0-or-later
// Isolated original/patched machine-code loop; continuations only capture registers.
// No game image, game process, virtual call or data dereference through a claimed slot.
#include <algorithm>
#include <array>
#include <barrier>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#else
#include <sys/mman.h>
#endif
#include "lod_bytes.h"

using u8 = unsigned char;
using u64 = uint64_t;
using u32 = uint32_t;
constexpr size_t Stride = 0x3d0;
constexpr u64 Canary = 0x13572468abcdef00ull;
struct Result { std::array<u64, 10> r{}; };
static_assert(sizeof(Result) == 80 && sizeof(void*) == 8);
struct Owner {
    alignas(64) std::array<u8, 512> bytes{};
    std::array<std::array<u8, Stride * 8>, 4> elements{};
    template<class T> void put(size_t at, T value) { std::memcpy(bytes.data() + at, &value, sizeof value); }
    template<class T> T get(size_t at) const { T value{}; std::memcpy(&value, bytes.data() + at, sizeof value); return value; }
    void reset(const std::array<u64, 4>& capacities) {
        bytes.fill(0);
        for (size_t slot = 0; slot < 4; ++slot) {
            put(0xa8 + 24 * slot, capacities[slot]);
            put(0xb0 + 24 * slot, reinterpret_cast<u64>(elements[slot].data()));
        }
    }
};
std::vector<u8> Hex(const std::string& text) {
    std::vector<u8> result;
    for (size_t i = 0; i < text.size(); i += 2) result.push_back(static_cast<u8>(std::stoul(text.substr(i, 2), nullptr, 16)));
    return result;
}
class Loop {
    static constexpr size_t Size = 8192, Entry = 512, Capture = Entry + 256;
    u8* code = nullptr;
    void jump(size_t at, size_t target) {
        code[at] = 0xe9;
        const int32_t distance = static_cast<int32_t>(target) - static_cast<int32_t>(at + 5);
        std::memcpy(code + at + 1, &distance, 4);
    }
    void bytes(size_t at, const std::vector<u8>& data) { std::memcpy(code + at, data.data(), data.size()); }
public:
    explicit Loop(bool patched) {
#ifdef _WIN32
        code = static_cast<u8*>(VirtualAlloc(nullptr, Size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE));
#else
        void* memory = mmap(nullptr, Size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (memory != MAP_FAILED) code = static_cast<u8*>(memory);
#endif
        if (!code) throw std::runtime_error("Cannot allocate fixture code");
        std::memset(code, 0xcc, Size);
        // Save all nonvolatile GPRs, reserve aligned call space, map platform arguments
        // to rdi=owner, ecx=first slot, r12=result; preserve the r8 sentinel through the loop.
#ifdef _WIN32
        bytes(0, Hex("5355575641544155415641574883ec284c89c84d89c44889cf89d149b800efcdab68245713ffd04883c428415f415e415d415c5e5f5d5bc3"));
#else
        bytes(0, Hex("5355575641544155415641574883ec284889c84989d489f149b800efcdab68245713ffd04883c428415f415e415d415c5e5f5d5bc3"));
#endif
        std::memcpy(code + Entry, patched ? PatchedClaim : OriginalClaim, sizeof OriginalClaim);
        bytes(Entry + ClaimDone, Hex("41bb01000000")); // r11d = success
        jump(Entry + ClaimDone + 6, Capture);
        bytes(Entry + ClaimFull, Hex("4531db")); // r11d = full
        jump(Entry + ClaimFull + 3, Capture);
        // Capture rsi,rcx,rax,rbx,r9,r10,rdx,r15,r8,r11, then return to the wrapper.
        bytes(Capture, Hex("4989342449894c2408498944241049895c24184d894c24204d8954242849895424304d897c24384d894424404d895c2448c3"));
#ifdef _WIN32
        DWORD previous{};
        if (!VirtualProtect(code, Size, PAGE_EXECUTE_READ, &previous) || !FlushInstructionCache(GetCurrentProcess(), code, Size))
            throw std::runtime_error("Cannot protect fixture code");
#else
        if (mprotect(code, Size, PROT_READ | PROT_EXEC) != 0) throw std::runtime_error("Cannot protect fixture code");
        __builtin___clear_cache(reinterpret_cast<char*>(code), reinterpret_cast<char*>(code + Size));
#endif
    }
    ~Loop() {
#ifdef _WIN32
        if (code) VirtualFree(code, 0, MEM_RELEASE);
#else
        if (code) munmap(code, Size);
#endif
    }
    Result call(Owner& owner, u32 first) const {
        Result result;
        using Function = void (*)(void*, u32, Result*, void*);
        reinterpret_cast<Function>(code)(owner.bytes.data(), first, &result, code + Entry);
        return result;
    }
};
bool Registers(const Owner& owner, const Result& result) {
    const auto& r = result.r;
    if (r[7] != 0 || r[8] != Canary) return false;
    if (!r[9]) return true;
    if (r[9] != 1 || r[0] >= 4) return false;
    const u64 base = owner.get<u64>(0xb0 + 24 * static_cast<size_t>(r[0]));
    return r[2] == r[1] + 1 && r[3] == r[0] * 3 && r[4] == base &&
           r[5] == r[1] * Stride && r[6] == base + r[5];
}
bool Sequential(const Loop& original, const Loop& patched) {
    const std::array<std::array<u64, 4>, 5> layouts{{{0,0,0,0},{2,2,2,2},{1,3,0,2},{3,1,4,0},{0,2,1,3}}};
    unsigned cases = 0;
    for (const auto& layout : layouts) for (u32 first = 0; first <= 4; ++first) {
        Owner a, b; a.reset(layout); b.reset(layout);
        for (unsigned n = 0; n < 24; ++n) {
            const auto x = original.call(a, first), y = patched.call(b, first);
            if (!Registers(a,x) || !Registers(b,y) || x.r[9] != y.r[9]) return false;
            if (x.r[9] && (x.r[0] != y.r[0] || x.r[1] != y.r[1] || x.r[2] != y.r[2] ||
                          x.r[3] != y.r[3] || x.r[5] != y.r[5])) return false;
            for (size_t i = 0; i < 4; ++i) if (a.get<u32>(0x100 + 4*i) != b.get<u32>(0x100 + 4*i)) return false;
            ++cases;
        }
    }
    Owner owner; owner.reset({2,2,2,2});
    for (u32 first : {5u, 0xffffffffu}) {
        const auto result = patched.call(owner, first);
        if (!Registers(owner,result) || result.r[9]) return false;
    }
    std::cout << "LOD_SEQUENTIAL_CASES=" << cases << " INVALID_STARTS=2 PASS\n";
    return true;
}
int main(int argc, char** argv) {
#if !defined(__x86_64__) && !defined(_M_X64)
    std::cout << "SKIP: actual x86-64 loop execution needs an x86-64 host\n";
    return 77;
#else
    try {
        const bool baseline = argc > 1 && std::string(argv[1]) == "baseline";
        const unsigned rounds = argc > 2 ? static_cast<unsigned>(std::stoul(argv[2])) : 100000;
        if (!rounds || rounds > 1000000) return 4;
        Loop original(false), patched(true);
        if (!Sequential(original, patched)) return 5;
        const Loop& loop = baseline ? original : patched;
        Owner owner;
        std::array<Result, 8> results;
        std::barrier start(9), done(9);
        std::vector<std::thread> workers;
        for (size_t worker = 0; worker < results.size(); ++worker) workers.emplace_back([&,worker] {
            for (unsigned round = 0; round < rounds; ++round) {
                start.arrive_and_wait();
                results[worker] = loop.call(owner, 0);
                done.arrive_and_wait();
            }
        });
        u64 duplicates = 0, overruns = 0, overflow_slots = 0, overflow_rounds = 0, invalid = 0, missed = 0;
        for (unsigned round = 0; round < rounds; ++round) {
            owner.reset({2,2,2,2});
            start.arrive_and_wait(); done.arrive_and_wait();
            std::array<bool,8> seen{};
            bool round_overflow = false;
            for (const auto& result : results) {
                if (!Registers(owner,result)) { ++invalid; continue; }
                if (!result.r[9]) { ++missed; continue; }
                if (result.r[1] >= 2) { ++overruns; round_overflow = true; continue; }
                const size_t index = static_cast<size_t>(result.r[0]*2 + result.r[1]);
                if (seen[index]) ++duplicates;
                seen[index] = true;
            }
            for (size_t slot = 0; slot < 4; ++slot) if (owner.get<u32>(0x100+4*slot) > 2) {
                ++overflow_slots; round_overflow = true;
            }
            if (round_overflow) ++overflow_rounds;
        }
        for (auto& worker : workers) worker.join();
        std::cout << "LOD_STRESS mode=" << (baseline ? "original" : "patched") << " rounds=" << rounds
                  << " threads=8 duplicates=" << duplicates << " overrun_claims=" << overruns
                  << " over_capacity_slots=" << overflow_slots << " overrun_rounds=" << overflow_rounds
                  << " invalid_registers=" << invalid << " missed_claims=" << missed << '\n';
        return baseline || (!duplicates && !overruns && !overflow_slots && !invalid && !missed) ? 0 : 1;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 6; }
#endif
}
