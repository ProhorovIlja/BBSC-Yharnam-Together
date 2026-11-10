// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <algorithm>
#include <array>
#include <string_view>

namespace Core::Bloodborne {
// Official Yharnam Together #546 (merged, 2026-11-10): these nine retail
// Bloodborne TITLE_IDs share the known 1.09 executable. Do not gate by the
// European GOTY edition alone; the image/site checks are still mandatory.
inline constexpr std::array<std::string_view, 9> RetailTitles{
    "CUSA03173", "CUSA00207", "CUSA00208", "CUSA00900", "CUSA03179",
    "CUSA01363", "CUSA03023", "CUSA00299", "CUSA03014",
};
constexpr bool IsBloodborneTitle(std::string_view title) {
    return std::ranges::find(RetailTitles, title) != RetailTitles.end();
}
inline constexpr std::string_view CoopAppVersion = "01.09";
enum class CoopGame {
    Yes,
    OtherVersion,  // param.sfo is stale; final hook-site code check still required
    OtherGame,
};
constexpr CoopGame SeamlessCoopGameFor(std::string_view title, std::string_view app_version) {
    if (!IsBloodborneTitle(title)) {
        return CoopGame::OtherGame;
    }
    return app_version == CoopAppVersion ? CoopGame::Yes : CoopGame::OtherVersion;
}
constexpr bool GetsSeamlessCoop(CoopGame game) {
    return game != CoopGame::OtherGame;
}
} // namespace Core::Bloodborne
