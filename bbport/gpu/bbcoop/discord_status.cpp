// SPDX-FileCopyrightText: Copyright 2026 CLS_AMG
// SPDX-License-Identifier: GPL-2.0-or-later

// Discord status (Amanises, adapted; Kaniel 2026-11-01: off unless the launcher's Co-op settings
// turn it on). It talks directly to Discord's local IPC pipe, so no Discord SDK or account token
// is bundled. Presence is built from the mutex-protected party snapshot instead of reading game
// memory on this thread.
// Amanises 2026-10-25, Discord parties: a player in a team shows its team as a Discord party
// (its id and size) with a join secret, so Discord offers Join, Ask to Join and "Invite to play"
// in any chat, on a public server only (a home server's code means nothing to a stranger). The
// secret is the team's code (the leader's, any team) or its id (an open team, any member):
// Discord keeps it hidden and hands it to the friend's game, which joins with it.

#include "bbcoop/discord_status.h"

#ifdef _WIN32

#include <windows.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <deque>
#include <mutex>
#include <vector>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <thread>
#include <utility>

#include <fmt/format.h>

#include "bbcoop.h"
#include "bbcoop/discord_activity.h"
#include "bbcoop/discord_presence_policy.h"
#include "bbcoop/build_archetype.h"
#include "common/logging/log.h"
#include "core/bloodborne_party.h"
#include "core/bloodborne_re.h"

namespace {

std::atomic<bool> running{false};

// Amanises 2026-10-25: Discord's join requests waiting for an answer on the team screen, and the
// answers for the Discord thread to send.
std::mutex asks_mutex;
std::vector<CoopDiscord::DiscordAsk> asks;    // asks_mutex
std::deque<std::pair<std::string, bool>> answers; // asks_mutex: user id, accept
constexpr std::size_t MostAsks = 8;

// The launcher says all of it: Co-op settings' "Show my game on Discord", our application's id,
// and whether this is a public server (join secrets).
std::string ApplicationId() {
    const char* value = std::getenv("BB_DISCORD_APP_ID");
    return value != nullptr ? std::string{value} : std::string{};
}

bool Enabled() {
    const char* value = std::getenv("BB_DISCORD_STATUS");
    return value != nullptr && std::string{value} == "1" && !ApplicationId().empty();
}

bool JoinOffered() {
    const char* value = std::getenv("BB_DISCORD_JOIN");
    return value != nullptr && std::string{value} == "1";
}

using DiscordActivity::Field;
using DiscordActivity::Json;

// A friend joined from Discord (Join, an invite): its team by the secret ("c:" a code, "t:" an
// open team's id). A player in another team is refused by the server as for a typed code.
void JoinFromDiscord(const std::string& secret) {
    if (secret.rfind("c:", 0) == 0) {
        bbcoop_lobby_request(BBCOOP_TEAM_JOIN_CODE, secret.substr(2).c_str());
        LOG_INFO(Loader, "Co-op Discord: joining a team from Discord (its code)");
    } else if (secret.rfind("t:", 0) == 0) {
        bbcoop_lobby_request(BBCOOP_TEAM_ASK_JOIN, secret.substr(2).c_str());
        LOG_INFO(Loader, "Co-op Discord: joining open team {} from Discord", secret.substr(2));
    } else {
        LOG_WARNING(Loader, "Co-op Discord: a join secret that is not ours");
    }
}

void NoteJoinRequest(const std::string& json) {
    const std::size_t user = json.find("\"user\"");
    const std::size_t from = user == std::string::npos ? 0 : user;
    const std::string id = Field(json, "id", from);
    std::string name = Field(json, "global_name", from);
    if (name.empty()) {
        name = Field(json, "username", from);
    }
    if (id.empty()) {
        return;
    }
    std::scoped_lock lock{asks_mutex};
    if (std::ranges::any_of(asks, [&](const auto& ask) { return ask.user_id == id; })) {
        return;
    }
    if (asks.size() == MostAsks) {
        asks.erase(asks.begin());
    }
    asks.push_back({id, name.empty() ? std::string{"A Discord friend"} : name});
    LOG_INFO(Loader, "Co-op Discord: {} asks to join through Discord", asks.back().name);
}

const char* AreaName(std::uint32_t map) {
    // Bloodborne text IDs use area*100 + block*10 (m24_01 -> 2410).
    constexpr std::array<std::pair<int, const char*>, 21> areas{{
        {2100, "Hunter's Dream"},
        {2110, "Abandoned Old Workshop"},
        {2200, "Hemwick Charnel Lane"},
        {2300, "Old Yharnam"},
        {2400, "Cathedral Ward"},
        {2410, "Central Yharnam"},
        {2411, "Iosefka's Clinic"},
        {2420, "Upper Cathedral Ward"},
        {2421, "Healing Church Workshop"},
        {2422, "Altar of Despair"},
        {2500, "Forsaken Cainhurst Castle"},
        {2600, "Nightmare of Mensis"},
        {2700, "Forbidden Woods"},
        {2800, "Yahar'gul, Unseen Village"},
        {3200, "Byrgenwerth"},
        {3201, "Lecture Building"},
        {3202, "Moonside Lake"},
        {3300, "Nightmare Frontier"},
        {3400, "Hunter's Nightmare"},
        {3500, "Research Hall"},
        {3600, "Fishing Hamlet"},
    }};
    const int id = static_cast<int>((map >> 24) * 100 + ((map >> 16) & 0xff) * 10);
    for (const auto& [candidate, name] : areas) {
        if (candidate == id) {
            return name;
        }
    }
    return map != 0 ? "The Hunt" : "Title screen";
}

class DiscordPipe {
public:
    ~DiscordPipe() {
        Close();
    }

    bool Connect() {
        for (int index = 0; index < 10; ++index) {
            const std::wstring name = L"\\\\.\\pipe\\discord-ipc-" + std::to_wstring(index);
            pipe = CreateFileW(name.c_str(), GENERIC_READ | GENERIC_WRITE, 0, nullptr,
                               OPEN_EXISTING, 0, nullptr);
            if (pipe != INVALID_HANDLE_VALUE) {
                break;
            }
        }
        if (pipe == INVALID_HANDLE_VALUE ||
            !Send(0, fmt::format("{{\"v\":1,\"client_id\":\"{}\"}}", ApplicationId()))) {
            Close();
            return false;
        }
        return Drain(true);
    }

    bool Send(std::uint32_t opcode, const std::string& json) {
        if (pipe == INVALID_HANDLE_VALUE) {
            return false;
        }
        std::string frame(8, '\0');
        const auto length = static_cast<std::uint32_t>(json.size());
        std::memcpy(frame.data(), &opcode, 4);
        std::memcpy(frame.data() + 4, &length, 4);
        frame += json;
        DWORD written = 0;
        return WriteFile(pipe, frame.data(), static_cast<DWORD>(frame.size()), &written, nullptr) &&
               written == frame.size();
    }

    bool Drain(bool wait) {
        for (;;) {
            DWORD available = 0;
            if (!PeekNamedPipe(pipe, nullptr, 0, nullptr, &available, nullptr)) {
                Close();
                return false;
            }
            if (available < 8 && !wait) {
                return true;
            }
            std::uint32_t header[2]{};
            DWORD got = 0;
            if (!ReadFile(pipe, header, 8, &got, nullptr) || got != 8) {
                Close();
                return false;
            }
            std::string body(header[1], '\0');
            if (header[1] != 0 &&
                (!ReadFile(pipe, body.data(), header[1], &got, nullptr) || got != header[1])) {
                Close();
                return false;
            }
            if (header[0] == 2) {
                Close();
                return false;
            }
            if (header[0] == 3) {
                Send(4, body); // a ping: its pong
            } else if (header[0] == 1) {
                const std::string event = Field(body, "evt");
                if (event == "ACTIVITY_JOIN") {
                    JoinFromDiscord(Field(body, "secret"));
                } else if (event == "ACTIVITY_JOIN_REQUEST") {
                    NoteJoinRequest(body);
                } else if (event == "ERROR") {
                    LOG_WARNING(Loader, "Co-op Discord: Discord says {}", Field(body, "message"));
                }
            }
            wait = false;
        }
    }

    bool Connected() const {
        return pipe != INVALID_HANDLE_VALUE;
    }

    void Close() {
        if (pipe != INVALID_HANDLE_VALUE) {
            CloseHandle(pipe);
            pipe = INVALID_HANDLE_VALUE;
        }
    }

private:
    HANDLE pipe = INVALID_HANDLE_VALUE;
};

// Only the game thread should ultimately populate level, build and boss names.
// The following existing snapshot surfaces already expose co-op, duel and
// invasion states without memory reads on the Discord IPC worker thread.
std::string ActivityJson(const Core::Bloodborne::PartyPanel& panel, const bbcoop_lobby& lobby,
                         std::int64_t started, std::int64_t boss_started) {
    bbcoop_duel duel{};
    bbcoop_duel_view(&duel);
    bbcoop_invasion invasion{};
    bbcoop_invasion_view(&invasion);

    DiscordActivity::PresenceSnapshot snapshot;
    snapshot.location = panel.map != 0 ? AreaName(panel.map)
                       : lobby.in_team ? "Team lobby" : "Title screen";
    snapshot.session_started_unix = started;
    snapshot.boss_fighting = panel.local_boss_fight;
    snapshot.boss_started_unix = boss_started;
    if (panel.local_level >= 4 && panel.local_level <= 544) {
        snapshot.level = panel.local_level;
    }
    if (panel.local_stats_valid) {
        const auto& a = panel.local_offensive_stats;
        if (const auto mask = BbHunterBuild::Mask({a[0], a[1], a[2], a[3]})) {
            snapshot.build = BbHunterBuild::English(*mask);
        }
    }
    snapshot.host = lobby.in_team && lobby.leader;
    snapshot.guest = lobby.in_team && !lobby.leader;
    snapshot.members = lobby.member_count;
    snapshot.capacity = lobby.team_size > 0 ? lobby.team_size : BBCOOP_LOBBY_TEAM;
    snapshot.down = panel.vital == Core::Bloodborne::Vital::Down;
    snapshot.dead = panel.vital == Core::Bloodborne::Vital::Dead;
    snapshot.spectating = panel.vital == Core::Bloodborne::Vital::Spectate ||
                           panel.watching.has_value();
    snapshot.duel = duel.may_cancel && duel.fighters > 0;
    snapshot.team_duel = snapshot.duel && duel.teams != 0;
    snapshot.invading = invasion.role == BBCOOP_INVASION_INVADER &&
                        (invasion.phase == BBCOOP_INVASION_APPROACHING ||
                         invasion.phase == BBCOOP_INVASION_ACTIVE ||
                         invasion.phase == BBCOOP_INVASION_RETURNING);
    snapshot.invasion_searching = invasion.role == BBCOOP_INVASION_INVADER &&
                                   invasion.phase == BBCOOP_INVASION_SEARCHING;

    const bool has_discord_party = lobby.in_team && lobby.team[0] != '\0' &&
                                   !snapshot.invading && !snapshot.invasion_searching;
    const bool accurate_party_size = DiscordActivity::ValidPartyCount(
        snapshot.members, snapshot.capacity);
    // Discord renders "(2 of 5)" by itself from party.size. When it does,
    // omit the custom "(2/5)" suffix so the state is not duplicated.
    snapshot.discord_party_counter = has_discord_party && accurate_party_size;

    DiscordActivity::PresencePrivacy privacy;
    // Current launcher already owns BB_DISCORD_STATUS. Additional per-field
    // switches are opt-in: no unvalidated character data is sent at all.
    if (const char* v = std::getenv("BB_DISCORD_SHOW_AREA")) {
        privacy.show_location = std::string_view{v} == "1";
    }
    privacy.show_level = std::getenv("BB_DISCORD_SHOW_LEVEL") &&
                         std::string_view{std::getenv("BB_DISCORD_SHOW_LEVEL")} == "1";
    privacy.show_build = std::getenv("BB_DISCORD_SHOW_BUILD") &&
                         std::string_view{std::getenv("BB_DISCORD_SHOW_BUILD")} == "1";
    privacy.show_boss = !std::getenv("BB_DISCORD_SHOW_BOSS") ||
                        std::string_view{std::getenv("BB_DISCORD_SHOW_BOSS")} == "1";
    const auto shown = DiscordActivity::Describe(snapshot, privacy);
    std::string activity = "{\"details\":" + Json(shown.details) +
                           ",\"state\":" + Json(shown.state);
    if (shown.start > 0) {
        activity += fmt::format(",\"timestamps\":{{\"start\":{}}}", shown.start);
    }
    activity += ",\"assets\":{\"large_image\":\"yharnam\",\"large_text\":" +
                Json("Yharnam Together") + "}";
    if (has_discord_party) {
        // Keep grouping by team ID even when an old/unknown board has no
        // trustworthy count; never fabricate (1/5) from a zero-member board.
        activity += ",\"party\":{\"id\":" + Json(std::string{"yt-"} + lobby.team);
        if (accurate_party_size) {
            activity += fmt::format(",\"size\":[{},{}]", snapshot.members,
                                    snapshot.capacity);
        }
        activity += "}";
        // Game invites require a real party size. Unknown counts must not
        // advertise spare seats or a join secret.
        const std::string secret =
            accurate_party_size && JoinOffered()
                ? DiscordActivity::JoinSecret(lobby.code, lobby.team, lobby.join,
                                               BBCOOP_JOIN_INVITE_ONLY, snapshot.members,
                                               snapshot.capacity)
                : std::string{};
        if (!secret.empty()) {
            activity += ",\"secrets\":{\"join\":" + Json(secret) + "}";
        }
    }
    return activity + "}";
}

DWORD WINAPI DiscordThread(LPVOID) {
    const auto started = std::chrono::duration_cast<std::chrono::seconds>(
                             std::chrono::system_clock::now().time_since_epoch())
                             .count();
    DiscordPipe discord;
    std::string sent;
    std::uint64_t nonce = 0;
    auto next_try = std::chrono::steady_clock::now();
    bool boss_previous = false;
    std::uint32_t boss_previous_map = 0;
    std::int64_t boss_started = 0;
    for (;;) {
        std::this_thread::sleep_for(std::chrono::seconds(2));
        if (!discord.Connected()) {
            if (std::chrono::steady_clock::now() < next_try) {
                continue;
            }
            if (!discord.Connect()) {
                next_try = std::chrono::steady_clock::now() + std::chrono::seconds(20);
                continue;
            }
            LOG_INFO(Loader, "Co-op Discord status: connected");
            sent.clear();
            // Amanises 2026-10-25: Discord tells this game when a friend joins it or asks to.
            for (const char* event : {"ACTIVITY_JOIN", "ACTIVITY_JOIN_REQUEST"}) {
                discord.Send(1, fmt::format("{{\"cmd\":\"SUBSCRIBE\",\"evt\":\"{}\","
                                            "\"nonce\":\"{}\"}}",
                                            event, ++nonce));
            }
        }
        if (!discord.Drain(false)) {
            continue;
        }
        // The team screen's answers to Discord's join requests.
        std::deque<std::pair<std::string, bool>> to_send;
        {
            std::scoped_lock lock{asks_mutex};
            to_send.swap(answers);
        }
        for (const auto& [user, accept] : to_send) {
            discord.Send(1, fmt::format("{{\"cmd\":\"{}\",\"args\":{{\"user_id\":{}}},"
                                        "\"nonce\":\"{}\"}}",
                                        accept ? "SEND_ACTIVITY_JOIN_INVITE"
                                               : "CLOSE_ACTIVITY_REQUEST",
                                        Json(user), ++nonce));
        }
        Core::Bloodborne::PartyPanel panel;
        Core::Bloodborne::ReadPartyPanel(panel); // also copies the cached snapshot while solo
        // A new observed boss encounter on this map restarts Discord's elapsed
        // timer. While the fight lasts, keep its start even when we spectate;
        // return to the session timer immediately when the encounter ends.
        if (panel.local_boss_fight && (!boss_previous || panel.map != boss_previous_map)) {
            boss_started = std::chrono::duration_cast<std::chrono::seconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();
        } else if (!panel.local_boss_fight) {
            boss_started = 0;
        }
        boss_previous = panel.local_boss_fight;
        boss_previous_map = panel.map;
        static bbcoop_lobby lobby; // large: kept off this thread's stack
        if (bbcoop_lobby_view(&lobby) == 0) {
            lobby = {};
        }
        const std::string activity = ActivityJson(panel, lobby, started, boss_started);
        if (activity == sent) {
            continue;
        }
        const std::string command = fmt::format(
            "{{\"cmd\":\"SET_ACTIVITY\",\"args\":{{\"pid\":{},\"activity\":{}}},"
            "\"nonce\":\"{}\"}}",
            GetCurrentProcessId(), activity, ++nonce);
        if (discord.Send(1, command)) {
            sent = activity;
        } else {
            discord.Close();
        }
    }
}

} // namespace

namespace CoopDiscord {

std::vector<DiscordAsk> DiscordJoinRequests() {
    std::scoped_lock lock{asks_mutex};
    return asks;
}

void AnswerDiscordJoinRequest(const std::string& user_id, bool accept) {
    std::scoped_lock lock{asks_mutex};
    std::erase_if(asks, [&](const DiscordAsk& ask) { return ask.user_id == user_id; });
    answers.emplace_back(user_id, accept);
}

void StartDiscordStatus() {
    if (!Enabled()) {
        LOG_INFO(Loader, "Co-op Discord status: off");
        return;
    }
    if (running.exchange(true)) {
        return;
    }
    if (HANDLE thread = CreateThread(nullptr, 0, DiscordThread, nullptr, 0, nullptr)) {
        CloseHandle(thread);
        LOG_INFO(Loader, "Co-op Discord status: enabled");
    } else {
        running = false;
        LOG_WARNING(Loader, "Co-op Discord status: could not start worker");
    }
}

} // namespace CoopDiscord

#else

namespace CoopDiscord {
std::vector<DiscordAsk> DiscordJoinRequests() {
    return {};
}
void AnswerDiscordJoinRequest(const std::string&, bool) {}
void StartDiscordStatus() {}
} // namespace CoopDiscord

#endif
