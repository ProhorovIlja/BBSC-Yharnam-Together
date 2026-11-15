// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <compare>
#include <cstdint>
#include <set>
#include <span>
#include <vector>

namespace Core::Bloodborne::Progression {

// Candidate policy only: inputs must come from verified game-event adapters,
// not the host snapshot, incoming flags, or arbitrary network messages.
enum class Mode { Off, EarnedOnly };
enum class Kind { Area, Lamp, Boss, UniquePickup, QuestMilestone };

struct Scope {
    std::uint64_t hunter, journey, session;
    auto operator<=>(const Scope&) const = default;
};
struct Key {
    Kind kind;
    std::uint64_t context; // map, dungeon instance or quest context
    std::uint64_t id;      // stable typed event / reward identity, not stack count
    auto operator<=>(const Key&) const = default;
};
struct Event {
    Scope scope;
    Key key;
    bool locally_earned;
    bool verified;
    bool additive;
    bool compatible;
};

// Does not mutate inventory, a world snapshot, or a save. A proposal is
// neither an award nor proof of persistence. Adapters must revalidate on apply.
inline std::vector<Key> Plan(Mode mode, Scope scope, std::span<const Event> events,
                             const std::set<Key>& already_owned) {
    std::vector<Key> additions;
    if (mode != Mode::EarnedOnly || !scope.hunter || !scope.journey || !scope.session)
        return additions;
    auto seen = already_owned;
    for (const auto& e : events) {
        if (e.scope == scope && e.key.id && e.locally_earned && e.verified &&
            e.additive && e.compatible && seen.insert(e.key).second)
            additions.push_back(e.key);
    }
    return additions;
}

} // namespace Core::Bloodborne::Progression
