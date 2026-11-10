"""B53: isolated execution of the actual DollHitEndsBlessing C++ class.

Win/Linux source contracts verify the actual game call site and early guard.
GCC/Clang compile the exact class body extracted from the real game header.
This cannot prove the Doll's in-game NPC animation or actual game 1.09 flags.
"""
import argparse
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class DollHitSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = read("emulator/src/core/bloodborne_party.h")
        cls.travel = read("emulator/src/core/bloodborne_travel.cpp")
        cls.kills = read("emulator/src/core/bloodborne_kills_hp.cpp")
        cls.re = read("emulator/src/core/bloodborne_re_internal.h")
        cls.tests = read("emulator/tests/bloodborne/test_bloodborne_flag_rules.cpp")

    def test_actual_class_requires_local_blessing_and_hp_decrease(self):
        body = self.h.split("class DollHitEndsBlessing {", 1)[1].split("\n};", 1)[0]
        self.assertIn("std::optional<s32> doll_hp", body)
        self.assertIn("last_hp = coop_mode ? doll_hp : std::nullopt;", body)
        self.assertIn("blessing_was_on = coop_mode && blessing_on;", body)
        self.assertIn("was_on && blessing_was_on && before && last_hp", body)
        self.assertIn("*last_hp < *before", body)

    def test_real_doll_actor_and_verified_local_set_flag_hook(self):
        self.assertIn("std::optional<s32> DollHp();", self.re)
        self.assertIn("const u64 doll = DollCharacter();", self.kills)
        self.assertIn("CharacterHp(doll)", self.kills)
        call = self.travel.split("void EndDollBlessingWhenSheIsHit() {", 1)[1].split(
            "\n}\n\n", 1
        )[0]
        for token in (
            "party_controller && GetLocalPlayer() >= 0x10000",
            "EventFlagOn(DollBlessingFlag)",
            "blessing_on ? DollHp() : std::nullopt",
            "image_base + PartyGhostSetEventFlagOffset",
            "DollBlessingFlag, false",
        ):
            self.assertIn(token, call)
        self.assertIn("EndDollBlessingWhenSheIsHit();\n    ClearDollLevelUpFlagAfterHerBlessing();",
                      self.travel)
        for forbidden in ("GiveItem(", "TradeReceive(", "SaveWorld(", "GrantEchoes("):
            self.assertNotIn(forbidden, call)

    def test_actual_emulator_regressions(self):
        self.assertIn("TEST(BloodborneFlagRules, AHitOnTheDollEndsHerBlessing)", self.tests)
        self.assertIn("TEST(BloodborneFlagRules, AHitOnTheDollOutsideHerBlessingChangesNothing)",
                      self.tests)
        self.assertIn("std::nullopt", self.tests)


def compile_real_class():
    h = read("emulator/src/core/bloodborne_party.h")
    a = h.index("class DollHitEndsBlessing {")
    b = h.index("\n};", a) + 3
    code = r"""
#include <optional>
#include <cstdint>
#include <cassert>
#include <iostream>
using s32 = std::int32_t;
""" + h[a:b] + r"""
int main() {
    DollHitEndsBlessing hit;
    assert(!hit.Tick(true, true, 900));    // initial Doll HP sample
    assert(!hit.Tick(true, true, 900));
    assert(hit.Tick(true, true, 586));     // actual damage during blessing
    assert(!hit.Tick(true, true, 586));   // no repeated false positive
    assert(!hit.Tick(true, true, 900));   // HP restored
    assert(hit.Tick(true, true, 0));      // another real drop
    assert(!hit.Tick(true, false, 0));    // blessing ended
    assert(!hit.Tick(true, false, 900));
    assert(!hit.Tick(true, false, 100));  // hit outside blessing
    assert(!hit.Tick(true, true, 100));   // baseline in new blessing
    assert(!hit.Tick(true, true, std::nullopt)); // unload Doll
    assert(!hit.Tick(true, true, 500));   // map load new sample
    assert(hit.Tick(true, true, 450));    // damage after loaded
    assert(!hit.Tick(false, true, 200));  // vanilla mode resets HP+blessing
    assert(!hit.Tick(true, true, 150));   // no stale cross-mode HP
    assert(hit.Tick(true, true, 100));    // true local damage again
    DollHitEndsBlessing solo;
    assert(!solo.Tick(false, true, 900));
    assert(!solo.Tick(false, true, 800));
    assert(!solo.Tick(true, true, 700));
    std::cout << "B53_ACTUAL_DOLL_HP_DROP_BLESSING_ONLY_NO_FALSE_TRIGGERS_PASS\n";
}
"""
    with tempfile.TemporaryDirectory(prefix="b53-real-doll-hit-") as temp:
        folder = Path(temp)
        cpp = folder / "doll_hit.cpp"
        cpp.write_text(code, encoding="utf-8")
        for compiler in ("g++", "clang++"):
            exe = folder / ("hit_" + compiler.replace("+", "p"))
            build = subprocess.run([compiler, "-std=c++20", "-O2",
                                    "-Wall", "-Wextra", "-Werror", "-pedantic",
                                    str(cpp), "-o", str(exe)],
                                   capture_output=True, text=True, timeout=40)
            if build.returncode:
                raise RuntimeError(f"{compiler} actual class compile: {build.stderr[:1500]}")
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
            if result.returncode:
                raise RuntimeError(f"{compiler} actual class regression: {result.stderr[:1000]}")
            print(compiler, result.stdout.strip())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    if args.compile:
        compile_real_class()
    else:
        unittest.main(argv=[__file__])
