// SPDX-License-Identifier: GPL-2.0-or-later
#include "core/ultimate_pvp_faction_rules.h"

#include <cassert>
#include <cstdio>

using namespace Core::Bloodborne::UltimatePvP;
int main() {
    const Member defender{10, 80, Side::Defender, Life::Alive};
    const Member defender_down{11, 80, Side::Defender, Life::Downed};
    const Member defender_dead{12, 80, Side::Defender, Life::Dead};
    const Member invader{21, 80, Side::Invader, Life::Alive};
    const Member invader_down{22, 80, Side::Invader, Life::Downed};
    const Member invader_other{23, 81, Side::Invader, Life::Alive};
    const Member disconnected{24, 80, Side::Invader, Life::Disconnected};
    assert(MaySeePrivateHud(defender, defender_down));
    assert(MaySeePrivateHud(defender, defender_dead)); // 0 HP until disconnected
    assert(MaySeePrivateHud(invader, invader_down));
    assert(MaySeePrivateHud(invader, invader));
    assert(!MaySeePrivateHud(defender, invader));
    assert(!MaySeePrivateHud(invader, defender_down));
    assert(!MaySeePrivateHud(invader, invader_other));
    assert(!MaySeePrivateHud(invader, disconnected));
    assert(!MaySeePrivateHud(Member{}, invader));
    assert(!MaySeePrivateHud(invader, Member{}));

    // Revive by *attacker's* validated hit on a same-side downed invader,
    // not defender/anonymous hit, nor a downed attacker or a normal kill.
    assert(MayReviveByHit(invader, invader_down, true, true));
    assert(!MayReviveByHit(invader, invader_down, false, true));
    assert(!MayReviveByHit(invader, invader_down, true, false));
    assert(!MayReviveByHit(defender, invader_down, true, true));
    assert(!MayReviveByHit(invader, defender_down, true, true));
    assert(!MayReviveByHit(invader_down, invader, true, true));
    assert(!MayReviveByHit(invader_down, invader_down, true, true));

    assert(AfterLethalInvaderHit(false, 1, 0) == DeathOutcome::DisconnectOne);
    assert(AfterLethalInvaderHit(false, 3, 2) == DeathOutcome::DisconnectOne);
    assert(AfterLethalInvaderHit(true, 3, 2) == DeathOutcome::KeepDowned);
    assert(AfterLethalInvaderHit(true, 3, 0) == DeathOutcome::DisconnectAll);
    assert(AfterLethalInvaderHit(true, 1, 0) == DeathOutcome::DisconnectAll);
    assert(AfterLethalInvaderHit(true, 0, 0) == DeathOutcome::Ignore);
    assert(AfterLethalInvaderHit(true, 2, 3) == DeathOutcome::Ignore);

    InvasionPermission permission;
    permission.max_members = 5;
    permission.existing_members = 4;
    permission.global_enabled = true;
    permission.host_allowed = true;
    assert(CanAdmitInvader(permission));
    permission.global_enabled = false;
    assert(!CanAdmitInvader(permission));
    permission.global_enabled = true;
    permission.host_allowed = false;
    assert(!CanAdmitInvader(permission));
    permission.host_allowed = true;
    permission.active_boss = true;
    assert(!CanAdmitInvader(permission));
    permission.active_boss = false;
    permission.world_loading = true;
    assert(!CanAdmitInvader(permission));
    permission.world_loading = false;
    permission.existing_members = 5;
    assert(!CanAdmitInvader(permission));
    permission.requester_is_leader = false;
    assert(!MayChangeHostRule(permission));
    permission.requester_is_leader = true;
    assert(MayChangeHostRule(permission));
    std::puts("pvp faction policy: ok");
}
