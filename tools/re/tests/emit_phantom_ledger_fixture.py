# SPDX-License-Identifier: GPL-2.0-or-later
"""Emit the actual ledger functions with no guest runtime or game assets."""
from pathlib import Path
import sys

core = Path(__file__).resolve().parents[3] / "emulator/src/core"
header = (core / "bloodborne_team.h").read_text(encoding="utf-8")
team = (core / "bloodborne_team.cpp").read_text(encoding="utf-8")


def between(source, begin, end):
    start = source.index(begin)
    return source[start:source.index(end, start + len(begin))]


bell = between(header, "inline constexpr std::array<u32, 4> BellGoods", "\n}") + "\n}\n"
types = between(header, "struct HeldGoods {", "// Kaniel 2026-10-23:")
count = between(team, "namespace {\ns32 CountIn(", "namespace {\nthread_local u32 silent_item_gets")
ledger = between(team, "std::vector<OwedKeyItem> PhantomKeyItemsGained(", "bool IsWorldFlag(")
body = r'''
int main() {
    const std::vector<OwedKeyItem> debt{{4114, 1, 1}, {4001, 1, 2}};
    assert(ValidateOwedKeyItems(EncodeOwedKeyItems(debt)) == debt);
    assert(ValidateOwedKeyItems("4114 1 1\r\n4001 1 2\r\n") == debt);
    assert(ValidateOwedKeyItems("") == std::vector<OwedKeyItem>{});
    assert(!ValidateOwedKeyItems("4114 1 1\n4001 1"));
    assert(!ValidateOwedKeyItems("4114 1 1\n4114 1 2\n"));
    assert(!ValidateOwedKeyItems("4114 1 1"));
    assert(!ValidateOwedKeyItems("268435456 1 1\n"));

    PhantomKeyItemLedger guest;
    assert(guest.LookAtPhantom(0x2000, {}).empty());
    guest.ObserveKnownPhantom(0x2100, {{4114, 1}});
    assert(guest.Owed().empty());
    guest.ObserveKnownPhantom(0x2000, {{4114, 1}});
    assert((guest.Owed() == std::vector<OwedKeyItem>{{4114, 1, 1}}));
    assert(!guest.LookAtOwn(0x2000, {{4114, 1}}));
    assert(!guest.AcknowledgeObservedReturn());
    assert((guest.LookAtOwn(0x3000, {}) == std::vector<HeldGoods>{{4114, 1}}));
    assert(!guest.AcknowledgeObservedReturn());
    assert(guest.LookAtOwn(0x3000, {{4114, 1}}) == std::vector<HeldGoods>{});
    int attempts = 0;
    assert(!guest.AcknowledgeObservedReturn([&] { ++attempts; return false; }));
    assert(attempts == 1);
    assert((guest.Owed() == std::vector<OwedKeyItem>{{4114, 1, 1}}));
    assert(guest.AcknowledgeObservedReturn([&] { ++attempts; return true; }));
    assert(attempts == 2 && guest.Owed().empty());
}
'''
preamble = """#include <algorithm>
#include <array>
#include <cassert>
#include <charconv>
#include <cstdint>
#include <functional>
#include <optional>
#include <span>
#include <string>
#include <utility>
#include <vector>
using u32 = std::uint32_t;
using u64 = std::uint64_t;
using s32 = std::int32_t;
"""
Path(sys.argv[1]).write_text(preamble + bell + types + count + ledger + body, encoding="utf-8")
