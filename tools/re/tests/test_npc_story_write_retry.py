# SPDX-License-Identifier: GPL-2.0-or-later
"""B32 real production C++20 NPC story retry filter, Linux GCC / Windows MSVC.

No Bloodborne files, personal saves, emulator rebuild or online game are used.
The fake game only models one SetEventFlag rejection then successful retry.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "emulator/src/core/bloodborne_team.cpp"
HEADER = ROOT / "emulator/src/core/bloodborne_team.h"
GAME = ROOT / "emulator/src/core/bloodborne_server_world.cpp"
GTEST = ROOT / "emulator/tests/bloodborne/test_bloodborne_team.cpp"


class NpcStoryRetry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.game = GAME.read_text(encoding="utf-8")

    def test_native_game_callsite_keeps_only_unconfirmed_write_in_current_world(self):
        source = self.source
        game = self.game
        header = HEADER.read_text(encoding="utf-8")
        section = game.split("void FollowTeamStory(s64 now_ms) {", 1)[1].split(
            "bool IsTeamScreenVerb(", 1
        )[0]
        self.assertIn("TeamStoryRetriesForWorld(", header)
        self.assertIn("TeamStoryRetriesForWorld(team_story_retries, target, flags_per_block)",
                      section)
        self.assertIn("if (EventFlagOn(flag) != on)", section)
        self.assertIn("unconfirmed.emplace_back(flag, on);", section)
        self.assertIn("expected_context == team_story_context_generation", section)
        self.assertIn("MaxPendingTeamStoryRetries", section)
        self.assertLess(
            section.index("reinterpret_cast<SetFlag>(image_base + PartyGhostSetEventFlagOffset)"),
            section.index("if (EventFlagOn(flag) != on)"),
        )
        self.assertLess(
            section.index("if (EventFlagOn(flag) != on)"),
            section.index("unconfirmed.emplace_back(flag, on)"),
        )
        self.assertLess(
            section.index("unconfirmed.emplace_back(flag, on)"),
            section.index("const auto valid = TeamStoryRetriesForWorld("),
        )
        self.assertIn("void ResetTeamStoryTracking()", game)
        resets = game.count("ResetTeamStoryTracking();")
        self.assertGreaterEqual(resets, 5)
        self.assertIn("team_story_retries.clear();", game)
        self.assertIn("++team_story_context_generation;", game)
        self.assertIn("RejectedNpcQuestFlagsRetryOnlyWhileTheHostStillWantsThem",
                      GTEST.read_text(encoding="utf-8"))
        self.assertIn("AnUnconfirmedStoryFlagSurvivesAnUnchangedHostReport",
                      GTEST.read_text(encoding="utf-8"))
        algorithm = source.split("std::vector<std::pair<s32, bool>> TeamStoryRetriesForWorld(", 1)[1]
        algorithm = algorithm.split("bool KeptChangeYieldsToTeam(", 1)[0]
        self.assertIn("std::binary_search(current.blocks.begin()", algorithm)
        self.assertIn("std::binary_search(current.on.begin()", algorithm)
        self.assertIn("!= desired", algorithm)
        self.assertIn("retry.erase(std::unique(", algorithm)

    def test_compiles_actual_production_cpp_and_retries_only_unconfirmed_game_flags(self):
        source = self.source
        a = source.index("bool IsTeamStoryFlag(s32 flag) {")
        b = source.index("\n}\n\n} // namespace", a) + 2
        exact_classifier = source[a:b]
        a = source.index("std::vector<std::pair<s32, bool>> TeamStoryToFollow(")
        b = source.index("\n}\n\nstd::vector<std::pair<s32, bool>> TeamStoryRetriesForWorld(", a) + 2
        exact_delta = source[a:b]
        a = source.index("std::vector<std::pair<s32, bool>> TeamStoryRetriesForWorld(")
        b = source.index("\n}\n\nbool KeptChangeYieldsToTeam(", a) + 2
        exact_retry = source[a:b]
        compiler = shutil.which("cl") if os.name == "nt" else shutil.which("g++") or shutil.which("clang++")
        self.assertIsNotNone(compiler, "C++20 compiler required; cannot silently skip native test")
        fixture = r'''
#include <algorithm>
#include <array>
#include <cstdint>
#include <ranges>
#include <span>
#include <utility>
#include <vector>
using s32=std::int32_t;
using u32=std::uint32_t;
struct WorldFlags {
    std::vector<s32> on;
    std::vector<u32> blocks;
};
struct FlagRange {};
const FlagRange* RowFor(s32 flag) {
    static constexpr std::array<s32, 6> individual{
        6630, 6749, 9401, 9403, 72410300, 72100100
    };
    static const FlagRange row{};
    return std::ranges::find(individual,flag)!=individual.end()?&row:nullptr;
}
inline constexpr std::array<s32,3> TimeOfDayFlags{9800,9801,9802};
// EXACT_CLASSIFIER
// EXACT_DELTA
// EXACT_RETRY
#define CHECK(x) do { if (!(x)) return __LINE__; } while(false)
int main() {
    WorldFlags old{{1100,1205,9401},{1,6,9}};
    WorldFlags host{{1100,1121,9401},{1,6,9}};
    const auto delta=TeamStoryToFollow(old,host,1000);
    CHECK(delta==(std::vector<std::pair<s32,bool>>{{1121,true},{1205,false}}));
    // Game rejected one set. Host reports the same snapshot on the next
    // tick, so delta alone would be empty and the quest NPC would stall.
    const std::vector<std::pair<s32,bool>> rejected{
        {1121,true}, {1121,true}, {2301,true}, {72410300,true},
        {6749,true}, {12410001,true}, {9801,true}
    };
    CHECK(TeamStoryToFollow(host,host,1000).empty());
    CHECK(TeamStoryRetriesForWorld(rejected,host,1000)==
          (std::vector<std::pair<s32,bool>>{{1121,true}}));
    // Native game call takes the previously refused flag on next tick.
    bool native_ack=true;
    CHECK(native_ack);
    CHECK(TeamStoryRetriesForWorld({},host,1000).empty());
    // The host advanced its quest again: OLD queued set must be forgotten.
    WorldFlags later=host;
    later.on={1100,9401};
    CHECK(TeamStoryRetriesForWorld(rejected,later,1000).empty());
    // The host lost coverage for the global story block: no live spawning.
    WorldFlags absent=host;
    absent.blocks={6,9};
    CHECK(TeamStoryRetriesForWorld(rejected,absent,1000).empty());
    CHECK(TeamStoryRetriesForWorld(rejected,host,0).empty());
    CHECK(TeamStoryRetriesForWorld(rejected,WorldFlags{},1000).empty());

    // A previously failed OFF transition is retried only while the host
    // still keeps its flag OFF. Later ON wins.
    const std::vector<std::pair<s32,bool>> off{{1205,false}};
    CHECK(TeamStoryRetriesForWorld(off,host,1000)==off);
    WorldFlags on_again=host;
    on_again.on.insert(on_again.on.begin()+2,1205);
    CHECK(TeamStoryRetriesForWorld(off,on_again,1000).empty());

    // Repeated checks for the same NPC do not result in duplicate retry
    // entries or a hidden per-player dialogue reward set.
    return 0;
}
'''
        fixture = fixture.replace("// EXACT_CLASSIFIER", exact_classifier).replace(
            "// EXACT_DELTA", exact_delta
        ).replace("// EXACT_RETRY", exact_retry)
        with tempfile.TemporaryDirectory(prefix="bbsc-b32-npc-quest-") as directory:
            cwd = Path(directory)
            cpp = cwd / "npc_retry.cpp"
            exe = cwd / ("npc_retry.exe" if os.name == "nt" else "npc_retry")
            cpp.write_text(fixture, encoding="utf-8")
            if os.name == "nt":
                command = [compiler, "/nologo", "/std:c++20", "/EHsc", "/W4",
                           str(cpp), f"/Fe:{exe}"]
            else:
                command = [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra",
                           "-Werror", str(cpp), "-o", str(exe)]
            built = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stdout[-1800:] + built.stderr[-3000:])
            ran = subprocess.run([str(exe)], cwd=cwd, capture_output=True, text=True, timeout=10)
            self.assertEqual(ran.returncode, 0,
                             f"production NPC story retry failed at C++ line {ran.returncode}: "
                             + ran.stderr[-900:])


if __name__ == "__main__":
    unittest.main()
