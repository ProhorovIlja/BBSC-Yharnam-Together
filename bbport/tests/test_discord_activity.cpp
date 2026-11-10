// SPDX-License-Identifier: GPL-2.0-or-later
// bbport co-op: what the Discord status says and reads (discord_activity.h).
#include <cassert>
#include <cstdio>
#include "gpu/bbcoop/discord_activity.h"
#include "gpu/bbcoop/discord_presence_policy.h"

using namespace DiscordActivity;

int main() {
    assert(Json("Yharnam") == "\"Yharnam\"");
    assert(Json("a\"b\\c") == "\"a\\\"b\\\\c\"");
    assert(Json("line\nbreak") == "\"line break\"");

    const std::string join = "{\"evt\":\"ACTIVITY_JOIN\",\"data\":{\"secret\":\"c:ABC\\\"D\"}}";
    assert(Field(join, "evt") == "ACTIVITY_JOIN");
    assert(Field(join, "secret") == "c:ABC\"D");
    assert(Field(join, "nothing").empty());
    const std::string ask = "{\"id\":\"1\",\"data\":{\"user\":{\"id\":\"42\",\"username\":\"ada\"}}}";
    assert(Field(ask, "id") == "1");
    assert(Field(ask, "id", ask.find("\"user\"")) == "42");

    constexpr int Invite = 0, Ask = 1, Open = 2;
    assert(JoinSecret("KTCDAB", "t1", Invite, Invite, 2, 5) == "c:KTCDAB"); // the leader
    assert(JoinSecret("", "t1", Open, Invite, 2, 5) == "t:t1");
    assert(JoinSecret("", "t1", Ask, Invite, 2, 5) == "t:t1");
    assert(JoinSecret("", "t1", Invite, Invite, 2, 5).empty()) ; // a member of a closed team
    assert(JoinSecret("KTCDAB", "t1", Open, Invite, 5, 5).empty()); // full
    // B56: actual rich presence policy used by discord_status.cpp.
    PresenceSnapshot p;
    p.location = "Central Yharnam";
    p.session_started_unix = 1600000000;
    p.host = true;
    p.members = 3;
    p.capacity = 5;
    auto shown = Describe(p, {});
    assert(shown.details == "In Central Yharnam");
    assert(shown.state == "Hosting");
    assert(shown.start == 1600000000);

    p.host = false;
    p.guest = true;
    shown = Describe(p, {});
    assert(shown.state == "In co-op (3 out of 5)");
    p.members = 7; // unsupported/lying network count: do not invent ratio
    shown = Describe(p, {});
    assert(shown.state == "In co-op");
    p.members = 3;

    p.duel = true;
    shown = Describe(p, {});
    assert(shown.state == "In-duel");
    p.team_duel = true;
    shown = Describe(p, {});
    assert(shown.state == "In Team Duel");
    p.spectating = true; // priority: an active duel remains an active duel
    assert(Describe(p, {}).state == "In Team Duel");
    p.duel = false;
    assert(Describe(p, {}).state == "Spectating");
    p.spectating = false;
    p.down = true;
    assert(Describe(p, {}).state == "Downed");
    p.invading = true;
    assert(Describe(p, {}).state == "Invading");
    p.invading = false;
    p.invasion_searching = true;
    assert(Describe(p, {}).state == "Searching for invasion");
    p.invasion_searching = false;
    p.down = false;

    p.level = 90;
    p.build = "STR+ARC";
    assert(Describe(p, {}).details == "In Central Yharnam");
    PresencePrivacy public_stats;
    public_stats.show_level = true;
    public_stats.show_build = true;
    shown = Describe(p, public_stats);
    assert(shown.details == "In Central Yharnam | Lv 90 | STR+ARC");
    public_stats.show_location = false;
    assert(Describe(p, public_stats).details == "Hunting | Lv 90 | STR+ARC");
    p.level = 9999;
    assert(Describe(p, public_stats).details == "Hunting | STR+ARC");
    public_stats.show_level = false;
    public_stats.show_build = false;
    p.boss = "Cleric Beast";
    p.boss_fighting = true;
    p.boss_started_unix = 1600000123;
    shown = Describe(p, public_stats);
    assert(shown.details == "Boss: Cleric Beast");
    assert(shown.start == 1600000123);
    public_stats.show_boss = false;
    assert(Describe(p, public_stats).details == "Hunting");
    p.boss_started_unix = 0;
    assert(Describe(p, public_stats).start == 1600000000);
    p.boss_fighting = false;
    assert(Describe(p, public_stats).start == 1600000000);

    std::puts("discord activity: ok");
    return 0;
}
