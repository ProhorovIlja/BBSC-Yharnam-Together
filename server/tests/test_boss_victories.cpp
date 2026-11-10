// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
#include <cassert>
#include <cstdint>
#include <iostream>
#include "coop/boss_victories.h"

using namespace BloodborneCoop;

int main() {
    static_assert(BossVictoryFlags.size() == 16);
    static_assert(IsBossVictoryFlag(0x18010000u, 12411800u));
    static_assert(IsBossVictoryFlag(0x18000000u, 12401800u));
    static_assert(IsBossVictoryFlag(0x18020000u, 12421700u));
    static_assert(IsBossVictoryFlag(0x18020000u, 12421800u));
    static_assert(!IsBossVictoryFlag(0x18010000u, 12401800u)); // cross-area mismatch
    static_assert(!IsBossVictoryFlag(0x18010000u, 12414700u)); // boss fog entry, NOT defeat
    static_assert(!IsBossVictoryFlag(0x18010000u, 12414000u)); // boss in progress, NOT defeat
    static_assert(!BossMapFlagIndex(0x18010000u, 10000)); // one map's bit limit
    static_assert(BossMapFlagIndex(0x18010000u, 1800));
    static_assert(!BossMapFlagIndex(0x18010000u, 4700));
    for (const BossVictoryFlag& row : BossVictoryFlags) {
        assert(IsBossVictoryFlag(row.map, row.flag));
        assert(row.flag >= BossMapFlagBase(row.map));
        assert(row.flag - BossMapFlagBase(row.map) < 10000u);
    }
    std::cout << "B44_16_AUDITED_BOSS_VICTORY_FLAG_CATALOG_PASS\n";
    return 0;
}
