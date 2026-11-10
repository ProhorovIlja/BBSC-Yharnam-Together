"""B48: verify the genuine upstream-backed enemy revive rule without the game.

The source contract checks the actual hook and GTest. The isolated C++20 probe
extracts the *actual* BroughtBackByTheHost function from bloodborne_party.cpp
and compiles it with minimal stand-in POD types for GCC and Clang. It does NOT
duplicate the algorithm or pretend to simulate a full Bloodborne session.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class GuestEnemyDeathGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = read("emulator/src/core/bloodborne_party.h")
        cls.cpp = read("emulator/src/core/bloodborne_party.cpp")
        cls.hook = read("emulator/src/core/bloodborne_kills_hp.cpp")
        cls.gtest = read("emulator/tests/bloodborne/test_bloodborne_party_death.cpp")

    def test_requires_confirmed_dead_host_sample_in_own_visit(self):
        self.assertIn("constexpr s64 HostDeadBeforeCopyMs = 15'000;", self.h)
        self.assertIn("const std::unordered_map<u32, s64>& host_dead", self.h)
        for term in ("host_dead.find(copy.handle)",
                     "dead_there != host_dead.end()",
                     "dead_there->second >= copy.dead_since_ms - HostDeadBeforeCopyMs",
                     "!copy.boss", "!party_kills.contains(copy.handle)"):
            self.assertIn(term, self.cpp)

    def test_host_dead_lifecycle_follows_live_map_visit(self):
        for term in ("static std::unordered_map<u32, s64> host_dead",
                     "if (visit != host_dead_visit)", "host_dead.clear()",
                     "if (character.dead)", "host_dead[character.handle] = now_ms",
                     "BroughtBackByTheHost(*hosts_now, dead_here, others, host_dead, now_ms)"):
            self.assertIn(term, self.hook)
        self.assertIn("AGuestNeverBringsBackItsOwnKillTheHostHasNotSeenYet", self.gtest)
        self.assertIn("ABossDeadHereIsNeverBroughtBack", self.gtest)

    def test_no_premature_guest_resurrection_or_new_flags_in_server(self):
        self.assertIn("if (!copy.boss && alive_at_host.contains(copy.handle)", self.cpp)
        self.assertNotIn("BroughtBackByTheHost(*hosts_now, dead_here, others, now_ms)", self.hook)
        self.assertIn("std::ranges::sort(back)", self.cpp)


def portable_probe():
    src = read("emulator/src/core/bloodborne_party.cpp")
    start = src.index("std::vector<u32> BroughtBackByTheHost(")
    end = src.index("\n}\n\nstd::vector<u32> BringBackGuard::Filter(", start) + 2
    actual_cpp = src[start:end]
    prefix = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <ranges>
#include <span>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using u32 = std::uint32_t;
using s64 = std::int64_t;
struct CharacterShown {
  u32 handle = 0;
  bool hidden = false;
  bool disabled = false;
  bool distant = false;
  bool dead = false;
};
struct DeadCopy {
  u32 handle = 0;
  s64 dead_since_ms = 0;
  bool boss = false;
};
constexpr s64 BringBackAfterMs = 3000;
constexpr s64 HostDeadBeforeCopyMs = 15000;
'''
    suffix = r'''
int main() {
    constexpr s64 Now = 100000;
    const std::vector<CharacterShown> host{
        {.handle = 0x10014000}, {.handle = 0x1000801b},
        {.handle = 0x1000801c}, {.handle = 0x10000002, .hidden = true}};
    const std::vector<DeadCopy> dead{
        {0x10014000, Now - 3000},   // self kill not yet transmitted
        {0x1000801b, Now - 30000},  // real generator revive
        {0x1000801c, Now - 30000},  // stale host-dead sample
        {0x10000002, Now - 30000},  // invisible host source
    };
    const std::unordered_map<u32,s64> observed{
        {0x1000801b, Now - 29000},
        {0x1000801c, Now - 30000 - HostDeadBeforeCopyMs - 1},
        {0x10000002, Now - 30000},
    };
    assert(BroughtBackByTheHost(host, dead, {}, observed, Now) ==
           std::vector<u32>{0x1000801b});
    assert(BroughtBackByTheHost(host, dead, {}, {}, Now).empty());
    assert(BroughtBackByTheHost(host, dead, {0x1000801b}, observed, Now).empty());
    const std::vector<DeadCopy> boss{{0x1000801b, Now - 30000, true}};
    assert(BroughtBackByTheHost(host, boss, {}, observed, Now).empty());
    const std::unordered_map<u32,s64> edge{{0x1000801b, Now - 30000 - HostDeadBeforeCopyMs}};
    const std::vector<DeadCopy> one{{0x1000801b, Now - 30000}};
    assert(BroughtBackByTheHost(host, one, {}, edge, Now) ==
           std::vector<u32>{0x1000801b}); // inclusive temporal boundary
    const std::unordered_map<u32,s64> too_old{{0x1000801b, Now - 30000 - HostDeadBeforeCopyMs - 1}};
    assert(BroughtBackByTheHost(host, one, {}, too_old, Now).empty());
    std::cout << "B48_REAL_PRODUCTION_HOST_DEAD_FIRST_NO_GUEST_DUPLICATE_KILL_PASS\n";
}
'''
    with tempfile.TemporaryDirectory(prefix="b48-real-function-") as tmp:
        file = Path(tmp) / "actual_party_kill.cpp"
        file.write_text(prefix + actual_cpp + suffix, encoding="utf-8")
        for compiler in ("g++", "clang++"):
            exe = Path(tmp) / ("actual_" + compiler.replace("+", "p"))
            p = subprocess.run(
                [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-pedantic", str(file), "-o", str(exe)],
                capture_output=True, text=True, timeout=40
            )
            if p.returncode:
                raise RuntimeError(f"{compiler}: actual production function failed compile:\n" +
                                   p.stderr[:1800])
            r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
            if r.returncode:
                raise RuntimeError(f"{compiler}: actual production function failed tests:\n" +
                                   r.stderr[:900])
            print(f"{compiler}: {r.stdout.strip()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile", action="store_true")
    opts = parser.parse_args()
    if opts.compile:
        portable_probe()
    else:
        unittest.main(argv=[__file__])
