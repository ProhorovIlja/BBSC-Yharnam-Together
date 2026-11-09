# SPDX-License-Identifier: GPL-2.0-or-later
"""B31: compile the actual production NPC/story delta algorithm with C++20.

Source-proven bug: adding/removing a flag-store block stopped ALL NPC/story
deltas, including changes to older blocks that both reports covered.
No proprietary script, game executable, user save or full client build.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
TEAM = ROOT / "emulator/src/core/bloodborne_team.cpp"
HEADER = ROOT / "emulator/src/core/bloodborne_team.h"
WORLD = ROOT / "emulator/src/core/bloodborne_server_world.cpp"
GTEST = ROOT / "emulator/tests/bloodborne/test_bloodborne_team.cpp"


class NpcStoryCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.team = TEAM.read_text(encoding="utf-8")
        cls.header = HEADER.read_text(encoding="utf-8")
        cls.world = WORLD.read_text(encoding="utf-8")

    def test_real_game_applies_only_to_shared_flag_blocks(self):
        code = self.team
        head = code.split("std::vector<std::pair<s32, bool>> TeamStoryToFollow(", 1)[1]
        head = head.split("bool KeptChangeYieldsToTeam(", 1)[0]
        self.assertIn("flags_per_block == 0", head)
        self.assertIn("std::binary_search(before.blocks.begin()", head)
        self.assertIn("std::binary_search(after.blocks.begin()", head)
        self.assertIn("IsTeamStoryFlag(flag) && shared_block(flag)", head)
        self.assertIn("u32 flags_per_block);", self.header)
        consumer = self.world.split("void FollowTeamStory(", 1)[1].split(
            "bool IsTeamScreenVerb(", 1
        )[0]
        self.assertIn("ReadFlagStore().flags_per_block", consumer)
        self.assertIn(
            "TeamStoryToFollow(team_story_followed, target, flags_per_block)", consumer
        )
        self.assertLess(
            consumer.index("if (flags_per_block == 0)"),
            consumer.index("team_story_followed = std::move(target);"),
        )
        # B32 moved the old single-field reset into a stronger helper that
        # clears both the NPC story baseline and game-unconfirmed retry queue.
        reset = self.world.split("void ResetTeamStoryTracking() {", 1)[1].split(
            "constexpr s64 TeamWorldReportMs", 1
        )[0]
        self.assertIn("team_story_followed = {};", reset)
        self.assertIn("team_story_retries.clear();", reset)
        self.assertIn("++team_story_context_generation;", reset)
        for context in (
            "never compare quest states across different worlds",
            "every freshly loaded save needs its own baseline",
            "new team/world must not inherit the old NPC-story delta",
        ):
            self.assertIn("ResetTeamStoryTracking(); // " + context, self.world)
        self.assertIn("NpcStoryChangesSurviveHostWorldBlockExpansionAndContraction",
                      GTEST.read_text(encoding="utf-8"))

    def test_exact_production_cpp_keeps_npc_quest_deltas_on_world_coverage_churn(self):
        code = self.team
        start = code.index("bool IsTeamStoryFlag(s32 flag) {")
        end = code.index("\n}\n\n} // namespace", start) + 2
        classification = code[start:end]
        start = code.index("std::vector<std::pair<s32, bool>> TeamStoryToFollow(")
        end = code.index("\n}\n\nbool KeptChangeYieldsToTeam(", start) + 2
        algorithm = code[start:end]

        compiler = (shutil.which("cl") if os.name == "nt"
                    else shutil.which("g++") or shutil.which("clang++"))
        self.assertIsNotNone(compiler, "C++20 compiler required")
        fixture = r'''
#include <algorithm>
#include <array>
#include <cstdint>
#include <ranges>
#include <span>
#include <utility>
#include <vector>
using u32 = std::uint32_t;
using s32 = std::int32_t;
struct WorldFlags {
    std::vector<s32> on;
    std::vector<u32> blocks;
};
struct FlagRange {};
const FlagRange* RowFor(s32 flag) {
    static constexpr std::array<s32, 9> special{
       6630, 6749, 9401, 9403, 12100122, 72100100, 72410300, 72410301, 72410302
    };
    static const FlagRange rule{};
    return std::ranges::find(special, flag) == special.end() ? nullptr : &rule;
}
inline constexpr std::array<s32, 3> TimeOfDayFlags{9800, 9801, 9802};
// ACTUAL_STORY_CLASSIFIER
// ACTUAL_STORY_ALGORITHM
#define CHECK(x) do { if (!(x)) return __LINE__; } while (false)
int main() {
    const WorldFlags before{
        {1100, 1121, 1205, 2301, 6749, 9401, 12410000},
        {1, 2, 6, 9, 12410}
    };
    const WorldFlags after{
        {1100, 1300, 6749, 9401, 12410000, 12411001},
        {1, 6, 9, 12410, 12411}
    };
    const auto actual = TeamStoryToFollow(before, after, 1000);
    const std::vector<std::pair<s32,bool>> wanted{
        {1121, false}, {1205, false}, {1300, true}
    };
    CHECK(actual == wanted); // NPC quest flags survived map coverage change
    CHECK(TeamStoryToFollow(after, before, 1000) ==
          (std::vector<std::pair<s32,bool>>{{1121,true},{1205,true},{1300,false}}));
    CHECK(TeamStoryToFollow(before, before, 1000).empty());
    CHECK(TeamStoryToFollow(WorldFlags{}, after, 1000).empty());
    CHECK(TeamStoryToFollow(before, after, 0).empty());

    WorldFlags new_block = before;
    new_block.blocks.push_back(3);
    new_block.on.push_back(3400); // in newly arrived block, not safe live
    std::ranges::sort(new_block.on);
    CHECK(TeamStoryToFollow(before, new_block, 1000).empty());

    WorldFlags per_player = before;
    per_player.on.push_back(72410300); // player-specific Iosefka dialogue
    std::ranges::sort(per_player.on);
    CHECK(TeamStoryToFollow(before, per_player, 1000).empty());

    WorldFlags time = before;
    time.on.push_back(9801);
    std::ranges::sort(time.on);
    CHECK(TeamStoryToFollow(before, time, 1000).empty());

    WorldFlags map = before;
    map.on.push_back(12410001);
    std::ranges::sort(map.on);
    CHECK(TeamStoryToFollow(before, map, 1000).empty()); // map actors need map load

    WorldFlags carried = before;
    carried.on.push_back(1300);
    std::ranges::sort(carried.on);
    CHECK(TeamStoryToFollow(before, carried, 1000) ==
          (std::vector<std::pair<s32,bool>>{{1300,true}}));
    return 0;
}
'''
        fixture = fixture.replace("// ACTUAL_STORY_CLASSIFIER", classification).replace(
            "// ACTUAL_STORY_ALGORITHM", algorithm
        )
        with tempfile.TemporaryDirectory(prefix="bbsc-b31-story-coverage-") as directory:
            directory = Path(directory)
            source = directory / "story.cpp"
            exe = directory / ("story.exe" if os.name == "nt" else "story")
            source.write_text(fixture, encoding="utf-8")
            if os.name == "nt":
                build = [compiler, "/nologo", "/std:c++20", "/EHsc", "/W4",
                         str(source), f"/Fe:{exe}"]
            else:
                build = [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                         str(source), "-o", str(exe)]
            built = subprocess.run(build, cwd=directory, capture_output=True,
                                   text=True, timeout=55)
            self.assertEqual(
                built.returncode, 0, built.stdout[-2000:] + built.stderr[-3000:]
            )
            ran = subprocess.run([str(exe)], cwd=directory, capture_output=True,
                                 text=True, timeout=10)
            self.assertEqual(
                ran.returncode, 0,
                f"compiled real NPC-story algorithm failed at {ran.returncode}: "
                + ran.stderr[-1400:],
            )


if __name__ == "__main__":
    unittest.main()
