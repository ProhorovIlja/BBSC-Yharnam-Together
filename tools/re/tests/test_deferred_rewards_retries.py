# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise ACTUAL production C++ guest reward queue extraction with mocked map loads.

A source-only regression, not a playable game or real saved-game validation.
We explicitly test the old failure: an item was popped from the queue during a
load when MapItemMan was unavailable, and therefore never awarded afterward.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
FILE = ROOT / "emulator/src/core/bloodborne_flags_store.cpp"


class DeferredRewardRetries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = FILE.read_text(encoding="utf-8")

    def test_actual_boss_npc_game_thread_requires_ready_manager_before_drain(self):
        source = self.source
        self.assertEqual(source.count("TakeDueDeferredItems("), 3)
        self.assertEqual(source.count("std::chrono::milliseconds{250}"), 2)
        npc = source.split("void GiveDueNpcGifts(", 1)[1].split(
            "\n// See GivesNpcDeathDrop:", 1)[0]
        boss = source.split("void GiveDeferredBossItems()", 1)[1].split(
            "\n} // namespace Coop", 1)[0]
        for method, queue in ((npc, "held_npc_gifts"), (boss, "deferred_item_lots")):
            with self.subTest(queue=queue):
                self.assertIn("std::ranges::none_of(" + queue, method)
                self.assertIn("ReadValue<u64>(image_base + MapItemManPointerOffset, 0)", method)
                self.assertIn("HasVtable(item_man, MapItemManVtable,", method)
                self.assertIn("TakeDueDeferredItems(" + queue + ", true", method)
                self.assertLess(method.index("HasVtable(item_man, MapItemManVtable"),
                                method.index("TakeDueDeferredItems(" + queue + ", true"))
                self.assertIn("std::scoped_lock lock{deferred_item_lots_mutex};", method)
        # An NPC trigger is not removed/marked done until the item lot can be given.
        self.assertLess(npc.index("TakeDueDeferredItems(held_npc_gifts, true"),
                        npc.index("switch (gift.after)"))

    def test_compile_real_cpp_extract_with_five_outstanding_rewards(self):
        start = self.source.index(
            "template <typename Item, typename IsDue>\nstd::vector<Item> TakeDueDeferredItems(")
        end = self.source.index("\n}\n\n} // namespace", start) + 2
        helper = self.source[start:end]
        self.assertIn("if (!item_manager_ready)", helper)
        self.assertIn("std::erase_if(pending", helper)
        cxx = shutil.which("g++") or shutil.which("c++")
        if cxx is None:
            self.skipTest("C++20 compiler unavailable")

        fixture = r'''
#include <algorithm>
#include <cstdint>
#include <utility>
#include <vector>
// ACTUAL_PRODUCTION_HELPER
#define CHECK(x) do { if (!(x)) return __LINE__; } while(0)
struct NpcGift { int id; int due; };
int main() {
    using Lot = std::pair<int, int>;
    std::vector<Lot> bosses{
        {2502000, 10}, {3501800, 20}, {3401850, 50}, {50000010, 90}, {15000, 110}
    };
    const auto is_due = [](const Lot& x) { return x.second <= 60; };
    // The game manager is missing during travel. DO NOT lose boss loot.
    auto gotten = TakeDueDeferredItems(bosses, false, is_due);
    CHECK(gotten.empty());
    CHECK(bosses.size() == 5);
    gotten = TakeDueDeferredItems(bosses, true, is_due);
    CHECK(gotten.size() == 3);
    CHECK(gotten[0].first == 2502000 && gotten[1].first == 3501800);
    CHECK(bosses.size() == 2);
    CHECK(bosses[0].second == 90 && bosses[1].second == 110);
    CHECK(TakeDueDeferredItems(bosses, true, is_due).empty()); // once each

    std::vector<NpcGift> gifts{
        {1, 10}, {2, 20}, {3, 30}, {4, 40}, {5, 50}
    };
    CHECK(TakeDueDeferredItems(gifts, false,
          [](const NpcGift&) { return true; }).empty());
    CHECK(gifts.size() == 5);
    auto ready = TakeDueDeferredItems(gifts, true,
        [](const NpcGift& gift) { return gift.due <= 30; });
    CHECK(ready.size() == 3 && gifts.size() == 2);
    CHECK(gifts[0].id == 4 && gifts[1].id == 5);
    CHECK(TakeDueDeferredItems(gifts, true,
          [](const NpcGift& gift) { return gift.due <= 30; }).empty());
    CHECK(TakeDueDeferredItems(gifts, true,
          [](const NpcGift&) { return true; }).size() == 2);
    CHECK(gifts.empty());
    return 0;
}
'''
        fixture = fixture.replace("// ACTUAL_PRODUCTION_HELPER", helper)
        with tempfile.TemporaryDirectory(prefix="bbsc-reward-queue-") as td:
            src = Path(td) / "rewards.cpp"
            exe = Path(td) / "rewards"
            src.write_text(fixture, encoding="utf-8")
            cmd = [cxx, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                   str(src), "-o", str(exe)]
            compilation = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
            self.assertEqual(compilation.returncode, 0, compilation.stderr[-2200:])
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=8)
            self.assertEqual(run.returncode, 0,
                             f"Production retry helper fixture failed line {run.returncode}: "
                             + run.stderr)


if __name__ == "__main__":
    unittest.main()
