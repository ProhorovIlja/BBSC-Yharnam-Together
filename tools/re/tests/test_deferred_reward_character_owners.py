# SPDX-License-Identifier: GPL-2.0-or-later
"""B04 regression: a pending co-op reward belongs to its exact character.

Compile the *production* C++ owner-tag and foreign-owner eviction templates.
No Bloodborne game assets, real saved games, online accounts, or full client
builds are used. Tests prove the in-memory selection contract, NOT a native
award succeeded on real hardware.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
FLAGS = ROOT / "emulator/src/core/bloodborne_flags_store.cpp"


class RewardCharacterOwnership(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = FLAGS.read_text(encoding="utf-8")

    def test_source_tags_all_producers_and_same_slot_replacement(self):
        code = self.source
        self.assertIn("std::atomic<u64> deferred_reward_character_generation{1};", code)
        self.assertIn(
            "deferred_reward_character_generation.fetch_add(1, std::memory_order_relaxed);",
            code,
        )
        new_char = code.split("void ForgetSlotIfNewCharacter()", 1)[1].split(
            "// After the pickups", 1
        )[0]
        self.assertLess(
            new_char.index("ForgetsSlotLists("),
            new_char.index("deferred_reward_character_generation.fetch_add("),
        )
        self.assertLess(
            new_char.index("deferred_reward_character_generation.fetch_add("),
            new_char.index("BackUpSlotLists();"),
        )
        self.assertIn("return BloodborneCoop::ValidSaveCharacterScope(slot, generation);", code)
        self.assertGreaterEqual(code.count("if (!owner.Valid()) {"), 4)
        self.assertIn("return in_session && current.Valid();", code)
        self.assertNotIn("if (owner.slot < 0)", code)
        boss_queue = code.split("bool PS4_SYSV_ABI HoldGuestBossItem(", 1)[1].split(
            "\n} // namespace", 1
        )[0]
        npc_queue = code.split("void QueueGuestNpcGift(", 1)[1].split(
            "\n// The held NPC gifts", 1
        )[0]
        self.assertIn("const DeferredRewardOwner owner = CurrentDeferredRewardOwner()", boss_queue)
        self.assertIn("const DeferredRewardOwner owner = CurrentDeferredRewardOwner()", npc_queue)
        self.assertIn("DeferredBossItemDelay, owner", boss_queue)
        self.assertIn("NpcGiftDelay, owner", npc_queue)
        self.assertIn("held.owner == owner && held.gift.trigger == gift.trigger", npc_queue)

    def test_both_consumers_retire_foreign_owner_before_looking_for_due(self):
        code = self.source
        npc = code.split("void GiveDueNpcGifts(", 1)[1].split(
            "\n// See GivesNpcDeathDrop:", 1
        )[0]
        boss = code.split("void GiveDeferredBossItems()", 1)[1].split(
            "\n} // namespace Coop", 1
        )[0]
        for name, part, pending in (
            ("npc", npc, "held_npc_gifts"),
            ("boss", boss, "deferred_item_lots"),
        ):
            with self.subTest(name=name):
                self.assertIn(
                    f"DiscardOtherCharactersRewards({pending}, owner)", part,
                )
                self.assertLess(
                    part.index(f"DiscardOtherCharactersRewards({pending}, owner)"),
                    part.index(f"std::ranges::none_of({pending}"),
                )
                self.assertLess(
                    part.index("HasVtable(item_man, MapItemManVtable,"),
                    part.index(f"TakeDueDeferredItems({pending}, true"),
                )
                self.assertIn("CurrentDeferredRewardOwner() == owner", part)
                self.assertIn(f"{pending}.insert({pending}.end()", part)
                self.assertIn("std::make_move_iterator(due.begin() + index)", part)
                self.assertIn("held.owner == owner && now >= held.due", part)

    def test_compile_actual_cpp_owner_eviction_with_five_hunters_and_slot_reuse(self):
        text = self.source
        start = text.index("struct DeferredRewardOwner {")
        owner_end = text.index("\nDeferredRewardOwner CurrentDeferredRewardOwner()", start)
        owner_type = text[start:owner_end]
        a = text.index("template <typename Item>\nsize_t DiscardOtherCharactersRewards(")
        b = text.index("\n}\n\n// Never remove a pending boss", a) + 2
        selector = text[a:b]
        self.assertIn("item.owner != current", selector)
        compiler = shutil.which("g++") or shutil.which("c++")
        if compiler is None:
            self.skipTest("C++20 compiler unavailable")
        fixture = r'''
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <vector>
#include "core/phantom_inventory_scope.h"
using u64 = std::uint64_t;
// EXACT_OWNER_TYPE
// EXACT_EVICTION_HELPER
#define CHECK(e) do { if (!(e)) return __LINE__; } while (0)
struct Lot { int id; int due; DeferredRewardOwner owner; };
struct Gift { int id; DeferredRewardOwner owner; };
int main() {
    CHECK((DeferredRewardOwner{0, 1}.Valid()));
    CHECK((DeferredRewardOwner{9, 42}.Valid()));
    CHECK(!(DeferredRewardOwner{-1, 1}.Valid()));
    CHECK(!(DeferredRewardOwner{10, 1}.Valid()));
    CHECK(!(DeferredRewardOwner{1, 0}.Valid()));
    // Five-hunter synthetic scenario. A single local character's reward
    // queue contains stale entries from earlier slots and a new character
    // that reused the same slot. Only the exact slot + generation survives.
    std::vector<Lot> lots = {
        {10, 1, {1, 7}}, {20, 1, {2, 7}}, {30, 1, {1, 8}},
        {40, 90, {1, 7}}, {50, 1, {3, 6}},
    };
    CHECK(DiscardOtherCharactersRewards(lots, {1, 7}) == 3);
    CHECK(lots.size() == 2 && lots[0].id == 10 && lots[1].id == 40);
    CHECK(DiscardOtherCharactersRewards(lots, {1, 7}) == 0);
    // Still pending when the manager is unavailable: the B03 readiness
    // function must not touch either valid item.
    CHECK(lots.size() == 2);
    // A new character in the same slot changes generation; no old reward.
    CHECK(DiscardOtherCharactersRewards(lots, {1, 8}) == 2);
    CHECK(lots.empty());
    std::vector<Gift> gifts = {
        {1, {4, 2}}, {2, {4, 2}}, {3, {5, 2}},
        {4, {4, 3}}, {5, {0, 99}}
    };
    CHECK(DiscardOtherCharactersRewards(gifts, {4, 2}) == 3);
    CHECK(gifts.size() == 2 && gifts[0].id == 1 && gifts[1].id == 2);
    CHECK(DiscardOtherCharactersRewards(gifts, {-1, 2}) == 2);
    CHECK(gifts.empty());
    return 0;
}
'''
        fixture = fixture.replace("// EXACT_OWNER_TYPE", owner_type).replace(
            "// EXACT_EVICTION_HELPER", selector
        )
        with tempfile.TemporaryDirectory(prefix="bbsc-reward-owner-") as td:
            path = Path(td) / "owners.cpp"
            exe = Path(td) / "owners"
            path.write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-I", str(ROOT / "emulator/src"), str(path), "-o", str(exe)],
                capture_output=True, text=True, timeout=40,
            )
            self.assertEqual(result.returncode, 0, result.stderr[-2500:])
            run = subprocess.run(
                [str(exe)], capture_output=True, text=True, timeout=8,
            )
            self.assertEqual(
                run.returncode, 0,
                f"Compiled production owner filter failed at fixture line {run.returncode}: "
                + run.stderr,
            )


if __name__ == "__main__":
    unittest.main()
