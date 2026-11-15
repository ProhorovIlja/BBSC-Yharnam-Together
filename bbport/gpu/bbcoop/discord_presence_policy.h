// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <algorithm>
#include <cstdint>
#include <cstddef>
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

// B63: game-thread telemetry is a short-lived lease, NOT a forever-cached
// record. Both sides measure steady_clock milliseconds in this same process.
// The independent lobby state is still queried live on the Discord thread.
inline constexpr std::int64_t GameSnapshotMaxAgeMs = 10'000;
[[nodiscard]] inline constexpr bool GameSnapshotFresh(std::int64_t observed_ms,
                                                     std::int64_t now_ms) {
    return observed_ms > 0 && now_ms >= observed_ms &&
           now_ms - observed_ms <= GameSnapshotMaxAgeMs;
}

// Keep the longest *valid* UTF-8 prefix without cutting halfway through a
// code point. The old resize(120) + strip continuation bytes could leave an
// orphan UTF-8 lead byte when truncation landed after the second byte of a
// three-byte character. Malformed game-provided strings fail at first bad
// character rather than being sent raw to Discord JSON.
inline void BoundValidUtf8(std::string& text, std::size_t limit = 120) {
    std::size_t n = 0;
    while (n < text.size() && n < limit) {
        const auto first = static_cast<unsigned char>(text[n]);
        std::size_t width = 0;
        if (first < 0x80) width = 1;
        else if (first >= 0xC2 && first <= 0xDF) width = 2;
        else if (first >= 0xE0 && first <= 0xEF) width = 3;
        else if (first >= 0xF0 && first <= 0xF4) width = 4;
        else break;
        if (width > text.size() - n || width > limit - n) break;
        bool good = true;
        for (std::size_t k = 1; k < width; ++k) {
            const auto b = static_cast<unsigned char>(text[n + k]);
            if ((b & 0xC0u) != 0x80u) { good = false; break; }
        }
        if (!good) break;
        if (width >= 3) {
            const auto second = static_cast<unsigned char>(text[n + 1]);
            if ((first == 0xE0 && second < 0xA0) ||
                (first == 0xED && second >= 0xA0) ||
                (first == 0xF0 && second < 0x90) ||
                (first == 0xF4 && second >= 0x90)) break;
        }
        n += width;
    }
    text.resize(n);
}

inline constexpr bool ValidPartyCount(int members, int capacity) {
    return capacity > 0 && members > 0 && members <= capacity;
}

// Only the two Discord text fields are available. ReferenceCard follows
// the user's supplied real-profile screenshot: area on row one, adjacent
// BL/build + context on row two, and the elapsed time below. The exact
// additional independent status row shown in the user's mockup would require
// a third custom Discord field, which the documented RPC API does not offer.
enum class PresenceLayout { StatusFirst, ReferenceCard };

struct PresenceText {
    std::string details;
    std::string state;
    std::int64_t start = 0;
};

inline PresenceText Describe(const PresenceSnapshot& s, const PresencePrivacy& privacy,
                             PresenceLayout layout = PresenceLayout::StatusFirst) {
    PresenceText out;
    // B61: user's visual contract is location, then BL / build, then
    // activity status, then a live elapsed timer. Discord RPC itself has
    // only TWO custom text fields; the separate BL/build row requested by
    // the user cannot be provided as an independent native Discord row.
    // Therefore details always carry location + optional local stats,
    // and state alone changes when the boss fight starts or ends.
    const bool location_visible = privacy.show_location && !s.location.empty();
    out.details = location_visible ? s.location : "Hunting";
    // Blood Level and Build belong to one compact, adjacent group.
    // Three spaces are a small visual gap, NOT two opposite edges of a row,
    // and NOT a pipe divider between BL and the archetype.
    const bool has_bl = privacy.show_level && s.level &&
                        *s.level >= 4 && *s.level <= 544;
    if (has_bl) {
        out.details += " | BL " + std::to_string(*s.level);
    }
    if (privacy.show_build && !s.build.empty() && s.build.size() <= 48) {
        out.details += has_bl ? "   " : " | ";
        out.details += s.build + " Build";
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
    if (s.boss_fighting && privacy.show_boss && s.boss_started_unix > 0 &&
        !s.invading && !s.invasion_searching && !s.duel) {
        out.start = s.boss_started_unix;
    }
    if (out.start == 0) {
        out.start = std::max<std::int64_t>(0, s.session_started_unix);
    }
    if (layout == PresenceLayout::ReferenceCard) {
        // Screenshot-compatible card presentation. The first line carries
        // the area normally, or the boss activity during an encounter.
        // The second carries Blood Level, build and co-op/role together.
        // These are supported native fields, never injected line breaks.
        const bool in_pvp = s.invading || s.invasion_searching || s.duel;
        if (s.spectating) {
            out.details = location_visible ? "Spectating in " + s.location : "Spectating";
        } else if (s.boss_fighting && privacy.show_boss && !in_pvp) {
            out.details = s.boss.empty() ? "Boss fight" : "Fighting " + s.boss;
        } else {
            out.details = location_visible ? "In " + s.location : "Hunting";
        }

        std::string stats;
        if (has_bl) {
            stats = "BL " + std::to_string(*s.level);
        }
        if (privacy.show_build && !s.build.empty() && s.build.size() <= 48) {
            if (!stats.empty()) stats += "   ";
            stats += s.build + " Build";
        }

        std::string role = out.state;
        // During a boss or spectate the activity goes on the FIRST field.
        // The second describes character identity + actual session mode,
        // without repeating "Fighting ..." twice in the same card.
        if (((s.boss_fighting && privacy.show_boss) && !in_pvp) || s.spectating) {
            if (s.host || s.guest) {
                role = "Co-op" + party_suffix();
            } else {
                role = "Solo";
            }
        } else if (s.host && role == "Hosting") {
            role += party_suffix();
        }
        if (role == "Solo hunter") role = "Solo";
        if (role == "In co-op" || role.starts_with("In co-op (")) {
            role.replace(0, 8, "Co-op");
        }
        out.state = stats.empty() ? role : stats + " · " + role;
    }

    // Discord's two text fields accept bounded UTF-8. Apply the same
    // deterministic validated prefix to both, including short malformed
    // input and code points straddling byte 120.
    BoundValidUtf8(out.details);
    BoundValidUtf8(out.state);
    return out;
}

} // namespace DiscordActivity
