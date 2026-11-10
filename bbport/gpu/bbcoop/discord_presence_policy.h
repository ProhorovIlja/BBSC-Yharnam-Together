// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <algorithm>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

namespace DiscordActivity {

// Privacy is local to the hunter; no launcher should transmit saved stats by
// default. Actual character data must originate from a validated game snapshot.
struct PresencePrivacy {
    bool show_location = true;
    bool show_level = false;
    bool show_build = false;
    bool show_boss = true;
};

struct PresenceSnapshot {
    std::string location;
    std::optional<unsigned> level;
    std::string build;
    std::string boss;
    bool boss_fighting = false;
    std::int64_t boss_started_unix = 0; // trusted game-side encounter transition
    std::int64_t session_started_unix = 0;

    bool host = false;
    bool guest = false;
    bool invading = false;
    bool invasion_searching = false;
    bool spectating = false;
    bool down = false;
    bool dead = false;
    bool duel = false;
    bool team_duel = false;
    int members = 0;
    int capacity = 0;
    // Discord automatically appends "(2 of 5)" when an RPC activity
    // includes a valid party.size. Never echo a second "(2/5)" in state.
    bool discord_party_counter = false;
};

inline constexpr bool ValidPartyCount(int members, int capacity) {
    return capacity > 0 && members > 0 && members <= capacity;
}

struct PresenceText {
    std::string details;
    std::string state;
    std::int64_t start = 0;
};

inline PresenceText Describe(const PresenceSnapshot& s, const PresencePrivacy& privacy) {
    PresenceText out;
    // B61: user's visual contract is location, then BL / build, then
    // activity status, then a live elapsed timer. Discord RPC itself has
    // only TWO custom text fields; the separate BL/build row requested by
    // the user cannot be provided as an independent native Discord row.
    // Therefore details always carry location + optional local stats,
    // and state alone changes when the boss fight starts or ends.
    const bool location_visible = privacy.show_location && !s.location.empty();
    out.details = location_visible ? s.location : "Hunting";
    if (privacy.show_level && s.level && *s.level >= 4 && *s.level <= 544) {
        out.details += " | BL " + std::to_string(*s.level);
    }
    if (privacy.show_build && !s.build.empty() && s.build.size() <= 48) {
        out.details += " | " + s.build + " Build";
    }

    // The final co-op count is an explicit manual (2/5) only when no
    // Discord party.size is in the RPC payload. Discord appends (2 of 5)
    // automatically when native party.size is transmitted instead.
    const auto party_suffix = [&]() -> std::string {
        if (!s.discord_party_counter && ValidPartyCount(s.members, s.capacity) &&
            (s.host || s.guest)) {
            return " (" + std::to_string(s.members) + "/" +
                   std::to_string(s.capacity) + ")";
        }
        return {};
    };

    // Priority: roles with different privacy/authority boundaries win
    // over combat snapshots from stale world ticks. Boss combat applies
    // to solo/host/co-op but NEVER changes details (map/BL/build).
    if (s.invading) {
        out.state = "Invading";
    } else if (s.invasion_searching) {
        out.state = "Searching for invasion";
    } else if (s.spectating) {
        out.state = "Spectating";
    } else if (s.duel) {
        out.state = s.team_duel ? "In Team Duel" : "In-duel";
    } else if (s.down) {
        out.state = "Downed";
    } else if (s.dead) {
        out.state = "Fallen";
    } else if (s.boss_fighting && privacy.show_boss) {
        out.state = s.boss.empty() ? "Boss fight" : "Fighting " + s.boss;
        out.state += party_suffix();
    } else if (s.host) {
        out.state = "Hosting";
    } else if (s.guest) {
        out.state = "In co-op" + party_suffix();
    } else {
        out.state = "Solo hunter";
    }
    // Discord has two short text fields and a single visible timer. Use the
    // fight start while the encounter runs, then restore play-session uptime.
    if (s.boss_fighting && privacy.show_boss && s.boss_started_unix > 0) {
        out.start = s.boss_started_unix;
    }
    if (out.start == 0) {
        out.start = std::max<std::int64_t>(0, s.session_started_unix);
    }
    // Discord's two text fields are compact; use an honest truncated label.
    if (out.details.size() > 120) {
        out.details.resize(120);
        while (!out.details.empty() &&
               (static_cast<unsigned char>(out.details.back()) & 0xC0) == 0x80) {
            out.details.pop_back();
        }
    }
    return out;
}

} // namespace DiscordActivity
