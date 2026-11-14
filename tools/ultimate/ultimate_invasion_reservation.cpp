// SPDX-License-Identifier: GPL-2.0-or-later
// Isolated server-side experiment. Call under one room's serialized executor;
// publish the returned complete roster in that same transaction. No wire changes.
#include "ultimate_invasion_capacity.cpp"
#include <array>
#include <cassert>
#include <optional>

namespace ultimate {
struct Claimant {
    std::uint64_t account = 0, connection = 0;
    constexpr bool valid() const { return account != 0 && connection != 0; }
    constexpr bool operator==(const Claimant&) const = default;
};
struct Claim {
    std::uint64_t token = 0, epoch = 0, expires = 0;
    std::array<Claimant, 2> roster{};
    unsigned size = 0;
    unsigned ready = 0;
};

// Monotonic times share one clock. Callers supply the room epoch, current
// occupancy excluding this pending claim, and live admission eligibility.
// At most one pending batch per room; no dynamic allocation or polling loop.
class PendingInvasion {
    std::optional<Claim> pending;
    std::uint64_t highest_token = 0;
    static constexpr std::uint64_t MaxHoldMs = 30000;

    bool current(std::uint64_t epoch, std::uint64_t now, RoomCapacity room) {
        if (pending && (pending->epoch != epoch || now >= pending->expires ||
                        !FitsInvasion(room, pending->size))) {
            pending.reset();
        }
        return pending.has_value();
    }

public:
    [[nodiscard]] bool reserve(std::uint64_t token, std::uint64_t epoch, std::uint64_t now,
                               std::uint64_t expires, RoomCapacity room, Claimant first,
                               std::optional<Claimant> second = std::nullopt) {
        if (current(epoch, now, room) || epoch == 0 || token <= highest_token ||
            expires <= now || expires - now > MaxHoldMs || !first.valid() ||
            (second && (!second->valid() || first.account == second->account)) ||
            !FitsInvasion(room, second ? 2U : 1U)) {
            return false;
        }
        highest_token = token;
        pending = Claim{token, epoch, expires, {first, second.value_or(Claimant{})},
                        second ? 2U : 1U, 0};
        return true;
    }

    [[nodiscard]] bool stage(std::uint64_t token, std::uint64_t epoch, std::uint64_t now,
                             RoomCapacity room, Claimant who) {
        if (!current(epoch, now, room) || pending->token != token) return false;
        for (unsigned i = 0; i < pending->size; ++i) {
            if (pending->roster[i] == who) {
                pending->ready |= 1U << i;
                return true;
            }
        }
        return false;
    }

    [[nodiscard]] std::optional<Claim> commit(std::uint64_t token, std::uint64_t epoch,
                                               std::uint64_t now, RoomCapacity room) {
        if (!current(epoch, now, room) || pending->token != token ||
            pending->ready != (1U << pending->size) - 1U) return std::nullopt;
        const auto result = pending;
        pending.reset();
        return result;
    }

    void disconnect(Claimant who) {
        if (!pending) return;
        for (unsigned i = 0; i < pending->size; ++i) {
            if (pending->roster[i] == who) {
                pending.reset();
                return;
            }
        }
    }

    [[nodiscard]] unsigned held(std::uint64_t epoch, std::uint64_t now, RoomCapacity room) {
        return current(epoch, now, room) ? pending->size : 0U;
    }
};
} // namespace ultimate

int main() {
    using namespace ultimate;
    constexpr RoomCapacity room{3, 0, 2, true, true, true, true};
    constexpr Claimant a{11, 101}, b{12, 102}, old_b{12, 99};
    PendingInvasion p;
    assert(!p.reserve(1, 1, 100, 200, room, a, Claimant{11, 102}));
    assert(!p.reserve(1, 1, 100, 30101, room, a, b));
    assert(p.reserve(1, 1, 100, 200, room, a, b));
    assert(p.held(1, 110, room) == 2);
    assert(!p.reserve(2, 1, 110, 200, room, b));
    assert(p.stage(1, 1, 120, room, a));
    assert(p.stage(1, 1, 121, room, a));
    assert(!p.stage(1, 1, 121, room, old_b));
    assert(!p.commit(1, 1, 121, room));
    assert(p.stage(1, 1, 122, room, b));
    auto committed = p.commit(1, 1, 123, room);
    assert(committed && committed->size == 2 && committed->roster[1] == b);
    assert(!p.commit(1, 1, 124, room));
    assert(!p.reserve(1, 1, 124, 200, room, a));
    assert(p.reserve(2, 1, 125, 200, room, a, b));
    p.disconnect(old_b);
    assert(p.held(1, 126, room) == 2);
    p.disconnect(b);
    assert(p.held(1, 126, room) == 0);
    assert(p.reserve(3, 1, 127, 200, room, a, b));
    assert(p.held(1, 200, room) == 0);
    assert(p.reserve(4, 1, 201, 300, room, a, b));
    assert(p.held(2, 202, room) == 0);
    auto changed = room;
    assert(p.reserve(5, 2, 203, 300, room, a, b));
    assert(p.stage(5, 2, 204, room, a) && p.stage(5, 2, 204, room, b));
    changed.defenders = 4;
    assert(!p.commit(5, 2, 205, changed));
    assert(p.held(2, 206, room) == 0);
    assert(p.reserve(6, 2, 207, 300, changed, a));
    changed.room_open = false;
    assert(!p.stage(6, 2, 208, changed, a));
    changed = room;
    changed.paired_protocol = false;
    assert(!p.reserve(7, 2, 209, 300, changed, a, b));
    assert(p.reserve(7, 2, 209, 300, changed, a));
    assert(p.stage(7, 2, 210, changed, a));
    assert(p.commit(7, 2, 210, changed)->size == 1);
}
