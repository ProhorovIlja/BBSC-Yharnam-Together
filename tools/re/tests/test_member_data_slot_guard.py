# SPDX-License-Identifier: GPL-2.0-or-later
"""B12: compile the actual production join/data readiness code and simulate hot joins.

No game files, game memories, accounts or live server. This is not a real
Bloodborne/Link4 five-player gameplay test.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
PARTY_CPP = ROOT / "emulator/src/core/bloodborne_party.cpp"
PARTY_H = ROOT / "emulator/src/core/bloodborne_party.h"
BOARDS = ROOT / "emulator/src/core/bloodborne_boards.cpp"
NATIVE_GTEST = ROOT / "emulator/tests/bloodborne/test_bloodborne_member_data.cpp"


class MemberDataSlotGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.party = PARTY_CPP.read_text(encoding="utf-8")
        cls.header = PARTY_H.read_text(encoding="utf-8")
        cls.boards = BOARDS.read_text(encoding="utf-8")

    def test_prod_hot_join_callsite_never_requests_without_a_per_member_slot(self):
        s = self.boards
        first = s.index("void FinishWaitingJoins(bool in_session) {")
        last = s.index("\n} // namespace Coop", first)
        part = s[first:last]
        needle = "MemberDataRequestReady(member_here, slot, parts)"
        self.assertEqual(part.count(needle), 1)
        self.assertIn("const u64 parts = slot ? MemberDataPartsAddress(*slot) : 0;", part)
        self.assertIn("const bool member_data_ready = " + needle, part)
        self.assertIn("waiting->second.Tick(now, member_data_ready,", part)
        self.assertIn("member_data_ready ? ReadValue<u8>(parts, 0) : 0", part)
        self.assertIn("case MemberDataWait::Action::Request:", part)
        self.assertIn("SendMemberDataRequest(net, member_id);", part)
        self.assertLess(part.index("case MemberDataWait::Action::Request:"),
                        part.index("SendMemberDataRequest(net, member_id);"))
        slot = s[s.index("std::optional<s32> MemberDataSlot("):
                 s.index("\nu64 MemberDataPartsAddress(", s.index("std::optional<s32> MemberDataSlot("))]
        self.assertIn("net < 0x10000", slot)
        self.assertIn("HasMemoryAccess(net, 0x88, MemoryProt::CpuRead)", slot)
        self.assertIn("id_equal(node + 0x10, member_id)", slot)
        self.assertIn("slot >= 0 && slot < 4", slot)
        address = s[s.index("u64 MemberDataPartsAddress("):
                    s.index("\nvoid SendMemberDataRequest(", s.index("u64 MemberDataPartsAddress("))]
        self.assertIn("MemoryProt::CpuWrite", address)

    def test_compile_actual_cpp_guard_and_state_machine(self):
        cpp = self.party
        header = self.header
        h_start = header.index("class MemberDataWait {")
        h_end = header.index("\n};", h_start) + 3
        real_class = header[h_start:h_end]
        c_start = cpp.index("bool HasAllMemberData(u8 parts) {")
        c_end = cpp.index("\nbool OwnDataWatch::Observe(", c_start)
        real_source = cpp[c_start:c_end]
        self.assertIn("MemberDataRequestReady", real_source)
        compiler = shutil.which("g++") or shutil.which("clang++") or shutil.which("c++")
        if not compiler:
            self.skipTest("No C++20 compiler available")
        program = r"""
#include <cstdint>
#include <optional>
using u8 = std::uint8_t;
using u64 = std::uint64_t;
using s32 = std::int32_t;
using s64 = std::int64_t;
constexpr u8 MemberDataParts = 0x1E;
class_placeholder
source_placeholder
#define VERIFY(b) do { if (!(b)) return __LINE__; } while (false)
int main() {
    using A = MemberDataWait::Action;
    // Five hunters = one local and four remote slots.
    for (s32 slot = 0; slot < 4; ++slot) {
        VERIFY(MemberDataRequestReady(true, slot, 0x10000 + slot));
    }
    VERIFY(!MemberDataRequestReady(true, -1, 0x10000));
    VERIFY(!MemberDataRequestReady(true, 4, 0x10000));
    VERIFY(!MemberDataRequestReady(true, std::nullopt, 0x10000));
    VERIFY(!MemberDataRequestReady(true, 2, 0));
    VERIFY(!MemberDataRequestReady(true, 2, 0xFFF));
    VERIFY(!MemberDataRequestReady(false, 2, 0x10000));
    MemberDataWait one, two;
    VERIFY(one.Tick(0, MemberDataRequestReady(true, std::nullopt, 0), 0x1F) == A::None);
    VERIFY(one.Tick(9000, MemberDataRequestReady(true, std::nullopt, 0), 0x1F) == A::None);
    VERIFY(one.Requests() == 0);
    VERIFY(two.Tick(0, MemberDataRequestReady(true, 1, 0x20000), 0x1F) == A::None);
    VERIFY(two.Tick(1000, MemberDataRequestReady(true, 1, 0x20000), 0x1F) == A::Request);
    VERIFY(two.Requests() == 1);
    VERIFY(two.Tick(1100, true, 0x1B) == A::None);
    VERIFY(two.Tick(1200, true, 0x1F) == A::Create);
    VERIFY(one.Requests() == 0);  // A different remote did not unblock this slot.
    VERIFY(one.Tick(10000, MemberDataRequestReady(true, 0, 0x20000), 0x1F) == A::None);
    VERIFY(one.Tick(11000, true, 0x1F) == A::Request);
    VERIFY(one.Tick(11001, true, 0x1F) == A::Create);
    // A slot missing in the middle of joining must invalidate an old request.
    MemberDataWait recovered;
    VERIFY(recovered.Tick(0, true, 0) == A::None);
    VERIFY(recovered.Tick(1000, true, 0) == A::Request);
    VERIFY(recovered.Tick(1001, MemberDataRequestReady(true, 0, 0), 0x1F) == A::None);
    VERIFY(recovered.Tick(2000, MemberDataRequestReady(true, 0, 0x20000), 0x1F) == A::None);
    VERIFY(recovered.Tick(3000, true, 0x1F) == A::Request);
    VERIFY(recovered.Requests() == 2);
    VERIFY(recovered.Tick(3001, true, 0x1F) == A::Create);
    return 0;
}
""".replace("class_placeholder", real_class).replace("source_placeholder", real_source)
        with tempfile.TemporaryDirectory(prefix="bbsc-b12-") as td:
            path = Path(td) / "member_guard.cpp"
            binary = Path(td) / "member_guard"
            path.write_text(program, encoding="utf-8")
            built = subprocess.run(
                [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                 str(path), "-o", str(binary)],
                capture_output=True, text=True, timeout=45,
            )
            self.assertEqual(built.returncode, 0, built.stderr[-2500:])
            run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, f"source-level fixture exit line {run.returncode}")

    def test_integrated_gtest_exercises_missing_slot_and_all_four_remote_slots(self):
        s = NATIVE_GTEST.read_text(encoding="utf-8")
        for name in ("VisibleNameWithoutMemberDataSlotDoesNotSendOrCreate",
                     "LosingSlotDuringJoinCannotUseOldDataOnReturn",
                     "OnlyTheFourRemoteSlotsAreRequestable"):
            self.assertIn("TEST(BloodborneMemberData, " + name + ")", s)
        self.assertIn("bool MemberDataRequestReady(", self.header)


if __name__ == "__main__":
    unittest.main()
