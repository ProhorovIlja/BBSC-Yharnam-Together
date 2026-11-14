// SPDX-License-Identifier: GPL-2.0-or-later
// Experimental policy only: no game hooks, password handling, or network I/O.
#include <cstdint>

namespace ultimate::bells {
using U = std::uint32_t;
enum class Action { Host, Join, Invade, Duel };
enum class Scope { Local, Worldwide };
enum class Result { Eligible, Incompatible, Closed, Full, Region, Pool, Level, UnsafeArrival };

struct Network {
    Scope scope;
    U region;        // Server-side region classification; zero is unknown, not a wildcard.
    U private_pool;  // Test stand-in for a server-owned opaque bucket; never the password.
};
struct Search {
    Action action;
    Network network;
    U level;
    bool compatible;
};
struct Room {
    Network network;
    U host_level;
    U occupied;      // Includes the host and all held seats, friendly or hostile.
    bool open;
    bool allows_invasions;
    bool safe_arrival;
};
constexpr bool RegionMatches(Network a, Network b) {
    return (a.scope == Scope::Worldwide && b.scope == Scope::Worldwide) ||
           (a.region != 0 && a.region == b.region);
}
constexpr bool InBand(U a, U b, U base, U divisor) {
    return a != 0 && b != 0 && (a > b ? a - b : b - a) <= base + b / divisor;
}
constexpr Result Match(Search q, Room r) {
    if (!q.compatible || (q.action != Action::Join && q.action != Action::Invade))
        return Result::Incompatible;
    if (!r.open || (q.action == Action::Invade && !r.allows_invasions)) return Result::Closed;
    if (r.occupied == 0 || r.occupied >= 5) return Result::Full;
    if (!RegionMatches(q.network, r.network)) return Result::Region;
    if (q.network.private_pool != r.network.private_pool ||
        (q.action == Action::Invade && q.network.private_pool != 0)) return Result::Pool;
    // Experimental starting values only. Unknown levels never enter public matching.
    if (q.network.private_pool == 0 &&
        !(q.action == Action::Join ? InBand(q.level, r.host_level, 10, 10)
                                   : InBand(q.level, r.host_level, 20, 5))) return Result::Level;
    // Discovery has no map filter. Admission waits for a safe destination/transition.
    return r.safe_arrival ? Result::Eligible : Result::UnsafeArrival;
}
constexpr bool DuelMayStart(U accepted_a, U accepted_b, U defenders, bool host_approved,
                            bool safe_arena, bool hostile_present_or_reserved) {
    return host_approved && safe_arena && !hostile_present_or_reserved && defenders <= 5 &&
           accepted_a >= 1 && accepted_a <= 2 && accepted_a == accepted_b &&
           accepted_a + accepted_b <= defenders;
}

constexpr Network world{Scope::Worldwide, 1, 0};
constexpr Network remote{Scope::Worldwide, 2, 0};
constexpr Network local{Scope::Local, 2, 0};
constexpr Network priv{Scope::Worldwide, 2, 7};
constexpr Room open{world, 50, 3, true, true, true};
constexpr Room closed{world, 50, 3, false, true, true};
constexpr Room full{world, 50, 5, true, true, true};
constexpr Room private_room{priv, 50, 3, true, true, true};
constexpr Room loading{world, 50, 3, true, true, false};
static_assert(Match({Action::Join, remote, 65, true}, open) == Result::Eligible);
static_assert(Match({Action::Join, remote, 66, true}, open) == Result::Level);
static_assert(Match({Action::Join, remote, 0, true}, open) == Result::Level);
static_assert(Match({Action::Join, remote, 50, true}, closed) == Result::Closed);
static_assert(Match({Action::Join, remote, 50, true}, full) == Result::Full);
static_assert(Match({Action::Join, local, 50, true}, open) == Result::Region);
static_assert(!RegionMatches(world, local));
static_assert(!RegionMatches({Scope::Local, 0, 0}, {Scope::Local, 0, 0}));
static_assert(Match({Action::Join, remote, 50, true}, private_room) == Result::Pool);
static_assert(Match({Action::Join, priv, 544, true}, private_room) == Result::Eligible);
static_assert(Match({Action::Join, {Scope::Worldwide, 2, 9}, 50, true}, private_room) == Result::Pool);
static_assert(Match({Action::Invade, priv, 50, true}, private_room) == Result::Pool);
static_assert(Match({Action::Invade, remote, 80, true}, open) == Result::Eligible);
static_assert(Match({Action::Invade, remote, 81, true}, open) == Result::Level);
static_assert(Match({Action::Invade, remote, 50, true}, {world, 50, 3, true, false, true}) == Result::Closed);
static_assert(Match({Action::Join, remote, 50, true}, loading) == Result::UnsafeArrival);
static_assert(Match({Action::Join, remote, 50, false}, open) == Result::Incompatible);
static_assert(DuelMayStart(1, 1, 2, true, true, false));
static_assert(DuelMayStart(2, 2, 5, true, true, false));
static_assert(!DuelMayStart(2, 2, 3, true, true, false));
static_assert(!DuelMayStart(1, 2, 5, true, true, false));
static_assert(!DuelMayStart(1, 1, 2, false, true, false));
static_assert(!DuelMayStart(1, 1, 2, true, false, false));
static_assert(!DuelMayStart(1, 1, 2, true, true, true));
} // namespace ultimate::bells
