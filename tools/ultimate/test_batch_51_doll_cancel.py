"""B51: test actual production DollLevelUpClear on cancellation and fresh sessions.

Source contracts on Linux/Windows, and an isolated native C++20 test that extracts
the real class from emulator/src/core/bloodborne_party.h and compiles its body.
Neither source tests nor extracted-class tests are a full game/rig verification.
"""
import argparse
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


class DollAnimationRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = source("emulator/src/core/bloodborne_party.h")
        cls.travel = source("emulator/src/core/bloodborne_travel.cpp")
        cls.tests = source("emulator/tests/bloodborne/test_bloodborne_flag_rules.cpp")

    def test_actual_doll_flag_only_clears_after_animation_steps(self):
        start = self.header.index("class DollLevelUpClear {")
        end = self.header.index("\n};", start) + 3
        cls = self.header[start:end]
        self.assertIn("bool Tick(bool coop_mode, bool level_up_on, bool blessing_on, bool steps_on)", cls)
        self.assertIn("if (!blessing_seen || steps_on)", cls)
        self.assertIn("blessing_seen = false;", cls)
        self.assertIn("return level_up_on;", cls)
        self.assertNotIn("return coop_mode && level_up_on && was_on && !blessing_on;", cls)

    def test_actual_per_frame_hook_checks_both_game_flag_steps(self):
        actual = self.travel.split("void ClearDollLevelUpFlagAfterHerBlessing()", 1)[1].split(
            "void KeepImpurityBonus(", 1)[0]
        self.assertIn("EventFlagOn(DollBlessingFlag + 1)", actual)
        self.assertIn("EventFlagOn(DollBlessingFlag + 2)", actual)
        self.assertIn("playing && EventFlagOn(DollBlessingFlag), steps_on)", actual)
        self.assertIn("image_base + PartyGhostSetEventFlagOffset", actual)
        self.assertIn("DollLevelUpFlag, false", actual)

    def test_real_emulator_tests_cover_quick_cancel_and_uninterrupted_levelup(self):
        for test in (
            "TheDollsLevelUpFlagGoesOffOnceHerBlessingIsOver",
            "TheDollsLevelUpFlagStaysOnUntilThePlayerStoodUp",
            "TheDollsLevelUpFlagStaysWithoutABlessingOrOutOfCoop",
        ):
            self.assertIn("TEST(BloodborneFlagRules, " + test, self.tests)
        self.assertIn('"menu closed, still kneeling"', self.tests)
        self.assertIn('"stood up and turn finished"', self.tests)


def portable_run():
    content = source("emulator/src/core/bloodborne_party.h")
    start = content.index("class DollLevelUpClear {")
    end = content.index("\n};", start) + 3
    production_class = content[start:end]
    cpp = r"""
#include <cassert>
#include <iostream>
""" + production_class + r"""
int main() {
    DollLevelUpClear clear;
    assert(!clear.Tick(true, true, false, false));
    assert(!clear.Tick(true, true, true, false));
    assert(!clear.Tick(true, true, true, true));
    // Circle pressed before the 54-frame stand-up, blessing stops.
    assert(!clear.Tick(true, true, false, true));
    for (int i = 0; i < 54; ++i) assert(!clear.Tick(true, true, false, true));
    // 72100101 done but 72100102 still set: combined steps_on remains true.
    assert(!clear.Tick(true, true, false, true));
    assert(clear.Tick(true, true, false, false));
    assert(!clear.Tick(true, false, false, false));
    // Second Level Up in same Dream visit still opens.
    assert(!clear.Tick(true, true, true, true));
    assert(!clear.Tick(true, true, false, true));
    assert(clear.Tick(true, true, false, false));
    DollLevelUpClear other;
    assert(!other.Tick(true, true, true, true));
    assert(!other.Tick(false, true, false, false));
    assert(!other.Tick(true, true, false, false));
    DollLevelUpClear unused;
    assert(!unused.Tick(true, true, false, false));
    assert(!unused.Tick(true, true, false, false));
    DollLevelUpClear no_flag;
    assert(!no_flag.Tick(true, false, true, true));
    assert(!no_flag.Tick(true, false, false, false));
    assert(!no_flag.Tick(true, true, false, false));
    std::cout << "B51_REAL_DOLL_FLAG_CLASS_FAST_CANCEL_AND_SECOND_LEVEL_UP_PASS\n";
}
"""
    with tempfile.TemporaryDirectory(prefix="b51-actual-doll-") as temp:
        p = Path(temp)
        src = p / "real_doll_class.cpp"
        src.write_text(cpp, encoding="utf-8")
        for compiler in ("g++", "clang++"):
            exe = p / ("test_" + compiler.replace("+", "p"))
            result = subprocess.run([compiler, "-std=c++20", "-O2",
                    "-Wall", "-Wextra", "-Werror", "-pedantic",
                    str(src), "-o", str(exe)], capture_output=True, text=True, timeout=40)
            if result.returncode:
                raise RuntimeError(f"{compiler} failed to compile production class: " +
                                   result.stderr[:1800])
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=12)
            if run.returncode:
                raise RuntimeError(f"{compiler} regression failed: {run.stderr[:900]}")
            print(compiler, run.stdout.strip())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    if args.compile:
        portable_run()
    else:
        unittest.main(argv=[__file__])
