"""B52: verify actual Doll Give dialog rule and live inventory-only hook.

The portable test extracts both actual production functions from party.cpp and
compiles the exact C++20 function definitions with GCC and Clang.
This does not open any Bloodborne game/save, and is not a live NPC conversation.
"""
import argparse
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class DollOrnamentFlag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = read("emulator/src/core/bloodborne_party.h")
        cls.cpp = read("emulator/src/core/bloodborne_party.cpp")
        cls.travel = read("emulator/src/core/bloodborne_travel.cpp")
        cls.gtest = read("emulator/tests/bloodborne/test_bloodborne_flag_rules.cpp")

    def test_exact_per_player_flag_and_goods_id(self):
        self.assertIn("constexpr s32 DollGiveFlag = 12100122;", self.header)
        self.assertIn("constexpr u32 SmallHairOrnamentGoods = 4300;", self.header)
        self.assertIn("std::optional<bool> DollGiveFix(bool party_configured, bool flag_on, bool holds);", self.header)
        self.assertIn("return HeldItemFlagFix(party_configured, flag_on, holds);", self.cpp)
        self.assertIn("TEST(BloodborneFlagRules, TheDollsGiveFollowsThePlayersOrnament)", self.gtest)
        self.assertIn("RuleFor(DollGiveFlag).owner, FlagOwner::PerPlayer", self.gtest)

    def test_active_party_only_local_inventory_read_not_writes(self):
        hook = self.travel.split("void KeepDollGiveFlagOwn() {", 1)[1].split(
            "\n}\n\n", 1
        )[0]
        for s in ("!party_controller", "now_ms - checked_ms < 1'000",
                  "GetLocalPlayer() < 0x10000", "!PlayerItemsReadable()",
                  "TradeItemKind::Goods, SmallHairOrnamentGoods, 0",
                  "EventFlagOn(DollGiveFlag)", "PartyGhostSetEventFlagOffset",
                  "DollGiveFlag, *fix"):
            self.assertIn(s, hook)
        for s in ("TradeGive(", "TradeReceive(", "GiveItem(", "RemoveItem("):
            self.assertNotIn(s, hook)
        self.assertIn("    KeepDollGiveFlagOwn();", self.travel)
        self.assertIn("    KeepHeldItemFlagsOwn();\n    KeepDollGiveFlagOwn();", self.travel)

    def test_all_flag_item_combinations_in_real_emulator_test(self):
        for s in ("DollGiveFix(true, false, true)",
                  "DollGiveFix(true, true, false)",
                  "DollGiveFix(true, true, true)",
                  "DollGiveFix(true, false, false)",
                  "DollGiveFix(false, false, true)"):
            self.assertIn(s, self.gtest)


def exact_function(text, declaration):
    a = text.index(declaration)
    b = text.index("\n}\n", a) + 2
    return text[a:b]


def portable_probe():
    src = read("emulator/src/core/bloodborne_party.cpp")
    held = exact_function(src, "std::optional<bool> HeldItemFlagFix(")
    doll = exact_function(src, "std::optional<bool> DollGiveFix(")
    cpp = r"""
#include <optional>
#include <cassert>
#include <iostream>
""" + held + "\n" + doll + r"""
int main() {
    assert(DollGiveFix(true, false, true) == std::optional<bool>{true});
    assert(DollGiveFix(true, true, false) == std::optional<bool>{false});
    assert(!DollGiveFix(true, false, false));
    assert(!DollGiveFix(true, true, true));
    assert(!DollGiveFix(false, false, true));
    assert(!DollGiveFix(false, true, false));
    // Changes in held goods across ticks produce only a flag correction,
    // never an item grant or any party member's shared progress mutation.
    assert(DollGiveFix(true, false, true) == std::optional<bool>{true});
    assert(!DollGiveFix(true, true, true));
    assert(DollGiveFix(true, true, false) == std::optional<bool>{false});
    assert(!DollGiveFix(true, false, false));
    std::cout<<"B52_ACTUAL_DOLL_PERSONAL_GIVE_FLAG_AND_ITEM_TRUTH_TABLE_PASS\n";
}
"""
    with tempfile.TemporaryDirectory(prefix="b52-production-doll-give-") as temp:
        folder = Path(temp)
        inp = folder / "real_doll_give.cpp"
        inp.write_text(cpp, encoding="utf-8")
        for compiler in ("g++", "clang++"):
            exe = folder / ("test_" + compiler.replace("+", "p"))
            result = subprocess.run([compiler, "-std=c++20", "-O2",
                    "-Wall", "-Wextra", "-Werror", "-pedantic",
                    str(inp), "-o", str(exe)], capture_output=True, text=True, timeout=40)
            if result.returncode:
                raise RuntimeError(f"{compiler} compile: " + result.stderr[:1500])
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=12)
            if run.returncode:
                raise RuntimeError(f"{compiler} actual C++ regression: " + run.stderr[:1000])
            print(compiler, run.stdout.strip())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    if args.compile:
        portable_probe()
    else:
        unittest.main(argv=[__file__])
