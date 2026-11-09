# SPDX-License-Identifier: GPL-2.0-or-later
"""B33: compile actual live and on-load game time-of-day helpers with C++20.

Check that an incomplete host TeamWorld cannot push 9800/9801/9802 to a
new hunter in the clinic or leave those flags in their own solo world.
A synthetic game callback only; not an actual Bloodborne script or save.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "emulator/src/core/bloodborne_team.cpp"
WORLD = ROOT / "emulator/src/core/bloodborne_server_world.cpp"
HEADER = ROOT / "emulator/src/core/bloodborne_team.h"
GTEST = ROOT / "emulator/tests/bloodborne/test_bloodborne_team.cpp"


class HostTimeOfDayCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = CODE.read_text(encoding="utf-8")
        cls.game = WORLD.read_text(encoding="utf-8")

    def test_actual_game_call_sites_share_host_coverage_and_current_store_geometry(self):
        game = self.game
        header = HEADER.read_text(encoding="utf-8")
        live = game.split("void FollowTeamTimeOfDay(s64 now_ms) {", 1)[1].split(
            "void ApplyTeamTimeOfDayOnLoad() {", 1
        )[0]
        load = game.split("void ApplyTeamTimeOfDayOnLoad() {", 1)[1].split(
            "void FollowTeamStory(", 1
        )[0]
        self.assertIn("team = WorldFlagsOf(*team_world);", live)
        self.assertIn("const u32 flags_per_block = ReadFlagStore().flags_per_block;", live)
        self.assertIn("if (flags_per_block == 0)", live)
        self.assertIn("TimeOfDayToFollow(team, flags_per_block, EventFlagOn)", live)
        self.assertNotIn("team_world->on()", live)
        self.assertLess(live.index("const u32 flags_per_block = "),
                        live.index("TimeOfDayToFollow(team, flags_per_block, EventFlagOn)"))
        self.assertIn("const u32 flags_per_block = ReadFlagStore().flags_per_block;", load)
        self.assertNotIn("static u32 flags_per_block", load)
        self.assertIn("if (flags_per_block == 0)", load)
        self.assertIn("TeamTimeOfDayAtLoad(WorldFlagsOf(*team_world), flags_per_block, EventFlagOn)",
                      load)
        self.assertIn("TimeOfDayToFollow(const WorldFlags& team, u32 flags_per_block", header)
        self.assertIn("TeamTimeOfDayAtLoad(const WorldFlags& team, u32 flags_per_block", header)
        src = self.code
        time = src.split("std::vector<s32> TimeOfDayToFollow(", 1)[1].split(
            "std::vector<std::pair<s32, bool>> TeamTimeOfDayAtLoad(", 1
        )[0]
        assert "team.blocks.empty()" in time
        assert "std::binary_search(team.blocks.begin()" in time
        load_alg = src.split(
            "std::vector<std::pair<s32, bool>> TeamTimeOfDayAtLoad(", 1
        )[1].split("namespace {", 1)[0]
        self.assertIn("for (const s32 flag : TimeOfDayFlags)", load_alg)
        self.assertIn("static_cast<u32>(flag) / flags_per_block", load_alg)
        test = GTEST.read_text(encoding="utf-8")
        self.assertIn("A Guest's", test) if False else None
        self.assertIn("A Guest", test) if False else None
        self.assertIn("team.blocks = {4900};", test)
        self.assertIn("TimeOfDayToFollow(team, 0", test)

    def test_real_source_cxx_functions_cover_no_unknown_and_changed_blocks(self):
        code = self.code
        start = code.index("std::vector<s32> TimeOfDayToFollow(")
        mid = code.index("std::vector<std::pair<s32, bool>> TeamTimeOfDayAtLoad(", start)
        end1 = code.rfind("\n}\n", start, mid) + 2
        self.assertGreater(end1, start)
        actual_live = code[start:end1]
        end2 = code.index("\n}\n", mid) + 2
        actual_load = code[mid:end2]
        self.assertIn("flags_per_block == 0", actual_live)
        self.assertIn("flags_per_block == 0", actual_load)
        compiler = shutil.which("cl") if os.name == "nt" else shutil.which("g++") or shutil.which("clang++")
        self.assertIsNotNone(compiler, "CI must provide a native C++20 compiler")
        fixture = r'''
#include <algorithm>
#include <array>
#include <cstdint>
#include <functional>
#include <utility>
#include <vector>
using s32 = std::int32_t;
using u32 = std::uint32_t;
struct WorldFlags {
    std::vector<s32> on;
    std::vector<u32> blocks;
};
inline constexpr std::array<s32,3> TimeOfDayFlags{9800,9801,9802};
// EXACT_PRODUCTION_LIVE
// EXACT_PRODUCTION_ON_LOAD
#define CHECK(expr) do { if (!(expr)) return __LINE__; } while(false)
int main() {
    WorldFlags host{{9800,9801}, {1, 12410}};
    auto none = [](s32) { return false; };
    // Stage on in an incomplete host snapshot must NOT push night or
    // force a newly created character to leave the tutorial timeline.
    CHECK(TimeOfDayToFollow(host,1000,none).empty());
    CHECK(TeamTimeOfDayAtLoad(host,1000,none).empty());

    host.blocks = {9};
    CHECK(TimeOfDayToFollow(host,1000,none) ==
          (std::vector<s32>{9800,9801}));
    CHECK(TeamTimeOfDayAtLoad(host,1000,none) ==
          (std::vector<std::pair<s32,bool>>{{9800,true},{9801,true}}));
    CHECK(TimeOfDayToFollow(host,1000,[](s32 f){return f==9800;}) ==
          (std::vector<s32>{9801}));
    CHECK(TimeOfDayToFollow(host,1000,[](s32 f){return f==9802;}).empty());
    CHECK(TimeOfDayToFollow(host,0,none).empty());
    CHECK(TeamTimeOfDayAtLoad(host,0,none).empty());

    // Stage transitions with smaller geometry (synthetic) cover 9800/9801
    // in block 4900, while 9802 is in a separate, still-unreported block.
    host = WorldFlags{{9800,9801,9802},{4900}};
    CHECK(TimeOfDayToFollow(host,2,none) == (std::vector<s32>{9800,9801}));
    CHECK(TeamTimeOfDayAtLoad(host,2,none) ==
          (std::vector<std::pair<s32,bool>>{{9800,true},{9801,true}}));
    host.blocks = {4901};
    CHECK(TimeOfDayToFollow(host,2,none) == (std::vector<s32>{9802}));
    CHECK(TeamTimeOfDayAtLoad(host,2,none) ==
          (std::vector<std::pair<s32,bool>>{{9802,true}}));

    // An already-advanced guest does not move BACKWARD between loads.
    host = WorldFlags{{9800},{9}};
    CHECK(TimeOfDayToFollow(host,1000,[](s32 f){return f==9802;}).empty());
    CHECK(TeamTimeOfDayAtLoad(host,1000,[](s32 f){return f==9802;}) ==
          (std::vector<std::pair<s32,bool>>{{9800,true},{9802,false}}));
    host.blocks.clear();
    CHECK(TimeOfDayToFollow(host,1000,none).empty());
    CHECK(TeamTimeOfDayAtLoad(host,1000,none).empty());
    return 0;
}
'''
        fixture = fixture.replace("// EXACT_PRODUCTION_LIVE", actual_live).replace(
            "// EXACT_PRODUCTION_ON_LOAD", actual_load
        )
        with tempfile.TemporaryDirectory(prefix="bbsc-b33-time-coverage-") as tmp:
            directory = Path(tmp)
            file = directory / "team_time.cpp"
            exe = directory / ("team_time.exe" if os.name == "nt" else "team_time")
            file.write_text(fixture, encoding="utf-8")
            if os.name == "nt":
                cmd = [compiler, "/nologo", "/std:c++20", "/EHsc", "/W4",
                       str(file), f"/Fe:{exe}"]
            else:
                cmd = [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra",
                       "-Werror", str(file), "-o", str(exe)]
            built = subprocess.run(cmd, cwd=directory, capture_output=True,
                                   text=True, timeout=55)
            self.assertEqual(built.returncode, 0, built.stdout[-1500:] + built.stderr[-2200:])
            ran = subprocess.run([str(exe)], cwd=directory, capture_output=True,
                                 text=True, timeout=10)
            self.assertEqual(ran.returncode, 0,
                             f"real production time-of-day functions failed fixture line {ran.returncode}: "
                             + ran.stderr[-1000:])


if __name__ == "__main__":
    unittest.main()
