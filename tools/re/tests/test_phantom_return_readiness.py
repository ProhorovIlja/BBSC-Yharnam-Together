# SPDX-License-Identifier: GPL-2.0-or-later
"""B74: compile the exact production native-give readiness function with stubs.

No original game, live inventory, server, or savedata access. A ready vtable
only authorizes an *attempt*; it is NOT native return-value or save ACK proof.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
TRADE = ROOT / "emulator/src/core/bloodborne_trade.cpp"
TRAVEL = ROOT / "emulator/src/core/bloodborne_travel.cpp"


class PhantomReturnReadiness(unittest.TestCase):
    def test_live_return_does_not_discard_on_missing_manager_or_key_list(self):
        travel = TRAVEL.read_text(encoding="utf-8")
        fn = travel.split("void GiveBackPhantomKeyItems() {", 1)[1].split(
            "// See LampsToRelight", 1
        )[0]
        self.assertIn("if (list == 0) {", fn)
        self.assertLess(fn.index("if (list == 0)"), fn.index("ReadValue<s32>(player, 0x78)"))
        self.assertIn("PhantomReturnMayRetireSnapshot(", fn)
        self.assertIn("TradeItemsReadyToGive()", fn)
        self.assertIn("const std::vector<HeldGoods> to_return", fn)
        # There are two legitimate resets: B69 owner change and this return
        # transition. The latter must be AFTER the readiness gate.
        transition = fn.split("const std::vector<HeldGoods> to_return", 1)[1]
        self.assertLess(transition.index("PhantomReturnMayRetireSnapshot"),
                        transition.index("phantom_list = 0;"))
        self.assertLess(transition.index("return; // unready, or prior grant ambiguous"),
                        transition.index("phantom_list = 0;"))
        self.assertIn("for (const HeldGoods& held : to_return)", transition)
        self.assertIn("return_attempt.MarkRequested();", transition)
        self.assertIn("return_attempt.ObservedInOwnInventory(to_return.size())", transition)
        self.assertIn("!return_attempt.Requested() && TradeItemsReadyToGive()", transition)
        self.assertLess(transition.index("return_attempt.MarkRequested();"),
                        transition.index("for (const HeldGoods& held : to_return)"))
        self.assertLess(transition.index("return_attempt.ObservedInOwnInventory"),
                        transition.index("phantom_list = 0;"))
        self.assertNotIn("phantom_list = 0;\n    for (const HeldGoods& held : to_return)", transition)
        self.assertIn("return_attempt.Reset(); // never carry an attempted grant", fn)
        # Rejoin guard must run BEFORE throttle and BEFORE any mutation of
        # last_look, first_look or phantom_list for a new guest list.
        phantom_branch = fn.split("if (ReadValue<s32>(player, 0x78) == PhantomType)", 1)[1]
        self.assertIn("subsequent_tracking || !return_attempt.MayUpdatePhantomSnapshot()", phantom_branch)
        self.assertIn("subsequent_phantom_debt.LookAtPhantom(list, seen)", phantom_branch)
        self.assertIn("reported_pending_rejoin_list", phantom_branch)
        self.assertLess(phantom_branch.index("subsequent_phantom_debt.LookAtPhantom"),
                        phantom_branch.index("last_look = HeldKeyGoods();"))
        self.assertLess(phantom_branch.index("MayUpdatePhantomSnapshot"),
                        phantom_branch.index("phantom_list = list;"))
        self.assertLess(phantom_branch.index("return;\n        }"),
                        phantom_branch.index("last_look = HeldKeyGoods();"))
        self.assertIn("subsequent_phantom_debt.LookAtOwn(list, home)", fn)
        self.assertIn("if (!subsequent_missing) return;", fn)
        self.assertIn("subsequent_phantom_debt.GaveBack();", fn)
        self.assertIn("return_attempt.MarkRequested(); // before every native void grant", fn)
        self.assertLess(fn.index("return_attempt.MarkRequested(); // before every native void grant"),
                        fn.index("for (const HeldGoods& held : *subsequent_missing)"))
        self.assertIn("subsequent_phantom_debt.Load({});", fn)
        self.assertNotIn("CreateNewRevision(", fn)
        self.assertNotIn("gave back {} x goods {}", transition)

    def test_compiled_actual_native_give_readiness_fails_closed(self):
        content = TRADE.read_text(encoding="utf-8")
        anchor = "bool TradeItemsReadyToGive() {"
        self.assertEqual(content.count(anchor), 1)
        start = content.index(anchor)
        end = content.index("\n}\n", start) + 2
        production = content[start:end]
        self.assertIn("if (!trade_sites.load()) return false;", production)
        self.assertIn("MapItemManPointerOffset", production)
        self.assertIn("HasVtable(", production)
        compiler = shutil.which("g++") or shutil.which("clang++")
        if not compiler:
            self.skipTest("No C++20 compiler available")
        fixture = r'''
#include <atomic>
#include <cstdint>
using u64 = std::uint64_t;
static std::atomic<bool> trade_sites{false};
static u64 manager = 0;
static bool vtable_valid = false;
static int reads = 0;
static int vtable_checks = 0;
constexpr u64 image_base = 0x1000;
constexpr u64 MapItemManPointerOffset = 0x100;
constexpr u64 MapItemManVtable = 0x7000;
template <typename T> T ReadValue(u64 address, u64 offset) {
    (void)offset;
    if (address != image_base + MapItemManPointerOffset) return T{};
    ++reads;
    return static_cast<T>(manager);
}
bool HasVtable(u64 ptr, u64 expected, const char* caller) {
    (void)caller;
    ++vtable_checks;
    return ptr == manager && expected == MapItemManVtable && vtable_valid;
}
// EXACT_PRODUCTION
#define CHECK(e) do { if (!(e)) return __LINE__; } while (0)
int main() {
    CHECK(!TradeItemsReadyToGive());
    CHECK(reads == 0 && vtable_checks == 0);
    trade_sites.store(true);
    CHECK(!TradeItemsReadyToGive());
    CHECK(reads == 1 && vtable_checks == 0);
    manager = 0x5000;
    CHECK(!TradeItemsReadyToGive());
    CHECK(vtable_checks == 1);
    vtable_valid = true;
    CHECK(TradeItemsReadyToGive());
    CHECK(vtable_checks == 2);
    trade_sites.store(false);
    CHECK(!TradeItemsReadyToGive());
    CHECK(vtable_checks == 2);
    return 0;
}
'''
        fixture = fixture.replace("// EXACT_PRODUCTION", production)
        with tempfile.TemporaryDirectory(prefix="bbsc-b74-native-gate-") as td:
            src = Path(td) / "real_trade_gate.cpp"
            exe = Path(td) / "real_trade_gate"
            src.write_text(fixture, encoding="utf-8")
            built = subprocess.run(
                [compiler, "-std=c++20", "-Wall", "-Wextra", "-Werror", "-O2",
                 str(src), "-o", str(exe)],
                text=True, capture_output=True, timeout=45,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([str(exe)], text=True,
                                 capture_output=True, timeout=12)
            self.assertEqual(ran.returncode, 0, f"failed at fixture line {ran.returncode}")


if __name__ == "__main__":
    unittest.main()
