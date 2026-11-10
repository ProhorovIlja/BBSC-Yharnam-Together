// SPDX-License-Identifier: GPL-2.0-or-later
// bbport co-op: what the Discord status says and reads (discord_activity.h).
#include <cassert>
#include <cstdio>
#include "gpu/bbcoop/discord_activity.h"
#include "gpu/bbcoop/discord_presence_policy.h"
#include "gpu/bbcoop/build_archetype.h"

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
    assert(shown.state == "In co-op (3/5)");
    p.members = 2;
    assert(Describe(p, {}).state == "In co-op (2/5)");
    assert(ValidPartyCount(2, 5));
    assert(!ValidPartyCount(0, 5));
    assert(!ValidPartyCount(6, 5));
    assert(!ValidPartyCount(2, 0));
    // With party.size in Discord's payload, Discord itself adds "(2 of 5)".
    // State must not repeat the count, or friends see both formats together.
    p.discord_party_counter = true;
    assert(Describe(p, {}).state == "In co-op");
    p.discord_party_counter = false;
    p.members = 3;
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
    p.spectating = true; // dead boss observer outranks stale duel
    assert(Describe(p, {}).state == "Spectating");
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

    p.level = 25;
    p.build = "STR/ARC";
    assert(Describe(p, {}).details == "In Central Yharnam");
    PresencePrivacy public_stats;
    public_stats.show_level = true;
    public_stats.show_build = true;
    shown = Describe(p, public_stats);
    assert(shown.details == "In Central Yharnam | BL 25 | STR/ARC Build");
    public_stats.show_location = false;
    assert(Describe(p, public_stats).details == "Hunting | BL 25 | STR/ARC Build");
    p.level = 9999;
    assert(Describe(p, public_stats).details == "Hunting | STR/ARC Build");
    public_stats.show_location = true; // restore independent area consent for boss fixture
    public_stats.show_level = false;
    public_stats.show_build = false;
    p.boss = "Cleric Beast";
    p.boss_fighting = true;
    p.boss_started_unix = 1600000123;
    shown = Describe(p, public_stats);
    assert(shown.details == "Fighting Cleric Beast | Central Yharnam");
    assert(shown.start == 1600000123);
    public_stats.show_level = true;
    public_stats.show_build = true;
    p.level = 25;
    assert(Describe(p, public_stats).details ==
           "Fighting Cleric Beast | Central Yharnam | BL 25 | STR/ARC Build");
    public_stats.show_location = false;
    assert(Describe(p, public_stats).details == "Fighting Cleric Beast | BL 25 | STR/ARC Build");
    public_stats.show_boss = false;
    assert(Describe(p, public_stats).details == "Hunting | BL 25 | STR/ARC Build");
    assert(Describe(p, public_stats).start == 1600000000); // privacy hides fight timer
    public_stats.show_boss = true;
    p.boss_started_unix = 0;
    assert(Describe(p, public_stats).start == 1600000000);
    p.boss_fighting = false;
    assert(Describe(p, public_stats).start == 1600000000);

    // B45 classifier reused instead of guessing a build from level.
    // 18 inclusive across STR/SKL/BLT/ARC, with 16 combinations.
    assert(BbHunterBuild::Mask({18, 17, 17, 17}) == 1);
    assert(BbHunterBuild::Mask({18, 18, 17, 17}) == 3);
    assert(BbHunterBuild::English(3) == "Quality");
    assert(BbHunterBuild::Mask({18, 18, 18, 18}) == 15);
    assert(BbHunterBuild::English(15) == "Omnibuild");
    assert(!BbHunterBuild::Mask({18, 0, 18, 18}));
    // Every valid mask is independently named. Threshold 18 is inclusive;
    // below 18 is not included in the current hunter's archetype.
    for (unsigned mask = 0; mask < 16; ++mask) {
        const auto stats = BbHunterBuild::Attributes{
            mask & 1 ? 18 : 17, mask & 2 ? 18 : 17,
            mask & 4 ? 18 : 17, mask & 8 ? 18 : 17};
        const auto actual = BbHunterBuild::Mask(stats);
        assert(actual.has_value() && *actual == mask);
        assert(!BbHunterBuild::English(*actual).empty());
    }
    assert(BbHunterBuild::English(0) == "Unfocused");
    assert(BbHunterBuild::English(5) == "Strength/Blood");
    assert(BbHunterBuild::English(9) == "Strength/Arcane");
    assert(BbHunterBuild::English(10) == "Skill/Arcane");
    assert(BbHunterBuild::English(12) == "Blood/Arcane");

    // B58: independent compact Discord labels for ALL valid 18+ masks,
    // while the descriptive English/Russian names are unaffected.
    constexpr std::string_view short_names[16] = {
        "UNF", "STR", "SKL", "QLT", "BLT",
        "STR/BLT", "SKL/BLT", "QLT/BLT",
        "ARC", "STR/ARC", "SKL/ARC", "QLT/ARC",
        "BLT/ARC", "STR/BLT/ARC", "SKL/BLT/ARC", "OMNI"
    };
    for (unsigned mask = 0; mask < 16; ++mask) {
        const auto stats = BbHunterBuild::Attributes{
            mask & 1 ? 18 : 17, mask & 2 ? 18 : 17,
            mask & 4 ? 18 : 17, mask & 8 ? 18 : 17};
        const auto actual = BbHunterBuild::Mask(stats);
        assert(actual && BbHunterBuild::DiscordShort(*actual) == short_names[mask]);
    }
    assert(BbHunterBuild::DiscordShort(3) == "QLT");
    assert(BbHunterBuild::English(3) == "Quality"); // existing HUD name stays
    assert(BbHunterBuild::DiscordShort(9) == "STR/ARC");
    assert(BbHunterBuild::DiscordShort(15) == "OMNI");
    assert(BbHunterBuild::DiscordShort(16) == "Unknown");

    // B58: visible location and BL remain present even with boss detail.
    PresenceSnapshot small;
    small.location = "Hunter's Dream";
    small.level = 25;
    small.build = "QLT";
    small.boss_fighting = true;
    small.boss = "Gehrman";
    small.session_started_unix = 1600000000;
    small.boss_started_unix = 1600000123;
    PresencePrivacy opt_in;
    opt_in.show_level = opt_in.show_build = true;
    assert(Describe(small, opt_in).details == "Fighting Gehrman | Hunter's Dream | BL 25 | QLT Build");
    assert(Describe(small, opt_in).start == 1600000123);
    opt_in.show_boss = false;
    assert(Describe(small, opt_in).details == "In Hunter's Dream | BL 25 | QLT Build");
    assert(Describe(small, opt_in).start == 1600000000);
    opt_in.show_location = false;
    assert(Describe(small, opt_in).details == "Hunting | BL 25 | QLT Build");
    opt_in.show_boss = true;
    assert(Describe(small, opt_in).details == "Fighting Gehrman | BL 25 | QLT Build");
    opt_in.show_level = opt_in.show_build = false;
    opt_in.show_boss = false;
    assert(Describe(small, opt_in).details == "Hunting");

    // B59: while observing another hunter's boss fight, avoid claiming
    // "Fighting" ourselves. State and details should agree on spectating.
    opt_in.show_boss = true;
    small.spectating = true;
    assert(Describe(small, opt_in).state == "Spectating");
    assert(Describe(small, opt_in).details == "Watching Gehrman");
    assert(Describe(small, opt_in).start == 1600000123);
    small.spectating = false;
    small.boss.clear();
    assert(Describe(small, opt_in).details == "Boss fight");
    small.boss_fighting = false;
    assert(Describe(small, opt_in).details == "Hunting");
    assert(Describe(small, opt_in).start == 1600000000);

    // Short labels for every 18+ archetype are classifier-owned. Only the
    // activity presentation appends "Build" and never doubles it in the game.
    opt_in.show_build = true;
    small.build = "STR";
    assert(Describe(small, opt_in).details == "Hunting | STR Build");
    small.build = "STR/ARC";
    assert(Describe(small, opt_in).details == "Hunting | STR/ARC Build");
    small.build.clear();
    assert(Describe(small, opt_in).details == "Hunting");



    std::puts("discord activity: ok");
    return 0;
}
