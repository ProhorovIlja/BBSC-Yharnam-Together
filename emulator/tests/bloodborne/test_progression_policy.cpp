// SPDX-License-Identifier: GPL-2.0-or-later
#include "../../src/core/bloodborne_progression_policy.h"

using namespace Core::Bloodborne::Progression;

int main() {
    constexpr Scope me{1, 1, 7};
    constexpr Key lamp{Kind::Lamp, 24, 1}, boss{Kind::Boss, 24, 1},
        loot{Kind::UniquePickup, 24, 1}, quest{Kind::QuestMilestone, 24, 1},
        area{Kind::Area, 24, 1}, dungeon_lamp{Kind::Lamp, 56, 1};
    const std::set<Key> owned{lamp};
    const Event events[]{
        {me, lamp, true, true, true, true},
        {me, boss, true, true, true, true},
        {me, boss, true, true, true, true}, // replay
        {me, loot, false, true, true, true}, // host's inventory
        {me, quest, true, true, true, false}, // conflicting branch
        {me, area, true, false, true, true}, // unverified
        {me, quest, true, true, false, true}, // destructive
        {{2, 1, 7}, loot, true, true, true, true}, // other hunter
        {{1, 2, 7}, loot, true, true, true, true}, // other NG cycle
        {{1, 1, 8}, loot, true, true, true, true}, // other session
        {me, dungeon_lamp, true, true, true, true},
    };
    if (!Plan(Mode::Off, me, events, owned).empty()) return 1;
    if (!Plan(Mode::EarnedOnly, {1, 1, 0}, events, owned).empty()) return 2;
    if (Plan(Mode::EarnedOnly, me, events, owned) != std::vector<Key>{boss, dungeon_lamp})
        return 3;
    if (owned != std::set<Key>{lamp}) return 4;
}
