// SPDX-License-Identifier: GPL-2.0-or-later
// Standalone acceptance fixture. Does not change the production matcher.
#include <cstdint>
#include <initializer_list>

namespace ultimate {
constexpr unsigned SessionLimit = 5;
constexpr unsigned InvaderLimit = 2;

// defenders includes the host and all co-op seats already claimed or reserved.
// hostile includes both active invaders and outstanding reservations.
struct RoomCapacity {
    unsigned defenders;
    unsigned hostile;
    unsigned host_limit; // 0, 1 or 2
    bool operator_enabled;
    bool room_open;
    bool gameplay_eligible;
    bool paired_protocol; // negotiated across participants, not a user setting
};

[[nodiscard]] constexpr bool FitsInvasion(RoomCapacity r, unsigned group) {
    if (!r.operator_enabled || !r.room_open || !r.gameplay_eligible ||
        r.defenders == 0 || r.defenders > SessionLimit ||
        r.host_limit > InvaderLimit || group == 0 || group > InvaderLimit) {
        return false;
    }
    const unsigned limit = r.paired_protocol ? r.host_limit : (r.host_limit == 0 ? 0 : 1);
    return r.hostile <= limit && group <= limit - r.hostile &&
           r.hostile <= SessionLimit - r.defenders &&
           group <= SessionLimit - r.defenders - r.hostile;
}

static_assert(FitsInvasion({3, 0, 2, true, true, true, true}, 2));
static_assert(!FitsInvasion({4, 0, 2, true, true, true, true}, 2));
static_assert(FitsInvasion({4, 0, 2, true, true, true, true}, 1));
static_assert(!FitsInvasion({5, 0, 2, true, true, true, true}, 1));
static_assert(!FitsInvasion({3, 1, 2, true, true, true, true}, 2));
static_assert(FitsInvasion({3, 1, 2, true, true, true, true}, 1));
static_assert(!FitsInvasion({3, 2, 2, true, true, true, true}, 1));
static_assert(!FitsInvasion({3, 0, 2, true, false, true, true}, 1));
static_assert(!FitsInvasion({3, 0, 2, false, true, true, true}, 1));
static_assert(!FitsInvasion({3, 0, 0, true, true, true, true}, 1));
static_assert(!FitsInvasion({3, 0, 2, true, true, false, true}, 1));
static_assert(!FitsInvasion({3, 0, 2, true, true, true, false}, 2));
static_assert(FitsInvasion({3, 0, 2, true, true, true, false}, 1));
static_assert(!FitsInvasion({0, 0, 2, true, true, true, true}, 1));
static_assert(!FitsInvasion({3, 0, 3, true, true, true, true}, 1));
static_assert(!FitsInvasion({3, 0, 2, true, true, true, true}, 0));
static_assert(!FitsInvasion({3, UINT32_MAX, 2, true, true, true, true}, 1));

constexpr bool ExhaustiveSmallDomain() {
    for (unsigned defenders = 1; defenders <= 5; ++defenders) {
        for (unsigned occupied = 0; occupied <= 6; ++occupied) {
            for (unsigned limit = 0; limit <= 2; ++limit) {
                for (unsigned group = 1; group <= 2; ++group) {
                    for (const bool paired : {false, true}) {
                        const auto allowed = FitsInvasion({defenders, occupied, limit, true, true, true, paired}, group);
                        if (allowed != (defenders + occupied + group <= 5 && occupied + group <= limit &&
                                        (paired || occupied + group <= 1))) {
                            return false;
                        }
                    }
                }
            }
        }
    }
    return true;
}
static_assert(ExhaustiveSmallDomain());
} // namespace ultimate
