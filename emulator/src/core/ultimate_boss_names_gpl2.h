// SPDX-FileCopyrightText: Copyright 2026 erezeth (source boss-ID catalog)
// SPDX-License-Identifier: GPL-2.0-only
#pragma once

// Boss name-ID -> English label reference data adapted with attribution from
// https://github.com/erezeth/bloodborne-rpc/blob/main/source_code/main.cpp
// (GPL-2.0, observed 2026-11-10). Original author explicitly states that
// not every location/boss has been tested. This catalog contains actor/hunter
// labels too; appearing in the game's *active boss HP gauge*, not just a
// known ID, is required before exposing a name publicly in Discord.
// No game artwork, private memory, player saves or Discord credentials.
#include <array>
#include <cstdint>
#include <string_view>
#include <utility>

namespace Core::Bloodborne::BossPresence {

inline constexpr std::array<std::pair<std::int32_t, std::string_view>, 87> NamedBossIds{{
    {1000, "Madman's Escort"},
    {1010, "Forgotten Madman"},
    {6400, "Old Hunter Henryk"},
    {6500, "Valtr, Master of the League"},
    {6505, "Valtr, Beast Eater"},
    {6530, "Yamamura the Wanderer"},
    {6540, "Younger Madaras Twin"},
    {6550, "Mensis Scholar Damian"},
    {6600, "Henriett"},
    {6640, "Defector Antal"},
    {7040, "Tomb Prospector Olek"},
    {7045, "Tomb Prospector Gremia"},
    {7060, "Beastclaw Jozef"},
    {7160, "Queen Killer"},
    {7300, "Vitus"},
    {7310, "Madman Wallar"},
    {101000, "Degenerate Beast"},
    {106000, "Brainsucker"},
    {127000, "Maneater Boar"},
    {209000, "Blood-starved Beast"},
    {209010, "Blood-starved Beast"},
    {210000, "The Witch of Hemwick"},
    {212010, "Shadow of Yharnam"},
    {212020, "Shadow of Yharnam"},
    {212030, "Shadow of Yharnam"},
    {216000, "Keeper of the Old Lords"},
    {218000, "Loran Silverbeast"},
    {232000, "Martyr Logarius"},
    {251000, "Ebrietas, Daughter of the Cosmos"},
    {251010, "Ebrietas, Daughter of the Cosmos"},
    {257000, "Celestial Emissary"},
    {257010, "Celestial Emissary"},
    {271000, "Father Gascoigne"},
    {272000, "Father Gascoigne"},
    {304000, "Merciless Watcher"},
    {304001, "Watcher Chieftain"},
    {304002, "Merciless Watcher"},
    {304003, "Merciless Watcher"},
    {305000, "Pthumerian Descendant"},
    {305001, "Pthumerian Descendant"},
    {305002, "Pthumerian Elder"},
    {306000, "Pthumerian Bride"},
    {306001, "Yharnam, Pthumerian Queen"},
    {313000, "Undead Giant"},
    {403000, "Living Failures"},
    {450000, "Laurence, the First Vicar"},
    {451000, "Ludwig the Accursed"},
    {451005, "Ludwig, the Holy Blade"},
    {452000, "Lady Maria of the Astral Clocktower"},
    {453000, "Orphan of Kos"},
    {454000, "Orphan of Kos"},
    {500000, "Cleric Beast"},
    {501000, "Watchdog of the Old Lords"},
    {502000, "Vicar Amelia"},
    {504000, "Loran Darkbeast"},
    {504010, "Abhorrent Beast"},
    {507000, "The One Reborn"},
    {508000, "Darkbeast Paarl"},
    {508010, "Loran Darkbeast"},
    {509000, "Bloodletting Beast"},
    {509010, "Bloodletting Beast"},
    {510000, "Rom, the Vacuous Spider"},
    {510010, "Rom, the Vacuous Spider"},
    {511000, "Great One Beast"},
    {512000, "Amygdala"},
    {512010, "Amygdala"},
    {540000, "Moon Presence"},
    {551000, "Mergo's Wet Nurse"},
    {551010, "Mergo's Wet Nurse"},
    {750000, "Beast-possessed Soul"},
    {802000, "Slug Princess"},
    {803000, "Heroine Doll"},
    {804000, "Gehrman, the First Hunter"},
    {805000, "Gehrman, the First Hunter"},
    {899000, "Micolash, Host of the Nightmare"},
    {899010, "Vileblood Hunter Alfred"},
    {900020, "The Vileblood"},
    {900030, "The Executioners"},
    {900040, "Hunter of Hunters"},
    {901040, "Nameless Tomb Prospector"},
    {901060, "Izzy's Admirer"},
    {901070, "Nameless Madman"},
    {901110, "Bone Ash Hunter Carla"},
    {901150, "Drifting Vileblood Leo"},
    {901160, "Ardeo Man"},
    {901170, "Defeated Hunter"},
    {901180, "Choir Intelligencer Edgar"},
}};

[[nodiscard]] constexpr std::string_view BossNameForId(std::int32_t id) {
    for (const auto& [candidate, name] : NamedBossIds) {
        if (candidate == id) return name;
    }
    return {};
}

} // namespace Core::Bloodborne::BossPresence
