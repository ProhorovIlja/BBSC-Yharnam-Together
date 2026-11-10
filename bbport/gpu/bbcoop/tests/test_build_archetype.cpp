// SPDX-License-Identifier: GPL-2.0-or-later
#include <cassert>
#include <cstdint>
#include <iostream>
#include <set>
#include <string>
#include "bbcoop/build_archetype.h"
using namespace BbHunterBuild;
int main() {
    static_assert(Threshold == 18);
    static_assert(Mask({17, 17, 17, 17}).value() == 0);
    static_assert(Mask({18, 17, 17, 17}).value() == Strength);
    static_assert(Mask({30, 25, 8, 7}).value() == (Strength | Skill));
    static_assert(Mask({12, 17, 36, 8}).value() == Bloodtinge);
    static_assert(Mask({25, 25, 20, 21}).value() == 15);
    static_assert(Mask({17, 17, 17, 18}).value() == Arcane);
    static_assert(!Mask({0, 19, 19, 19}).has_value());
    static_assert(!Mask({1, 1, 100, 19}).has_value());
    static_assert(English(Strength | Skill) == "Quality");
    static_assert(English(15) == "Omnibuild");
    static_assert(English(16) == "Unknown");
    static_assert(Russian(15) == "Универсал");
    std::set<std::string> en, ru;
    // All 16 combinations must be uniquely labelled, no duplicate
    // hybids or collisions due to ordering/thresholding.
    for (std::uint8_t mask = 0; mask < 16; ++mask) {
        const Attributes a{
            (mask & Strength) ? 18 : 17,
            (mask & Skill) ? 18 : 17,
            (mask & Bloodtinge) ? 18 : 17,
            (mask & Arcane) ? 18 : 17
        };
        assert(Mask(a).has_value() && Mask(a).value() == mask);
        assert(en.insert(std::string(English(mask))).second);
        assert(ru.insert(std::string(Russian(mask))).second);
    }
    std::cout << "B45_16_BUILD_ARCHETYPES_THRESHOLD_18_PASS\n";
}
