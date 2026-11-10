// SPDX-License-Identifier: GPL-2.0-or-later
#include <cassert>
#include <iostream>
#include "core/bloodborne_titles.h"
using namespace Core::Bloodborne;
int main() {
    static_assert(RetailTitles.size() == 9);
    static_assert(IsBloodborneTitle("CUSA03173"));
    static_assert(IsBloodborneTitle("CUSA00900"));
    static_assert(IsBloodborneTitle("CUSA03023"));
    static_assert(!IsBloodborneTitle("CUSA0317"));
    static_assert(!IsBloodborneTitle("cusa03173"));
    static_assert(!IsBloodborneTitle("CUSA00001"));
    static_assert(SeamlessCoopGameFor("CUSA00900", "01.09") == CoopGame::Yes);
    static_assert(SeamlessCoopGameFor("CUSA03173", "01.00") == CoopGame::OtherVersion);
    static_assert(SeamlessCoopGameFor("", "01.09") == CoopGame::OtherGame);
    static_assert(GetsSeamlessCoop(CoopGame::Yes));
    static_assert(GetsSeamlessCoop(CoopGame::OtherVersion));
    static_assert(!GetsSeamlessCoop(CoopGame::OtherGame));
    for (const auto title : RetailTitles) {
        assert(IsBloodborneTitle(title));
        assert(SeamlessCoopGameFor(title, "01.09") == CoopGame::Yes);
    }
    std::cout<<"B49_ALL_9_CUSA_EXACT_109_SEAMLESS_GATE_PASS\n";
}
