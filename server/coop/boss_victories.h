// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Known permanent boss-defeat progression flags from bloodborne_map.cpp::AreaBossFlags.
// Not fog entry flags, not generic enemy kills. This is intentionally a bounded
// audited subset: DLC/chalice will need separately verified flags and test fixtures.
#include <array>
#include <cstdint>

namespace BloodborneCoop {
struct BossVictoryFlag {
    std::uint32_t map;
    std::uint32_t flag;
};
inline constexpr std::array<BossVictoryFlag, 16> BossVictoryFlags{{
    {0x16000000u, 12201800u}, {0x17000000u, 12301800u},
    {0x18000000u, 12401800u}, {0x18010000u, 12411800u},
    {0x18020000u, 12421700u}, {0x18020000u, 12421800u},
    {0x19000000u, 12501800u}, {0x1a000000u, 12601800u},
    {0x1b000000u, 12701800u}, {0x1c000000u, 12801800u},
    {0x20000000u, 13201800u}, {0x21000000u, 13301800u},
    {0x22000000u, 13401800u}, {0x23000000u, 13501800u},
    {0x23000000u, 13501850u}, {0x24000000u, 13601800u},
}};
[[nodiscard]] constexpr bool IsBossVictoryFlag(std::uint32_t map, std::uint32_t flag) {
    for (const auto& entry : BossVictoryFlags) {
        if (entry.map == (map & 0xffff0000u) && entry.flag == flag) return true;
    }
    return false;
}
[[nodiscard]] constexpr std::uint32_t BossMapFlagBase(std::uint32_t map) {
    return (1000u + ((map >> 24) & 0xffu) * 10u + ((map >> 16) & 0xffu)) * 10000u;
}
[[nodiscard]] constexpr bool BossMapFlagIndex(std::uint32_t map, std::uint32_t index) {
    return index < 10000u && IsBossVictoryFlag(map, BossMapFlagBase(map) + index);
}
} // namespace BloodborneCoop
