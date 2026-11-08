# SPDX-License-Identifier: GPL-2.0-or-later
"""B05: isolate a guest's observed pickup baseline and world-change timestamps.

Compile the exact production C++ owner-change reset, not a rewritten model.
No proprietary Bloodborne files, live accounts, player saves or full builds.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "emulator/src/core/bloodborne_flags_store.cpp"


class GuestProgressOwnerIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = SOURCE.read_text(encoding="utf-8")

    def test_world_timestamp_cache_follows_slot_and_character_reset(self):
        code = self.code
        loader = code.split("std::map<s32, bool>& GuestWorldChanges()", 1)[1].split(
            "\nvoid SaveGuestWorldChanges()", 1
        )[0]
        self.assertIn("guest_world_slot != character_slot.load()", loader)
        self.assertLess(
            loader.index("guest_world_kept_ms.clear();"),
            loader.index("guest_world_slot = character_slot.load();"),
        )
        reset = code.split("void ForgetGuestWorldChanges() {", 1)[1].split(
            "\nvoid KeepWorldChanges(", 1
        )[0]
        self.assertIn("guest_world_kept_ms.clear();", reset)
        self.assertLess(
            reset.index("GuestWorldChanges().clear();"),
            reset.index("guest_world_kept_ms.clear();"),
        )
        # The reset and loader operate under the same mutex, rather than
        # swapping the slot-specific timestamp map asynchronously.
        self.assertIn("std::scoped_lock lock{guest_world_mutex};", reset)

    def test_pickup_owner_check_precedes_session_flag_observation(self):
        code = self.code.split("void KeepGuestProgress(bool in_session)", 1)[1].split(
            "\n// Ritual altars", 1
        )[0]
        self.assertIn("static u64 generation = 0;", code)
        self.assertIn("deferred_reward_character_generation.load(std::memory_order_relaxed)", code)
        self.assertLess(
            code.index("ResetGuestPickupObservationIfOwnerChanged("),
            code.index("if (in_session) {"),
        )
        self.assertLess(
            code.index("ResetGuestPickupObservationIfOwnerChanged("),
            code.index("seen_on.insert(flag);"),
        )

    def test_compile_production_cpp_owner_switch_for_five_hunters(self):
        text = self.code
        start = text.index("void ResetGuestPickupObservationIfOwnerChanged(")
        end = text.index("\n}\n\nvoid KeepGuestProgress(bool in_session)", start) + 2
        exact_function = text[start:end]
        compiler = shutil.which("g++") or shutil.which("c++")
        if not compiler:
            self.skipTest("C++20 compiler unavailable")
        fixture = r"""
#include <chrono>
#include <cstdint>
#include <unordered_set>
using s32 = std::int32_t;
using u64 = std::uint64_t;
// PRODUCTION_FUNCTION
#define CHECK(c) do { if (!(c)) return __LINE__; } while (0)
int main() {
    int observed_slot = -1;
    u64 observed_generation = 0;
    bool baseline = true;
    bool at_home = true;
    std::unordered_set<s32> seen{11, 12};
    auto home = std::chrono::steady_clock::time_point{std::chrono::seconds{500}};
    // A new player joining must never inherit an earlier player's baseline.
    for (int hunter = 0; hunter < 5; ++hunter) {
        baseline = true;
        at_home = true;
        seen.insert(100 + hunter);
        home = std::chrono::steady_clock::time_point{std::chrono::seconds{700}};
        ResetGuestPickupObservationIfOwnerChanged(
            hunter, 10, observed_slot, observed_generation,
            baseline, seen, at_home, home);
        CHECK(observed_slot == hunter && observed_generation == 10);
        CHECK(!baseline && !at_home && seen.empty());
        CHECK(home == std::chrono::steady_clock::time_point{});
    }
    // Same save slot and generation: preserve the active observation.
    baseline = true;
    at_home = true;
    seen.insert(999);
    home = std::chrono::steady_clock::time_point{std::chrono::seconds{900}};
    ResetGuestPickupObservationIfOwnerChanged(
        4, 10, observed_slot, observed_generation,
        baseline, seen, at_home, home);
    CHECK(baseline && at_home && seen.count(999) == 1);
    CHECK(home == std::chrono::steady_clock::time_point{std::chrono::seconds{900}});
    // Same slot, new character generation: new baseline, even without a slot change.
    ResetGuestPickupObservationIfOwnerChanged(
        4, 11, observed_slot, observed_generation,
        baseline, seen, at_home, home);
    CHECK(observed_slot == 4 && observed_generation == 11);
    CHECK(!baseline && !at_home && seen.empty());
    CHECK(home == std::chrono::steady_clock::time_point{});
    return 0;
}
"""
        fixture = fixture.replace("// PRODUCTION_FUNCTION", exact_function)
        with tempfile.TemporaryDirectory(prefix="bbsc-b05-") as td:
            source = Path(td) / "owner.cpp"
            binary = Path(td) / "owner"
            source.write_text(fixture, encoding="utf-8")
            build = subprocess.run(
                [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                 str(source), "-o", str(binary)],
                capture_output=True, text=True, timeout=40,
            )
            self.assertEqual(build.returncode, 0, build.stderr[-2000:])
            run = subprocess.run(
                [str(binary)], capture_output=True, text=True, timeout=8,
            )
            self.assertEqual(run.returncode, 0, f"fixture line {run.returncode}: {run.stderr}")


if __name__ == "__main__":
    unittest.main()
