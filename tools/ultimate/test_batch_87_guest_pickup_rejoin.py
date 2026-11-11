"""B87: production source contracts and isolated native owner-scope regression.

No game data, player saves, credentials, or live machines. C++ test compiles
the EXACT production owner-scope predicate extracted from bloodborne_team.cpp.
Flag replay in the actual game is additionally checked at its C++ source call
site. Full native emulator GoogleTests and real crash/rejoin rig remain separate.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def production_guard() -> str:
    s = source("emulator/src/core/bloodborne_team.cpp")
    key = "bool ShouldReplayGuestPickupsInSession(bool in_session,"
    assert s.count(key) == 1
    start = s.index(key)
    end = s.index("\n}", start) + 2
    result = s[start:end]
    assert "current_generation != 0" in result
    assert "observed_slot == current_slot && observed_generation == current_generation" in result
    return result


def emit_native(path: Path) -> None:
    cxx = ("""#include <cassert>
#include <cstdint>
using u64 = std::uint64_t;
""" + production_guard() + """
int main() {
    assert(ShouldReplayGuestPickupsInSession(true, 2, 1, -1, 0));
    assert(ShouldReplayGuestPickupsInSession(true, 2, 1, 2, 1));
    assert(!ShouldReplayGuestPickupsInSession(false, 2, 1, 2, 1));
    assert(!ShouldReplayGuestPickupsInSession(true, -1, 1, -1, 0));
    assert(!ShouldReplayGuestPickupsInSession(true, 2, 0, -1, 0));
    assert(!ShouldReplayGuestPickupsInSession(true, 3, 1, 2, 1));
    assert(!ShouldReplayGuestPickupsInSession(true, 2, 2, 2, 1));
    assert(ShouldReplayGuestPickupsInSession(true, 2, 2, 2, 2));
    return 0;
}
""")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cxx, encoding="utf-8")


class B87GuestPickup(unittest.TestCase):
    def test_real_owner_policy_present(self):
        self.assertIn("observed_slot < 0", production_guard())
        self.assertIn("current_slot >= 0", production_guard())

    def test_replay_before_first_baseline_and_not_with_nested_lock(self):
        cpp = source("emulator/src/core/bloodborne_flags_store.cpp")
        start = cpp.index("void KeepGuestProgress(bool in_session) {")
        end = cpp.index("// Ritual altars", start)
        block = cpp[start:end]
        replay = block.index("if (replay_own_pickups) {")
        baseline = block.index("if (!have_baseline) {")
        lock = block.index("std::scoped_lock lock{guest_picked_mutex};")
        self.assertLess(replay, baseline)
        self.assertLess(baseline, lock)
        self.assertIn("SetGuestPickedFlags()", block[replay:baseline])
        self.assertIn("if (!IsPartyGuestRole() || now - last < GuestProgressInterval)", block)
        self.assertIn("ResetGuestPickupObservationIfOwnerChanged(", block)
        self.assertLess(block.index("ShouldReplayGuestPickupsInSession("),
                        block.index("ResetGuestPickupObservationIfOwnerChanged("))
        self.assertIn("SaveGuestProgress(picked);", block)

    def test_generation_and_slot_invalidate_cached_pickups(self):
        cpp = source("emulator/src/core/bloodborne_flags_store.cpp")
        i = cpp.index("std::optional<std::vector<s32>> guest_picked;")
        j = cpp.index("void SaveGuestProgress(", i)
        block = cpp[i:j]
        self.assertIn("u64 guest_picked_generation = 0;", block)
        self.assertIn("guest_picked_slot != current_slot", block)
        self.assertIn("guest_picked_generation != current_generation", block)
        self.assertIn("guest_picked_generation = current_generation;", block)
        self.assertIn("GuestProgressFile()", block)

    def test_existing_new_hunter_backup_and_map_load_replay_preserved(self):
        cpp = source("emulator/src/core/bloodborne_flags_store.cpp")
        begin = cpp.index("void ForgetSlotIfNewCharacter() {")
        end = cpp.index("// After the pickups are set", begin)
        block = cpp[begin:end]
        self.assertIn("BackUpSlotLists();", block)
        self.assertIn("GuestPickedFlags().clear();", block)
        self.assertIn("SaveGuestProgress({});", block)
        self.assertIn("deferred_reward_character_generation.fetch_add(", block)
        mapload = cpp[cpp.index("void SetGuestPickupsBeforeMapItems() {"):]
        self.assertLess(mapload.index("ForgetSlotIfNewCharacter();"),
                        mapload.index("if (const size_t set = SetGuestPickedFlags();"))
        self.assertIn("if (!InPartySession())", mapload[:mapload.index("ForgetSlotIfNewCharacter();")])

    def test_real_emulator_gtest_covers_rejoin_and_identity_change(self):
        cpp = source("emulator/tests/bloodborne/test_bloodborne_team.cpp")
        self.assertIn("TEST(GuestPickupReplay, CrashRejoinRestoresCurrentHunterButNotOldSlot)", cpp)
        self.assertIn("same slot now carries a new hunter generation", cpp)
        self.assertIn("different save slot", cpp)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--extract-native":
        emit_native(Path(sys.argv[2]))
        print("B87_EXACT_PRODUCTION_OWNER_GUARD_EXTRACTED")
    else:
        unittest.main()
