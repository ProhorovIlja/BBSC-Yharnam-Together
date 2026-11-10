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
    // B61 contract: details stay FIXED as location + optional BL/build.
    // Discord exposes only details and state, not an independent BL row.
    PresenceSnapshot p;
    p.location = "Central Yharnam";
    p.level = 25;
    p.build = "STR";
    p.session_started_unix = 1600000000;
    p.members = 2;
    p.capacity = 5;
    p.guest = true;

    PresencePrivacy stats;
    stats.show_level = true;
    stats.show_build = true;
    auto shown = Describe(p, stats);
    assert(shown.details == "Central Yharnam | BL 25   STR Build");
    // A narrow, human-readable gap, not a left/right full-width column.
    assert(shown.details.find("BL 25   STR Build") != std::string::npos);
    assert(shown.details.find("BL 25 | STR Build") == std::string::npos);

    assert(shown.state == "In co-op (2/5)");
    assert(shown.start == 1600000000);

    // The same line stays unchanged throughout the entire boss fight.
    p.boss = "Father Gascoigne";
    p.boss_fighting = true;
    p.boss_started_unix = 1600000123;
    shown = Describe(p, stats);
    assert(shown.details == "Central Yharnam | BL 25   STR Build");
    assert(shown.state == "Fighting Father Gascoigne (2/5)");
    assert(shown.start == 1600000123);
    // Host fights also show the boss and party occupancy, not "Hosting".
    p.guest = false;
    p.host = true;
    assert(Describe(p, stats).state == "Fighting Father Gascoigne (2/5)");
    // Native party.size automatically renders "(2 of 5)" on Discord; never
    // repeat an explicit "(2/5)" in the state.
    p.discord_party_counter = true;
    assert(Describe(p, stats).state == "Fighting Father Gascoigne");
    p.boss_fighting = false;
    assert(Describe(p, stats).state == "Hosting");
    assert(Describe(p, stats).start == 1600000000);
    p.guest = true;
    p.host = false;
    assert(Describe(p, stats).state == "In co-op");
    p.discord_party_counter = false;
    assert(Describe(p, stats).state == "In co-op (2/5)");

    // Exactly the same details line and the overall session timer return.
    p.boss_fighting = true;
    p.boss_started_unix = 1600000200;
    assert(Describe(p, stats).start == 1600000200);
    stats.show_boss = false;
    shown = Describe(p, stats);
    assert(shown.details == "Central Yharnam | BL 25   STR Build");
    assert(shown.state == "In co-op (2/5)");
    assert(shown.start == 1600000000); // a private fight does not leak via timer
    stats.show_boss = true;

    // Never identify a boss without validated gauge/ID evidence.
    p.boss.clear();
    assert(Describe(p, stats).state == "Boss fight (2/5)");
    p.boss = "Father Gascoigne";
    p.spectating = true;
    assert(Describe(p, stats).state == "Spectating");
    assert(Describe(p, stats).details == "Central Yharnam | BL 25   STR Build");
    p.spectating = false;

    // Invasion/duels/down states override stale game boss flags.
    p.invading = true;
    assert(Describe(p, stats).state == "Invading");
    p.invading = false;
    p.invasion_searching = true;
    assert(Describe(p, stats).state == "Searching for invasion");
    p.invasion_searching = false;
    p.duel = true;
    assert(Describe(p, stats).state == "In-duel");
    p.team_duel = true;
    assert(Describe(p, stats).state == "In Team Duel");
    p.duel = false;
    p.down = true;
    assert(Describe(p, stats).state == "Downed");
    p.down = false;
    p.dead = true;
    assert(Describe(p, stats).state == "Fallen");
    p.dead = false;
    p.boss_fighting = false;

    // Privacy toggles are independent. Hidden area/boss never reappear
    // under stats, status, or timer.
    stats.show_location = false;
    assert(Describe(p, stats).details == "Hunting | BL 25   STR Build");
    stats.show_level = false;
    assert(Describe(p, stats).details == "Hunting | STR Build");
    stats.show_build = false;
    assert(Describe(p, stats).details == "Hunting");
    stats.show_location = true;
    stats.show_level = true;
    stats.show_build = true;
    p.level = 9999;
    assert(Describe(p, stats).details == "Central Yharnam | STR Build");
    p.level = 25;
    p.build = "STR/ARC";
    assert(Describe(p, stats).details == "Central Yharnam | BL 25   STR/ARC Build");

    // Unknown or impossible membership is never advertised as fake seats.
    assert(ValidPartyCount(2, 5));
    assert(!ValidPartyCount(0, 5));
    assert(!ValidPartyCount(6, 5));
    assert(!ValidPartyCount(2, 0));
    p.members = 7;
    assert(Describe(p, stats).state == "In co-op");
    p.members = 2;
    // Solo fights must not claim a 2/5 party.
    p.guest = false;
    p.boss_fighting = true;
    p.boss = "Father Gascoigne";
    p.boss_started_unix = 1600000300;
    assert(Describe(p, stats).state == "Fighting Father Gascoigne");
    assert(Describe(p, stats).start == 1600000300);
    p.boss_fighting = false;
    assert(Describe(p, stats).state == "Solo hunter");

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

    // B61: verify the same B58 classifier still maps all sixteen masks.
    constexpr std::string_view short_names[16] = {
        "UNF", "STR", "SKL", "QLT", "BLT",
        "STR/BLT", "SKL/BLT", "QLT/BLT",
        "ARC", "STR/ARC", "SKL/ARC", "QLT/ARC",
        "BLT/ARC", "STR/BLT/ARC", "SKL/BLT/ARC", "OMNI"
    };
    for (unsigned mask = 0; mask < 16; ++mask) {
        const auto attrs = BbHunterBuild::Attributes{
            mask & 1 ? 18 : 17, mask & 2 ? 18 : 17,
            mask & 4 ? 18 : 17, mask & 8 ? 18 : 17};
        const auto actual = BbHunterBuild::Mask(attrs);
        assert(actual && *actual == mask);
        assert(BbHunterBuild::DiscordShort(*actual) == short_names[mask]);
        assert(!BbHunterBuild::English(*actual).empty());
    }
    assert(BbHunterBuild::English(3) == "Quality"); // game HUD unchanged
    assert(BbHunterBuild::DiscordShort(3) == "QLT");
    assert(BbHunterBuild::DiscordShort(9) == "STR/ARC");
    assert(BbHunterBuild::DiscordShort(15) == "OMNI");
    assert(BbHunterBuild::DiscordShort(16) == "Unknown");

    // No extra row is silently encoded as newline; Discord text rows do
    // not support independently positioned third/fourth custom strings.
    assert(Describe(p, stats).details.find('\n') == std::string::npos);
    assert(Describe(p, stats).state.find('\n') == std::string::npos);

    // B62: reproduce the **two real fields + timer** seen in the uploaded
    // Discord desktop profile, rather than inventing a third custom field.
    PresenceSnapshot example;
    example.location = "Central Yharnam";
    example.level = 25;
    example.build = "STR";
    example.guest = true;
    example.members = 2;
    example.capacity = 5;
    example.session_started_unix = 1600000000;
    PresencePrivacy visible;
    visible.show_location = true;
    visible.show_level = true;
    visible.show_build = true;
    visible.show_boss = true;
    const auto screenshot = PresenceLayout::ReferenceCard;
    auto card = Describe(example, visible, screenshot);
    assert(card.details == "In Central Yharnam");
    assert(card.state == "BL 25   STR Build · Co-op (2/5)");
    assert(card.start == 1600000000);

    example.boss_fighting = true;
    example.boss = "Father Gascoigne";
    example.boss_started_unix = 1600000099;
    card = Describe(example, visible, screenshot);
    assert(card.details == "Fighting Father Gascoigne");
    assert(card.state == "BL 25   STR Build · Co-op (2/5)");
    assert(card.start == 1600000099);
    example.spectating = true;
    card = Describe(example, visible, screenshot);
    assert(card.details == "Spectating in Central Yharnam");
    assert(card.state == "BL 25   STR Build · Co-op (2/5)");
    example.spectating = false;
    example.boss.clear();
    card = Describe(example, visible, screenshot);
    assert(card.details == "Boss fight");
    visible.show_boss = false;
    card = Describe(example, visible, screenshot);
    assert(card.details == "In Central Yharnam");
    assert(card.start == 1600000000); // privacy: no fight-only timer
    visible.show_boss = true;

    example.boss_fighting = false;
    example.guest = false;
    card = Describe(example, visible, screenshot);
    assert(card.details == "In Central Yharnam");
    assert(card.state == "BL 25   STR Build · Solo");

    example.invading = true;
    example.boss_fighting = true; // stale boss cache must not override invader state
    card = Describe(example, visible, screenshot);
    assert(card.details == "In Central Yharnam");
    assert(card.state == "BL 25   STR Build · Invading");
    example.invading = false;
    example.boss_fighting = false;
    example.duel = true;
    example.team_duel = true;
    assert(Describe(example, visible, screenshot).state == "BL 25   STR Build · In Team Duel");
    example.duel = false;
    example.team_duel = false;

    // The user's original B61 compact mode is still intact and selectable.
    example.guest = true;
    auto compact = Describe(example, visible, PresenceLayout::StatusFirst);
    assert(compact.details == "Central Yharnam | BL 25   STR Build");
    assert(compact.state == "In co-op (2/5)");

    example.discord_party_counter = true;
    card = Describe(example, visible, screenshot);
    assert(card.state == "BL 25   STR Build · Co-op");
    example.discord_party_counter = false;

    visible.show_level = false;
    visible.show_build = false;
    card = Describe(example, visible, screenshot);
    assert(card.details == "In Central Yharnam");
    assert(card.state == "Co-op (2/5)");
    visible.show_location = false;
    card = Describe(example, visible, screenshot);
    assert(card.details == "Hunting");
    // The two fields do not contain newlines and we never send untrusted
    // player text as a fake third Discord line.
    assert(card.details.find('\n') == std::string::npos);
    assert(card.state.find('\n') == std::string::npos);

    std::puts("discord activity: ok");
    return 0;
}
