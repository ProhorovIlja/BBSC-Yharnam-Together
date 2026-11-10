// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// B45: deterministic, presentation-only Bloodborne hunter build labels.
// The four offensive stats are Strength/Skill/Bloodtinge/Arcane; threshold 18
// inclusive. Never fabricate a build from level, weapon, guessed network data
// or the server's private anti-cheat CharacterSheet.
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string_view>

namespace BbHunterBuild {
inline constexpr int Threshold = 18;
inline constexpr int MaxAttribute = 99;
enum Stat : std::uint8_t {
    Strength = 1u << 0,
    Skill = 1u << 1,
    Bloodtinge = 1u << 2,
    Arcane = 1u << 3
};

struct Attributes {
    int strength = 0;
    int skill = 0;
    int bloodtinge = 0;
    int arcane = 0;
};

[[nodiscard]] constexpr std::optional<std::uint8_t> Mask(Attributes v) {
    const std::array<int, 4> stats{v.strength, v.skill, v.bloodtinge, v.arcane};
    std::uint8_t mask = 0;
    for (std::size_t i = 0; i < stats.size(); ++i) {
        if (stats[i] < 1 || stats[i] > MaxAttribute) return std::nullopt;
        if (stats[i] >= Threshold) mask |= static_cast<std::uint8_t>(1u << i);
    }
    return mask;
}
[[nodiscard]] constexpr std::string_view English(std::uint8_t mask) {
    constexpr std::array<std::string_view, 16> names{
        "Unfocused",       // 0000
        "Strength",        // 0001
        "Skill",           // 0010
        "Quality",         // 0011 STR + SKL
        "Bloodtinge",      // 0100
        "Strength/Blood",  // 0101
        "Skill/Blood",     // 0110
        "Quality/Blood",   // 0111
        "Arcane",          // 1000
        "Strength/Arcane", // 1001
        "Skill/Arcane",    // 1010
        "Quality/Arcane",  // 1011
        "Blood/Arcane",    // 1100
        "Strength/Blood/Arcane", // 1101
        "Skill/Blood/Arcane",    // 1110
        "Omnibuild"        // 1111
    };
    return mask < names.size() ? names[mask] : "Unknown";
}
// B58: concise *Discord-only* presentation. Keep English/Russian as-is for
// in-game HUD and accessibility; a common authoritative Mask decides both.
// Bloodborne abbreviations: QLT = STR+SKL (Quality), OMNI = all four.
// 0 = no offensive stat at or above the inclusive 18 threshold.
[[nodiscard]] constexpr std::string_view DiscordShort(std::uint8_t mask) {
    constexpr std::array<std::string_view, 16> names{
        "UNF",              // 0000: no 18+ offense
        "STR",              // 0001
        "SKL",              // 0010
        "QLT",              // 0011 STR+SKL
        "BLT",              // 0100
        "STR/BLT",          // 0101
        "SKL/BLT",          // 0110
        "QLT/BLT",          // 0111
        "ARC",              // 1000
        "STR/ARC",          // 1001
        "SKL/ARC",          // 1010
        "QLT/ARC",          // 1011
        "BLT/ARC",          // 1100
        "STR/BLT/ARC",      // 1101
        "SKL/BLT/ARC",      // 1110
        "OMNI"              // 1111
    };
    return mask < names.size() ? names[mask] : "Unknown";
}
[[nodiscard]] constexpr std::string_view Russian(std::uint8_t mask) {
    constexpr std::array<std::string_view, 16> names{
        "Без специализации", "Сила", "Ловкость", "Качество",
        "Кровавый оттенок", "Сила/Кровь", "Ловкость/Кровь", "Качество/Кровь",
        "Тайна", "Сила/Тайна", "Ловкость/Тайна", "Качество/Тайна",
        "Кровь/Тайна", "Сила/Кровь/Тайна", "Ловкость/Кровь/Тайна", "Универсал"
    };
    return mask < names.size() ? names[mask] : "Неизвестно";
}
} // namespace BbHunterBuild
