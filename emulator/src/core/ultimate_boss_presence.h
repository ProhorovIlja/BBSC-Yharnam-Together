// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// Bloodborne 1.09 boss gauge slot decoder and independent encounter clock.
// Sources: our existing bloodborne_party.h BossGauges* constants and the
// attributed GPLv2 boss-ID catalog in ultimate_boss_names_gpl2.h. This is a
// read-only decoder: it never obtains addresses or modifies game memory.
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <optional>
#include <span>
#include <string_view>

#include "core/ultimate_boss_names_gpl2.h"

namespace Core::Bloodborne::BossPresence {

inline constexpr std::size_t GaugeSlots = 3;
inline constexpr std::size_t GaugeSize = 0x14;
inline constexpr std::size_t GaugeBytes = GaugeSlots * GaugeSize;

// A slot contains [name_id:i32][boss handle:i32][...][shown:u8 at +0x10].
// Unknown IDs, unshown HP bars and mixed distinct bosses fail closed. Two or
// three slots for a single named boss (e.g. Shadows) are one encounter.
[[nodiscard]] inline std::optional<std::string_view> NameFromActiveGauges(
    std::span<const std::uint8_t> bytes) {
    if (bytes.size() != GaugeBytes) return std::nullopt;
    std::optional<std::string_view> label;
    for (std::size_t i = 0; i < GaugeSlots; ++i) {
        const std::uint8_t* slot = bytes.data() + i * GaugeSize;
        std::int32_t handle = -1;
        std::memcpy(&handle, slot + 4, sizeof(handle));
        if (handle == -1) continue;
        // The gauge has a boss handle, but the game has not exposed this
        // nameplate yet. Never guess an encounter name.
        if (slot[0x10] == 0) return std::nullopt;
        std::int32_t id = -1;
        std::memcpy(&id, slot, sizeof(id));
        const std::string_view candidate = BossNameForId(id);
        if (candidate.empty() || (label && *label != candidate)) {
            return std::nullopt;
        }
        label = candidate;
    }
    return label;
}

// One timestamp per observed map/encounter, not a fresh timestamp every
// 2-second Discord IPC poll. The game tick calls Observe; Discord reads only
// the already cached number. Map change, missing map or no fight reset it.
// Phase/name changes do not reset the clock (e.g. Ludwig's transformation).
class EncounterClock {
public:
    void Observe(bool boss_fighting, std::uint32_t map, std::int64_t unix_seconds) {
        if (!boss_fighting || map == 0 || unix_seconds <= 0) {
            Reset();
            return;
        }
        if (!active_ || current_map_ != map) {
            start_ = unix_seconds;
            current_map_ = map;
            active_ = true;
        }
    }

    [[nodiscard]] std::int64_t StartedUnix() const { return active_ ? start_ : 0; }
    void Reset() {
        active_ = false;
        current_map_ = 0;
        start_ = 0;
    }

private:
    bool active_ = false;
    std::uint32_t current_map_ = 0;
    std::int64_t start_ = 0;
};

} // namespace Core::Bloodborne::BossPresence
