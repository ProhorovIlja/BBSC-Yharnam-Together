// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <cstddef>
#include <cstdint>

namespace Core::Bloodborne::UltimatePvP {

// Server-verified faction, not the visual phantom color. A future routed
// packet/view must carry stable member IDs and the current invasion instance.
enum class Side { None, Defender, Invader };
enum class Life { Alive, Downed, Dead, Disconnected };

struct Member {
    std::uint64_t id = 0;
    std::uint64_t invasion_id = 0;
    Side side = Side::None;
    Life life = Life::Disconnected;
};

inline bool MaySeePrivateHud(const Member& observer, const Member& target) {
    return observer.id != 0 && target.id != 0 &&
           observer.invasion_id != 0 && observer.invasion_id == target.invasion_id &&
           observer.side != Side::None && observer.side == target.side &&
           observer.life != Life::Disconnected && target.life != Life::Disconnected;
}

inline bool MayReviveByHit(const Member& attacker, const Member& target,
                           bool dbno, bool server_verified_hit) {
    return dbno && server_verified_hit && MaySeePrivateHud(attacker, target) &&
           attacker.id != target.id && attacker.side == Side::Invader &&
           attacker.life == Life::Alive && target.life == Life::Downed;
}

enum class DeathOutcome {
    Ignore,          // no active invasion / invalid member
    DisconnectOne,   // DBNO off: remove just the fallen invader
    KeepDowned,      // DBNO on: a teammate remains up and can revive by hit
    DisconnectAll,   // DBNO on: no invader left standing
};

// Snapshot counts must come from the authoritative server for the SAME
// invasion id, after applying this death atomically. A dead/disconnected
// member cannot be counted as alive just because its actor remains rendered.
inline DeathOutcome AfterLethalInvaderHit(
    bool dbno, std::size_t active_invaders, std::size_t standing_after_hit) {
    if (active_invaders == 0 || standing_after_hit > active_invaders) {
        return DeathOutcome::Ignore;
    }
    if (!dbno) {
        return DeathOutcome::DisconnectOne;
    }
    return standing_after_hit == 0 ? DeathOutcome::DisconnectAll
                                   : DeathOutcome::KeepDowned;
}

struct InvasionPermission {
    bool global_enabled = false;
    bool host_allowed = false;
    bool requester_is_leader = false;
    bool active_boss = false;
    bool world_loading = false;
    std::size_t existing_members = 0;
    std::size_t max_members = 5;
};

inline bool CanAdmitInvader(const InvasionPermission& p) {
    return p.global_enabled && p.host_allowed && !p.active_boss &&
           !p.world_loading && p.max_members != 0 &&
           p.existing_members < p.max_members;
}
inline bool MayChangeHostRule(const InvasionPermission& p) {
    return p.requester_is_leader;
}

} // namespace Core::Bloodborne::UltimatePvP
