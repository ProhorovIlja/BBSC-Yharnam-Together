"""B86: inspect and compile the production solo guest-world predicate.

The native policy smoke test extracts the actual C++ function from
bloodborne_team.cpp; its world-flag classifier is a controlled stub. Real
FlagRule / game runtime integration needs the emulator CMake GoogleTests/rig.
No game assets, saves, credentials, or live game process are accessed.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def policy_function() -> str:
    code = source("emulator/src/core/bloodborne_team.cpp")
    marker = "bool KeptChangeStaysWithTeam(s32 flag, bool team_mode, bool plays_in_team) {"
    assert code.count(marker) == 1, "missing or duplicated production B86 helper"
    start = code.index(marker)
    end = code.index("\n}", start) + 2
    body = code[start:end]
    assert "return team_mode && !plays_in_team && IsWorldFlag(flag);" in body
    return body


def emit_native(path: Path) -> None:
    # Compile the exact production C++ predicate with a controlled IsWorldFlag
    # stand-in. Full game's flag classifier is separately tested by native
    # emulator TeamWorld GoogleTests, not by this isolated smoke test.
    cpp = r"""#include <cassert>
#include <cstdint>
using s32 = std::int32_t;
bool IsWorldFlag(s32 flag) {
    return flag == 12401800 || flag == 12407810 || flag == 7240;
}
""" + policy_function() + r"""
int main() {
    for (const s32 flag : {12401800, 12407810, 7240}) {
        assert(KeptChangeStaysWithTeam(flag, true, false));
        assert(!KeptChangeStaysWithTeam(flag, true, true));
        assert(!KeptChangeStaysWithTeam(flag, false, false));
    }
    for (const s32 personal : {6744, 12101022, 52800170}) {
        assert(!KeptChangeStaysWithTeam(personal, true, false));
    }
    assert(!KeptChangeStaysWithTeam(12401800, true, true));
    assert(KeptChangeStaysWithTeam(12401800, true, false));
    return 0;
}
"""
    cpp = cpp.replace("#include <cstdint>", "#include <cstdint>\n#include <initializer_list>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cpp, encoding="utf-8")


class B86WorldIsolation(unittest.TestCase):
    def test_exact_production_predicate(self):
        self.assertIn("IsWorldFlag(flag)", policy_function())

    def test_real_flag_classification_has_personal_and_transient_guards(self):
        cpp = source("emulator/src/core/bloodborne_team.cpp")
        start = cpp.index("bool IsWorldFlag(s32 flag) {")
        end = cpp.index("\n}", start)
        rule = cpp[start:end]
        self.assertIn("FlagOwner::Host", rule)
        self.assertIn("FlagOwner::Shared", rule)
        self.assertIn("!rule.Has(FlagMapPickup)", rule)
        self.assertIn("!rule.Has(FlagResetsOnLoad)", rule)

    def test_actual_state_read_is_locked_and_checks_active_team(self):
        cpp = source("emulator/src/core/bloodborne_server_world.cpp")
        start = cpp.index("bool SavePlaysInTeam() {")
        end = cpp.index("\n}", start)
        helper = cpp[start:end]
        self.assertIn("std::scoped_lock lock{team_mutex};", helper)
        self.assertIn("team_switch && !team_party.empty()", helper)
        self.assertIn("bool SavePlaysInTeam();", source(
            "emulator/src/core/bloodborne_re_internal.h"))

    def test_live_guest_world_loop_skips_before_native_flag_mutation(self):
        cpp = source("emulator/src/core/bloodborne_flags_store.cpp")
        start = cpp.index("size_t SetGuestWorldChanges(bool keep) {")
        end = cpp.index("\n}\n\n} // namespace Coop", start)
        body = cpp[start:end]
        guard = body.index("if (KeptChangeStaysWithTeam(")
        next_flag = body.index("const auto kept = guest_world_kept_ms.find", guard)
        mutate = body.index("reinterpret_cast<SetFlag>", guard)
        self.assertLess(guard, next_flag)
        self.assertLess(next_flag, mutate)
        self.assertIn("++left_to_team;\n            ++it;\n            continue;", body)
        self.assertIn("SaveGuestWorldChanges();", body)
        self.assertIn("const bool team_mode = TeamModeOn();", body)
        self.assertIn("const bool plays_in_team = SavePlaysInTeam();", body)
        self.assertNotIn("world.erase(it)", body[guard:next_flag])

    def test_native_emulator_google_test_covers_world_personal_and_switch(self):
        test = source("emulator/tests/bloodborne/test_bloodborne_team.cpp")
        self.assertIn("TEST(TeamWorld, KeptTeamWorldNeverLeaksIntoSoloGuestSave)", test)
        for number in ("12401800", "12407810", "7240", "6744", "12101022",
                       "52800170"):
            self.assertIn(number, test)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--extract-native":
        emit_native(Path(sys.argv[2]))
        print("B86_EXTRACTED_PRODUCTION_POLICY_READY")
    else:
        unittest.main()
