# SPDX-License-Identifier: GPL-2.0-or-later
"""C++ production regression: five-hunter join tasks must match their OWN member.

No Bloodborne executable, dump, Discord messages, live users, server or secrets.
The pure selector is compiled from production bloodborne_party.cpp, while the
source contract asserts FinishWaitingJoins passes an exact session identity.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PARTY = ROOT / "emulator/src/core/bloodborne_party.cpp"
BOARDS = ROOT / "emulator/src/core/bloodborne_boards.cpp"


class MemberSpecificJoins(unittest.TestCase):
    def test_production_selector_on_two_three_and_five_hunter_boards(self):
        source = PARTY.read_text(encoding="utf-8")
        signature = "bool MemberStandsOnMap(std::span<const MemberVitals> board,"
        self.assertEqual(source.count(signature), 1)
        first = source.index(signature)
        end = source.index("\nbool SomeoneElseStands(", first)
        method = source[first:end]
        self.assertIn("known.member == member", method)
        self.assertIn("known.vital == Vital::Up", method)
        self.assertIn("known.map == map", method)
        cxx = shutil.which("c++")
        if not cxx:
            self.skipTest("No C++ compiler is installed")
        program = r'''
#include <algorithm>
#include <cstdint>
#include <ranges>
#include <span>
#include <string>
#include <string_view>
#include <vector>
using u32 = std::uint32_t;
enum class Vital { Up, Down };
struct MemberVitals {
    std::string member;
    u32 map = 0;
    Vital vital = Vital::Down;
};
// ACTUAL_PRODUCTION_SELECTOR

#define CHECK(x) do { if (!(x)) return __LINE__; } while (0)
int main() {
    const u32 dream = 400, ward = 410;
    // Five in one party: the host plus four remote hunters, spread over maps.
    std::vector<MemberVitals> five = {
        {"host", dream, Vital::Up},
        {"late", ward, Vital::Up},
        {"guest2", dream, Vital::Down},
        {"guest3", dream, Vital::Up},
        {"guest4", dream, Vital::Up},
    };
    // The first waiting join must not be unblocked merely because host,
    // guest3 and guest4 stand there. A different member's map is irrelevant.
    CHECK(!MemberStandsOnMap(five, "late", dream));
    CHECK(MemberStandsOnMap(five, "late", ward));
    CHECK(!MemberStandsOnMap(five, "guest2", dream));
    CHECK(MemberStandsOnMap(five, "guest3", dream));
    CHECK(MemberStandsOnMap(five, "guest4", dream));
    CHECK(MemberStandsOnMap(five, "host", dream));
    CHECK(!MemberStandsOnMap(five, "nonmember", dream));
    CHECK(!MemberStandsOnMap(five, "", dream));
    CHECK(!MemberStandsOnMap(five, "guest3", 0));
    five[1].map = dream;
    CHECK(MemberStandsOnMap(five, "late", dream));
    five[3].vital = Vital::Down;
    CHECK(!MemberStandsOnMap(five, "guest3", dream));

    const std::vector<MemberVitals> two(five.begin(), five.begin() + 2);
    CHECK(MemberStandsOnMap(two, "late", dream));
    CHECK(!MemberStandsOnMap(two, "guest4", dream));
    const std::vector<MemberVitals> three(five.begin(), five.begin() + 3);
    CHECK(!MemberStandsOnMap(three, "guest2", dream));
    CHECK(MemberStandsOnMap(three, "late", dream));
    return 0;
}
'''
        program = program.replace("// ACTUAL_PRODUCTION_SELECTOR", method)
        with tempfile.TemporaryDirectory(prefix="bbsc-member-join-") as temp:
            cpp = Path(temp) / "joins.cpp"
            exe = Path(temp) / "joins"
            cpp.write_text(program, encoding="utf-8")
            compile_result = subprocess.run(
                [cxx, "-std=c++20", "-Wall", "-Wextra", "-Werror",
                 "-O2", str(cpp), "-o", str(exe)],
                text=True, capture_output=True, timeout=45,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            actual = subprocess.run(
                [str(exe)], text=True, capture_output=True, timeout=8,
            )
            self.assertEqual(actual.returncode, 0,
                             "Production C++ selector failed at fixture line "
                             + str(actual.returncode) + ": " + actual.stderr)

    def test_each_waiting_task_uses_exact_session_name_not_any_hunter(self):
        source = BOARDS.read_text(encoding="utf-8")
        signature = "void FinishWaitingJoins(bool in_session) {"
        self.assertEqual(source.count(signature), 1)
        method = source.split(signature, 1)[1].split(
            "\n}\n\n} // namespace Coop", 1
        )[0]
        self.assertIn("const u64 member_id = task + 0xC8;", method)
        self.assertIn("SessionMemberBoardName(member_id, online_ids)", method)
        self.assertIn("MemberStandsOnMap(view.board.members, *board_name, map)", method)
        self.assertIn("Tick(now, member_here,", method)
        self.assertIn("online_ids.empty() ? std::nullopt", method)
        self.assertIn("member.vital != Vital::Up", method)
        self.assertIn("view.Fresh()", method)
        self.assertNotIn("SomeoneElseStands(", method)
        self.assertNotIn("Tick(now, here,", method)
        self.assertLess(
            method.index("SessionMemberBoardName(member_id, online_ids)"),
            method.index("Tick(now, member_here,"),
        )


if __name__ == "__main__":
    unittest.main()
