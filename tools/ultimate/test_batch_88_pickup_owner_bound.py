"""B88: source-grounded owner-bound pickup metadata tests (no actual saves).

Extract and compile the exact production PickupOwnerNameMatches function, not
a reimplementation. Static source contracts cover the live native flag setter,
in-session pickup persistence retries, safe name settling, and rig scenario.
Full shadPS4 CMake/game rig remains separate.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def file(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def production_owner_predicate() -> str:
    s = file("emulator/src/core/bloodborne_team.cpp")
    start_marker = "bool PickupOwnerNameMatches(std::string_view recorded, std::string_view active) {"
    assert s.count(start_marker) == 1
    i = s.index(start_marker)
    j = s.index("\n}", i) + 2
    snippet = s[i:j]
    assert "recorded == active" in snippet
    assert "recorded.empty()" in snippet
    return snippet


def emit_native(path: Path) -> None:
    cpp = (
        "#include <cassert>\n"
        "#include <string>\n"
        "#include <string_view>\n"
        + production_owner_predicate()
        + r"""
int main() {
    assert(PickupOwnerNameMatches("Hunter One", "Hunter One"));
    assert(!PickupOwnerNameMatches("Hunter One", "Hunter Two"));
    assert(!PickupOwnerNameMatches("", "Hunter One"));
    assert(!PickupOwnerNameMatches("Hunter One", ""));
    assert(!PickupOwnerNameMatches(std::string(65, 'x'), std::string(65, 'x')));
    assert(!PickupOwnerNameMatches("Hunter\nOne", "Hunter\nOne"));
    assert(!PickupOwnerNameMatches("Hunter\rOne", "Hunter\rOne"));
    // Same-name collision is explicitly unresolved: name is not a unique ID.
    assert(PickupOwnerNameMatches("Duplicate", "Duplicate"));
    return 0;
}
"""
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cpp, encoding="utf-8")


class B88PickupOwner(unittest.TestCase):
    def test_owner_predicate_uses_actual_production_code(self):
        p = production_owner_predicate()
        self.assertIn("std::string_view", p)
        self.assertIn("recorded.size() <= 64", p)
        self.assertIn("recorded.find('\\n')", p)
        self.assertIn("recorded.find('\\r')", p)

    def test_name_only_after_game_save_has_settled(self):
        s = file("emulator/src/core/bloodborne_server_world.cpp")
        i = s.index("std::string SettledOwnCharacterNameForPickupOwner() {")
        j = s.index("\n}", i)
        block = s[i:j]
        self.assertIn("save_opened_ms.load", block)
        self.assertIn("CharacterNameSettleMs", block)
        self.assertIn("TitleLoadCharacterName(false, OwnCharacterName())", block)
        self.assertIn("if (opened <= 0", block)

    def test_replay_guard_before_any_game_native_flag_setter(self):
        s = file("emulator/src/core/bloodborne_flags_store.cpp")
        i = s.index("size_t SetGuestPickedFlags() {")
        j = s.index("\n}", i) + 2
        block = s[i:j]
        self.assertLess(block.index("if (!GuestPickupOwnerMatches())"),
                        block.index("reinterpret_cast<SetFlag>"))
        self.assertIn("return 0;", block)
        self.assertIn("PickupOwnerNameMatches(ReadGuestPickupOwnerName()", s)
        self.assertIn("SettledOwnCharacterNameForPickupOwner()", s)

    def test_legacy_progress_quarantined_and_owner_not_overwritten(self):
        s = file("emulator/src/core/bloodborne_flags_store.cpp")
        i = s.index("bool SaveGuestProgress(std::span<const s32> flags) {")
        j = s.index("\n}", i) + 2
        body = s[i:j]
        self.assertIn('if (file.bad() || !existing.empty())', body)
        self.assertIn('return false; // unreadable or legacy/unbound journal', body)
        self.assertIn('if (existed && !file.is_open())', body)
        self.assertIn('std::filesystem::exists(progress_file, check_error)', body)
        self.assertLess(body.index("if (file.bad() || !existing.empty())"),
                        body.index("ReplaceGuestMetadataFile(GuestPickupOwnerFile(), active"))
        self.assertIn("PickupOwnerNameMatches(recorded, active)", body)
        self.assertIn('ReplaceGuestMetadataFile(GuestProgressFile(), FormatFlagList(flags))', body)
        self.assertIn('ReplaceGuestMetadataFile(GuestPickupOwnerFile(), "")', body)
        self.assertIn('ReplaceGuestMetadataFile(GuestProgressFile(), "")', body)

    def test_name_unsettled_does_not_drop_first_pickup(self):
        s = file("emulator/src/core/bloodborne_flags_store.cpp")
        i = s.index("void KeepGuestProgress(bool in_session) {")
        j = s.index("// Ritual altars", i)
        block = s[i:j]
        self.assertIn("static bool pickup_metadata_dirty = false;", block)
        self.assertIn("pickup_metadata_dirty = false; // never retry the previous hunter", block)
        self.assertIn("pickup_metadata_dirty = true;", block)
        self.assertIn("pickup_metadata_dirty = !SaveGuestProgress(picked);", block)
        self.assertLess(block.index("if (replay_own_pickups)"),
                        block.index("if (!have_baseline)"))
        self.assertLess(block.index("if (!have_baseline)"),
                        block.index("pickup_metadata_dirty = !SaveGuestProgress(picked);"))

    def test_full_game_google_test_contains_mismatch_cases(self):
        s = file("emulator/tests/bloodborne/test_bloodborne_team.cpp")
        self.assertIn("TEST(GuestPickupReplay, StoredOwnerNameMustMatchActiveHunterBeforeReplay)", s)
        self.assertIn("Hunter Alice", s)
        self.assertIn("Hunter Bob", s)

    def test_real_game_rig_scenario_is_preserved_for_later_validation(self):
        s = file("tools/rig/scenarios.py")
        self.assertIn('SCENARIOS["pickup-after-guest-crash"] = {', s)
        self.assertIn("PICKUP_CRASH_REJOIN_FLAG = 52410140", s)
        self.assertIn('"wait-solo 200"', s)
        self.assertIn('"wait-session 2 420"', s)
        self.assertIn('f"wait-flag {PICKUP_CRASH_REJOIN_FLAG} 1 30"', s)
        self.assertIn('"allow": CRASH_CLEANUP', s)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--extract-native":
        emit_native(Path(sys.argv[2]))
        print("B88_PRODUCTION_OWNER_NAME_PREDICATE_EXTRACTED")
    else:
        unittest.main()
