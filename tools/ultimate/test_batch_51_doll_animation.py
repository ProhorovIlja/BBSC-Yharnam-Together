"""B51 C++ Doll blessing anti-softlock: compile the REAL production class.

A single isolated class is extracted verbatim from bloodborne_party.h so the
unit fixture cannot accidentally pass against a disconnected duplicate.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[2]
HEAD = ROOT / "emulator/src/core/bloodborne_party.h"
TRAVEL = ROOT / "emulator/src/core/bloodborne_travel.cpp"
GTEST = ROOT / "emulator/tests/bloodborne/test_bloodborne_flag_rules.cpp"


class DollStandupInvariant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = HEAD.read_text(encoding="utf-8")
        cls.travel = TRAVEL.read_text(encoding="utf-8")
        cls.gtest = GTEST.read_text(encoding="utf-8")

    def test_real_game_tick_checks_both_animation_steps(self):
        self.assertIn("EventFlagOn(DollBlessingFlag + 1)", self.travel)
        self.assertIn("EventFlagOn(DollBlessingFlag + 2)", self.travel)
        self.assertIn("EventFlagOn(DollBlessingFlag), steps_on)", self.travel)
        self.assertIn("return level_up_on;", self.header)
        self.assertIn("if (!blessing_seen || steps_on)", self.header)
        self.assertNotIn("return coop_mode && level_up_on && was_on && !blessing_on;", self.header)

    def test_actual_emulator_gtest_has_cancel_and_mode_guards(self):
        self.assertIn("TEST(BloodborneFlagRules, TheDollsLevelUpFlagStaysOnUntilThePlayerStoodUp)", self.gtest)
        self.assertIn("TEST(BloodborneFlagRules, TheDollsLevelUpFlagStaysWithoutABlessingOrOutOfCoop)", self.gtest)
        self.assertIn("clear.Tick(true, true, false, true)", self.gtest)
        self.assertIn("clear.Tick(true, true, false, false)", self.gtest)

    def test_does_not_touch_unrelated_invasion_or_save_ownership(self):
        self.assertIn("class DollLevelUpClear", self.header)
        self.assertIn("void ClearDollLevelUpFlagAfterHerBlessing()", self.travel)


def compile_real_class():
    src = HEAD.read_text(encoding="utf-8")
    begin = src.index("class DollLevelUpClear {")
    end = src.index("\n};", begin) + 3
    code = src[begin:end]
    test = r'''
#include <cassert>
#include <iostream>
''' + code + r'''
int main() {
    DollLevelUpClear quick;
    assert(!quick.Tick(true, true, false, false));
    assert(!quick.Tick(true, true, true, false));
    assert(!quick.Tick(true, true, true, true));
    assert(!quick.Tick(true, true, false, true)); // user cancels but kneeling
    assert(!quick.Tick(true, true, false, true)); // waits
    assert( quick.Tick(true, true, false, false)); // finally stood up
    assert(!quick.Tick(true, true, false, false)); // once
    assert(!quick.Tick(true, false, false, false));

    DollLevelUpClear never;
    assert(!never.Tick(true, true, false, false)); // no blessing
    assert(!never.Tick(true, true, false, true));  // stale flag alone
    assert(!never.Tick(true, true, false, false));

    DollLevelUpClear solo;
    assert(!solo.Tick(false, true, true, true));
    assert(!solo.Tick(false, true, false, false));
    assert(!solo.Tick(true, true, false, false)); // no carried state
    assert(!solo.Tick(true, true, true, true));
    assert(!solo.Tick(false, true, false, true)); // reset
    assert(!solo.Tick(true, true, false, false));
    std::cout << "B51_REAL_DOLL_CLASS_QUICK_CANCEL_WAIT_FOR_STAND_UP_PASS\\n";
}
'''
    with tempfile.TemporaryDirectory(prefix="b51-doll-class-") as folder:
        source = Path(folder) / "real_doll.cpp"
        source.write_text(test, encoding="utf-8")
        for compiler in ("g++", "clang++"):
            exe = Path(folder) / ("doll_" + compiler.replace("+", "p"))
            args = [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic", str(source), "-o", str(exe)]
            c = subprocess.run(args, capture_output=True, text=True, timeout=35)
            if c.returncode:
                raise RuntimeError(f"{compiler} compile failed:\n" + c.stderr[:1600])
            r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
            if r.returncode:
                raise RuntimeError(f"{compiler} test failed: " + r.stderr[:700])
            print(compiler, r.stdout.strip())


if __name__ == "__main__":
    if "--compile" in sys.argv:
        compile_real_class()
    else:
        unittest.main(argv=[sys.argv[0]])
