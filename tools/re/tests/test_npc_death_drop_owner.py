# SPDX-License-Identifier: GPL-2.0-or-later
"""B30: compile the actual NPC death-drop generation/slot ledger.

The game's single-hunter NPC-death-drop dedup cache previously tracked only
save slot. A newly created character can reuse that same slot while the
session is still active. The new generation-aware production helper must
forget the old hunter's grants, but not duplicate the SAME hunter's loot.
All files and game objects here are synthetic; this is not a real lot grant.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "emulator/src/core/bloodborne_flags_store.cpp"


class NpcDeathDropOwnership(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_real_game_call_site_guards_unknown_slot_and_same_slot_character(self):
        src = self.source
        self.assertIn(
            "deferred_reward_character_generation.fetch_add(1, std::memory_order_relaxed);", src
        )
        self.assertEqual(src.count("bool RefreshNpcDeathDropLedger("), 1)
        drop = src.split("void GiveNpcDeathDrops(", 1)[1].split(
            "\nvoid GiveDeferredBossItems()", 1
        )[0]
        self.assertIn("const DeferredRewardOwner owner = CurrentDeferredRewardOwner()", drop)
        self.assertIn("RefreshNpcDeathDropLedger(owner, in_session, given_owner, given)", drop)
        self.assertNotIn("given_slot", drop)
        self.assertLess(drop.index("RefreshNpcDeathDropLedger("),
                        drop.index("const bool guest = IsPartyGuestRole()"))
        self.assertLess(drop.index("HasVtable(item_man, MapItemManVtable,"),
                        drop.index("given.insert(drop.death_flag);"))
        self.assertLess(drop.index("(item_man, drop.lot, 0);"),
                        drop.index("given.insert(drop.death_flag);"))
        self.assertEqual(drop.count("given.insert(drop.death_flag);"), 1)

    def test_compile_real_cpp_owner_and_ledger_for_five_hunters(self):
        source = self.source
        begin = source.index("struct DeferredRewardOwner {")
        end = source.index("DeferredRewardOwner CurrentDeferredRewardOwner()", begin)
        owner_type = source[begin:end]
        begin = source.index("bool RefreshNpcDeathDropLedger(")
        end = source.index("\n}\nstruct HeldBossItem", begin) + 2
        actual_helper = source[begin:end]
        self.assertIn("current != recorded", actual_helper)
        self.assertIn("current.slot >= 0", actual_helper)
        self.assertIn("awarded.clear()", actual_helper)

        compiler = (shutil.which("cl") if os.name == "nt"
                    else shutil.which("g++") or shutil.which("clang++"))
        if not compiler:
            self.fail("C++20 compiler missing: tests must run in real Windows/Linux CI")

        fixture = r'''
#include <cstdint>
#include <set>
using u64 = std::uint64_t;
using s32 = std::int32_t;
// EXACT_OWNER_TYPE
// EXACT_PRODUCTION_LEDGER
#define CHECK(cond) do { if (!(cond)) return __LINE__; } while (0)
int main() {
    DeferredRewardOwner prior{};
    std::set<s32> given;
    // Five different hunters, e.g. party leader and four guests, all use
    // their own current slot; old-only reward flags cannot leak.
    for (int slot = 0; slot < 5; ++slot) {
        const DeferredRewardOwner who{slot, 7};
        CHECK(RefreshNpcDeathDropLedger(who, true, prior, given));
        CHECK(given.empty());
        given.insert(6671 + slot);
        CHECK(RefreshNpcDeathDropLedger(who, true, prior, given));
        CHECK(given.size() == 1 && given.contains(6671 + slot)); // no second award
    }
    // The last slot is reused by a newly created character without a
    // team-session leave; generation change alone MUST reset dedup.
    CHECK(RefreshNpcDeathDropLedger({4, 8}, true, prior, given));
    CHECK(given.empty());
    given.insert(6675);
    CHECK(RefreshNpcDeathDropLedger({4, 8}, true, prior, given));
    CHECK(given.contains(6675));

    // No loaded/known save slot means no reward even when a session exists.
    CHECK(!RefreshNpcDeathDropLedger({-1, 8}, true, prior, given));
    CHECK(given.empty());
    CHECK(RefreshNpcDeathDropLedger({4, 8}, true, prior, given));
    CHECK(given.empty());

    // Exiting a session resets the previous session's dedup; same character
    // can legitimately receive a new session-specific drop later.
    given.insert(6600);
    CHECK(!RefreshNpcDeathDropLedger({4, 8}, false, prior, given));
    CHECK(given.empty());
    CHECK(RefreshNpcDeathDropLedger({4, 8}, true, prior, given));
    CHECK(given.empty());
    given.insert(6601);
    CHECK(RefreshNpcDeathDropLedger({4, 8}, true, prior, given));
    CHECK(given.size() == 1 && given.contains(6601));
    return 0;
}
'''
        fixture = fixture.replace("// EXACT_OWNER_TYPE", owner_type).replace(
            "// EXACT_PRODUCTION_LEDGER", actual_helper
        )
        with tempfile.TemporaryDirectory(prefix="bbsc-b30-npc-ledger-") as td:
            folder = Path(td)
            cpp = folder / "npc_owner.cpp"
            exe = folder / ("npc_owner.exe" if os.name == "nt" else "npc_owner")
            cpp.write_text(fixture, encoding="utf-8")
            if os.name == "nt":
                command = [compiler, "/nologo", "/std:c++20", "/EHsc", "/W4",
                           str(cpp), f"/Fe:{exe}"]
            else:
                command = [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra",
                           "-Werror", str(cpp), "-o", str(exe)]
            built = subprocess.run(command, cwd=folder, capture_output=True,
                                   text=True, timeout=45)
            self.assertEqual(built.returncode, 0, built.stdout[-2000:] +
                             built.stderr[-2200:])
            ran = subprocess.run([str(exe)], cwd=folder, capture_output=True,
                                 text=True, timeout=10)
            self.assertEqual(ran.returncode, 0,
                             f"Production ledger failed fixture line {ran.returncode}: " +
                             ran.stderr[-1000:])


if __name__ == "__main__":
    unittest.main()
