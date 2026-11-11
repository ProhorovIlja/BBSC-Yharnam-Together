# SPDX-License-Identifier: GPL-2.0-or-later
"""B77: execute real upstream-derived production multi-phantom ledger methods.

We extract actual method definitions (not reimplementations), provide only
synthetic HeldGoods types and bell exclusion, and test two separate one-shot
grant lanes. No user savedata, game binary or server is read.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
TEAM = ROOT / "emulator/src/core/bloodborne_team.cpp"
TRAVEL = ROOT / "emulator/src/core/bloodborne_travel.cpp"


def definition(text: str, anchor: str) -> str:
    start = text.index(anchor)
    open_brace = text.index("{", start)
    level = 0
    for idx in range(open_brace, len(text)):
        if text[idx] == "{":
            level += 1
        elif text[idx] == "}":
            level -= 1
            if level == 0:
                return text[start:idx + 1]
    raise AssertionError(f"Missing terminating brace for {anchor}")


class LiveMultiSessionLedger(unittest.TestCase):
    def test_live_game_hooks_route_pending_sessions_into_secondary_lane(self):
        text = TRAVEL.read_text(encoding="utf-8")
        body = text.split("void GiveBackPhantomKeyItems() {", 1)[1].split(
            "// See LampsToRelight", 1
        )[0]
        for marker in (
            "static PhantomKeyItemLedger subsequent_phantom_debt;",
            "subsequent_phantom_debt.Load({});",
            "subsequent_phantom_debt.LookAtPhantom(list, seen)",
            "subsequent_phantom_debt.LookAtOwn(list, home)",
            "subsequent_phantom_debt.GaveBack();",
            "if (!subsequent_missing) return;",
            "return_attempt.AcknowledgeObservedHome(subsequent_missing->size())",
            "return_attempt.MarkRequested(); // before every native void grant",
            "for (const HeldGoods& held : *subsequent_missing)",
        ):
            self.assertIn(marker, body, marker)
        phantom = body.split("if (ReadValue<s32>(player, 0x78) == PhantomType) {", 1)[1]
        self.assertLess(phantom.index("subsequent_phantom_debt.LookAtPhantom(list, seen)"),
                        phantom.index("last_look = HeldKeyGoods();"))
        own = body.split("std::optional<std::vector<HeldGoods>> subsequent_missing;", 1)[1]
        self.assertLess(own.index("subsequent_phantom_debt.LookAtOwn(list, home)"),
                        own.index("if (phantom_list == 0)"))
        self.assertLess(own.index("return_attempt.MarkRequested(); // before every native void grant"),
                        own.index("for (const HeldGoods& held : *subsequent_missing)"))
        self.assertLess(own.index("return_attempt.AcknowledgeObservedHome(subsequent_missing->size())"),
                        own.index("subsequent_phantom_debt.GaveBack();"))
        self.assertIn("reported_pending_rejoin_list = 0;", own)
        self.assertNotIn("CreateNewRevision(", body)  # still OFFLINE on purpose

    def test_compiled_actual_production_ledger_three_joins_and_late_receipt(self):
        source = TEAM.read_text(encoding="utf-8")
        real = [
            source[source.index("namespace {\ns32 CountIn("):
                   source.index("std::vector<HeldGoods> OwnKeyItemsForPhantom(")],
            definition(source, "std::vector<HeldGoods> OwnKeyItemsForPhantom("),
            definition(source, "std::vector<OwedKeyItem> PhantomKeyItemsGained("),
            definition(source, "std::vector<HeldGoods> OwedKeyItemsToGive("),
            source[source.index("namespace {\n// Both lists as one"):
                   source.index("void PhantomKeyItemLedger::Load(")],
            definition(source, "void PhantomKeyItemLedger::Load("),
            definition(source, "std::vector<HeldGoods> PhantomKeyItemLedger::LookAtPhantom("),
            definition(source, "std::optional<std::vector<HeldGoods>> PhantomKeyItemLedger::LookAtOwn("),
            definition(source, "void PhantomKeyItemLedger::GaveBack("),
            definition(source, "std::vector<OwedKeyItem> PhantomKeyItemLedger::Owed("),
        ]
        compiler = os.environ.get("CXX") or shutil.which("g++") or shutil.which("clang++")
        if not compiler:
            self.skipTest("No C++20 compiler installed")
        fixture = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <optional>
#include <ranges>
#include <span>
#include <utility>
#include <vector>
using u32 = std::uint32_t;
using u64 = std::uint64_t;
using s32 = std::int32_t;
struct HeldGoods { u32 goods; s32 count; bool operator==(const HeldGoods&) const = default; };
struct OwedKeyItem { u32 goods; s32 gained; s32 held; bool operator==(const OwedKeyItem&) const = default; };
bool IsBellGoods(u32 id) { return id == 200 || id == 205 || id == 225 || id == 4312; }
class PhantomKeyItemLedger {
public:
    void Load(std::vector<OwedKeyItem> owed);
    std::vector<HeldGoods> LookAtPhantom(u64 list, std::vector<HeldGoods> held);
    std::optional<std::vector<HeldGoods>> LookAtOwn(u64 list, std::vector<HeldGoods> held);
    void GaveBack();
    std::vector<OwedKeyItem> Owed() const;
private:
    u64 phantom_list = 0;
    std::vector<HeldGoods> first_look, last_look, own_look;
    std::vector<OwedKeyItem> carried;
};
// EXACT_PRODUCTION_LEDGER
int main() {
    PhantomKeyItemLedger ledger;
    assert(ledger.LookAtPhantom(0x1100, {}).empty());
    assert(ledger.LookAtPhantom(0x1100, {{4110,1}}).empty());
    (void)ledger.LookAtPhantom(0x2200, {});
    assert(ledger.LookAtPhantom(0x2200, {{4000,1}}).empty());
    (void)ledger.LookAtPhantom(0x3300, {});
    assert(ledger.LookAtPhantom(0x3300, {{4103,1}}).empty());
    const std::vector<OwedKeyItem> owed = {{4103,1,1},{4000,1,1},{4110,1,1}};
    assert(ledger.Owed() == owed);
    assert(!ledger.LookAtOwn(0x3300, {{4103,1}}).has_value());
    const auto due = ledger.LookAtOwn(0x4400, {});
    assert(due.has_value());
    assert((*due == std::vector<HeldGoods>{{4103,1},{4000,1},{4110,1}}));
    // The game's void-return GiveItems is NOT a receipt.
    assert(ledger.Owed() == owed);
    const auto in_home = ledger.LookAtOwn(0x4400, {{4103,1},{4000,1},{4110,1}});
    assert(in_home && in_home->empty());
    ledger.GaveBack();
    assert(ledger.Owed().empty());
    // Another hunter's process must never inherit the old in-memory tracker.
    ledger.Load({});
    assert(ledger.Owed().empty());
    return 0;
}
'''
        fixture = fixture.replace("// EXACT_PRODUCTION_LEDGER", "\n\n".join(real))
        with tempfile.TemporaryDirectory(prefix="bbsc-b77-real-ledger-") as td:
            src = Path(td) / "production_ledger.cpp"
            exe = Path(td) / "production_ledger"
            src.write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra",
                 "-Werror", "-pedantic", str(src), "-o", str(exe)],
                text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr[-3500:])
            run = subprocess.run([str(exe)], text=True,
                                 capture_output=True, timeout=20)
            self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == "__main__":
    unittest.main()
