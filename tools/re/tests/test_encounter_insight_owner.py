# SPDX-License-Identifier: GPL-2.0-or-later
"""B13: compile actual boss-Insight payout owner logic, no proprietary game files.

A synthetic Windows/Linux fixture extracts the exact inline C++ production class
from bloodborne_party.h. The full Bloodborne game/engine is not built here.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
PARTY = ROOT / "emulator/src/core/bloodborne_party.h"
TRAVEL = ROOT / "emulator/src/core/bloodborne_travel.cpp"
INTERNAL = ROOT / "emulator/src/core/bloodborne_re_internal.h"
NATIVE_TESTS = ROOT / "emulator/tests/bloodborne/test_bloodborne_party.cpp"


class InsightOwner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = PARTY.read_text(encoding="utf-8")
        cls.travel = TRAVEL.read_text(encoding="utf-8")
        cls.internal = INTERNAL.read_text(encoding="utf-8")
        start = cls.header.index("class EncounterInsightPayout {")
        end = cls.header.index("\n};", start) + len("\n};")
        cls.production = cls.header[start:end]

    def test_source_calls_are_owner_bound_no_static_global_unowned_points(self):
        start = self.travel.index("void GiveEncounterInsight(bool in_session) {")
        end = self.travel.index("\n}\n", start)
        source = self.travel[start:end]
        self.assertIn("payout.ObserveOwner(slot, generation)", source)
        self.assertIn("deferred_reward_character_generation.load(", source)
        self.assertIn("character_slot.load(", source)
        self.assertIn("watch.Reset();", source)
        self.assertIn("if (slot < 0)", source)
        self.assertIn("payout.Add(boss.amount)", source)
        self.assertIn("payout.CanPay(now_ms)", source)
        self.assertIn("payout.Paid(now_ms)", source)
        self.assertNotIn("static s32 points_due", source)
        self.assertNotIn("points_due += boss.amount", source)
        self.assertIn("extern std::atomic<u64> deferred_reward_character_generation;",
                      self.internal)

    def test_real_production_cpp_compiles_and_prevents_cross_character_awards(self):
        compiler = shutil.which("clang++") or shutil.which("g++") or shutil.which("c++")
        if compiler is None:
            self.skipTest("Need a C++20 native compiler")
        program = r"""
#include <algorithm>
#include <cstdint>
#include <map>
#include <optional>
#include <utility>
using u64 = std::uint64_t;
using s64 = std::int64_t;
using s32 = std::int32_t;
__PRODUCTION__
#define REQUIRE(x) do { if (!(x)) return __LINE__; } while (false)
int main() {
    EncounterInsightPayout queue;
    REQUIRE(queue.ObserveOwner(0, 1));
    REQUIRE(queue.Add(5));
    REQUIRE(queue.Remaining() == 5);
    REQUIRE(queue.Paid(100));
    REQUIRE(queue.Remaining() == 4);
    REQUIRE(queue.ObserveOwner(1, 1));
    REQUIRE(!queue.CanPay(500));
    REQUIRE(queue.Remaining() == 0);
    REQUIRE(queue.Add(2));
    REQUIRE(queue.Paid(500));
    REQUIRE(queue.Remaining() == 1);
    REQUIRE(queue.ObserveOwner(0, 1));
    REQUIRE(queue.Remaining() == 4);
    REQUIRE(queue.Paid(800));
    REQUIRE(queue.Remaining() == 3);
    REQUIRE(!queue.Paid(1099));
    REQUIRE(queue.Paid(1100));
    REQUIRE(queue.ObserveOwner(1, 1));
    REQUIRE(queue.Remaining() == 1);

    // Replacing a save slot increments generation, never inherits old Insight.
    REQUIRE(queue.ObserveOwner(1, 2));
    REQUIRE(queue.Remaining() == 0);
    REQUIRE(!queue.Paid(1500));
    REQUIRE(queue.ObserveOwner(1, 1));
    REQUIRE(queue.Remaining() == 0);

    REQUIRE(queue.ObserveOwner(-1, 2));
    REQUIRE(!queue.Add(5));
    REQUIRE(!queue.CanPay(2000));
    REQUIRE(queue.ObserveOwner(3, 10));
    REQUIRE(!queue.Add(0));
    REQUIRE(!queue.Add(-1));
    for (int i = 0; i < 1000; ++i) REQUIRE(queue.Add(5));
    REQUIRE(queue.Remaining() == 200);
    REQUIRE(queue.Paid(2000));
    REQUIRE(queue.Remaining() == 199);
    REQUIRE(!queue.Paid(2001));
    return 0;
}
""".replace("__PRODUCTION__", self.production)
        with tempfile.TemporaryDirectory(prefix="bbsc-b13-") as td:
            source = Path(td) / "owner.cpp"
            binary = Path(td) / ("owner.exe" if os.name == "nt" else "owner")
            source.write_text(program, encoding="utf-8")
            built = subprocess.run(
                [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                 str(source), "-o", str(binary)],
                capture_output=True, text=True, timeout=45
            )
            self.assertEqual(built.returncode, 0, built.stderr[-3000:])
            run = subprocess.run([str(binary)], capture_output=True,
                                 text=True, timeout=10)
            self.assertEqual(run.returncode, 0, f"fixture exit line {run.returncode}")

    def test_production_engine_gtests_are_present(self):
        tests = NATIVE_TESTS.read_text(encoding="utf-8")
        for name in (
            "BossInsightStaysWithItsOriginalHunterAcrossSaveSwitch",
            "SameSlotNewCharacterCannotInheritPendingPoints",
            "UnknownCharacterAndEmptyAwardNeverPay",
            "PayoutPacesNativeEffectToOnePointEvery300Milliseconds",
            "DuplicateEventStormCannotOverflowPendingLedger",
        ):
            self.assertIn("TEST(BloodborneEncounterInsight, " + name + ")", tests)


if __name__ == "__main__":
    unittest.main()
