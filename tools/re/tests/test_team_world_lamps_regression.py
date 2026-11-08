# SPDX-License-Identifier: GPL-2.0-or-later
"""Protect the already-integrated co-op team-switch lamp fix from regression.

Upstream YT PR #488 was closed without merging *that PR*, but the complete
WithoutRelitLamps behavior and C++ test already exist in this 1.4.0 fork.
Compile the ACTUAL production helper with synthetic flags; avoid a duplicate
patch, a game dump, production saves or a costly full Windows build.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORE = ROOT / "emulator/src/core"


class TeamWorldLamps(unittest.TestCase):
    def test_existing_fix_is_connected_to_lifecycle_and_world_post(self):
        flags = (CORE / "bloodborne_flags_store.cpp").read_text(encoding="utf-8")
        party = (CORE / "bloodborne_party.cpp").read_text(encoding="utf-8")
        travel = (CORE / "bloodborne_travel.cpp").read_text(encoding="utf-8")
        fixtures = (ROOT / "emulator/tests/bloodborne/test_bloodborne_flag_rules.cpp").read_text(encoding="utf-8")
        self.assertEqual(party.count("FlagChanges WithoutRelitLamps("), 1)
        self.assertEqual(travel.count("FlagChanges LeaveOutRelitLamps("), 1)
        self.assertIn("std::scoped_lock lock{relit_lamps_mutex};", travel)
        self.assertIn("relit_lamps.insert(flag);", travel)
        self.assertIn("return WithoutRelitLamps(std::move(changes), relit_lamps);", travel)
        self.assertIn("const FlagChanges changes = LeaveOutRelitLamps(", flags)
        self.assertIn("ForgetRelitLamps();", flags)
        self.assertIn("if (!sharing)", flags)
        self.assertIn("TEST(BloodborneFlagRules, ALampLitAgainIsNoWorldChange)", fixtures)

    def test_the_real_production_lamp_filter_preserves_genuine_team_progress(self):
        source = (CORE / "bloodborne_party.cpp").read_text(encoding="utf-8")
        start = source.index("FlagChanges WithoutRelitLamps(")
        end = source.index("\nstd::vector<s32> LampsToRelight(", start)
        real_helper = source[start:end]
        self.assertIn("std::erase_if(changes.set,", real_helper)
        self.assertIn("relit.erase(flag) != 0", real_helper)
        compiler = shutil.which("g++") or shutil.which("c++")
        if not compiler:
            self.skipTest("No native C++20 compiler available")
        synthetic = r'''
#include <algorithm>
#include <cstdint>
#include <set>
#include <vector>
using s32 = std::int32_t;
struct FlagChanges {
    std::vector<s32> set, cleared;
};
// EXACT_PRODUCTION_HELPER
#define CHECK(expr) do { if (!(expr)) return __LINE__; } while (0)
int main() {
    // The guest's own lamp was relit after joining another team.
    std::set<s32> relit{12807810};
    FlagChanges incoming{{12807810, 12105032}, {2411}};
    FlagChanges filtered = WithoutRelitLamps(incoming, relit);
    CHECK((filtered.set == std::vector<s32>{12105032}));
    CHECK((filtered.cleared == std::vector<s32>{2411}));
    CHECK(relit.empty());
    // Lighting the same lamp legitimately later is new world progress.
    filtered = WithoutRelitLamps({{12807810}, {}}, relit);
    CHECK((filtered.set == std::vector<s32>{12807810}));
    // Four guests and a host: overlapping own lamps must never leak into
    // this team's world just because the watcher ticks after a scene load.
    relit = {12807810, 12417830, 13007811, 13107850};
    filtered = WithoutRelitLamps({{12807810, 12105032, 12417830, 13007811,
                                   13501800, 13107850}, {998, 2411}}, relit);
    CHECK((filtered.set == std::vector<s32>{12105032, 13501800}));
    CHECK((filtered.cleared == std::vector<s32>{998, 2411}));
    CHECK(relit.empty());
    // A team-world genuine change remains even when no lamp was relit.
    filtered = WithoutRelitLamps({{13501800}, {251}}, relit);
    CHECK((filtered.set == std::vector<s32>{13501800}));
    CHECK((filtered.cleared == std::vector<s32>{251}));
    return 0;
}
'''.replace("// EXACT_PRODUCTION_HELPER", real_helper)
        with tempfile.TemporaryDirectory(prefix="bbsc-team-lamps-") as td:
            cpp = Path(td) / "team_lamps.cpp"
            exe = Path(td) / "team_lamps"
            cpp.write_text(synthetic, encoding="utf-8")
            result = subprocess.run(
                [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                 str(cpp), "-o", str(exe)], capture_output=True,
                text=True, timeout=35,
            )
            self.assertEqual(result.returncode, 0, result.stderr[-1800:])
            checked = subprocess.run(
                [str(exe)], capture_output=True, text=True, timeout=8)
            self.assertEqual(checked.returncode, 0,
                             "Real lamp filter returned fixture source line "
                             + str(checked.returncode) + ": " + checked.stderr)


if __name__ == "__main__":
    unittest.main()
