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

    bool Drain(bool wait_for_ready) {
        constexpr std::uint32_t MaxBody = 64 * 1024; // Local budget for activity RPC.
        constexpr unsigned MaxFramesPerPoll = 32;
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        for (unsigned frames = 0; frames < MaxFramesPerPoll;) {
            if (wait_for_ready && std::chrono::steady_clock::now() >= deadline) {
                Close();
                return false;
            }
            if (header_used < sizeof(header)) {
                if (!ReadAvailable(reinterpret_cast<char*>(header), sizeof(header), header_used)) {
                    Close();
                    return false;
                }
                if (header_used == sizeof(header)) {
                    if (header[1] > MaxBody) {
                        Close();
                        return false;
                    }
                    body.resize(header[1]);
                }
            }
            if (header_used == sizeof(header) && body_used < header[1] &&
                !ReadAvailable(body.data(), header[1], body_used)) {
                Close();
                return false;
            }
            if (header_used != sizeof(header) || body_used != header[1]) {
                if (!wait_for_ready) {
                    return true;
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
                continue;
            }

            const auto opcode = header[0];
            header_used = body_used = 0;
            ++frames;
            if (opcode == 2) {
                Close();
                return false;
            }
            if (opcode == 3) {
                if (!Send(4, body)) {
                    Close();
                    return false;
                }
            } else if (opcode == 1) {
                const std::string event = Field(body, "evt");
                if (wait_for_ready) {
                    if (event == "READY") {
                        return true;
                    }
                    if (event == "ERROR") {
                        Close();
                        return false;
                    }
                } else if (event == "ACTIVITY_JOIN") {
                    JoinFromDiscord(Field(body, "secret"));
                } else if (event == "ACTIVITY_JOIN_REQUEST") {
                    NoteJoinRequest(body);
                } else if (event == "ERROR") {
                    LOG_WARNING(Loader, "Co-op Discord: Discord says {}", Field(body, "message"));
                }
            }
        }
        if (wait_for_ready) {
            Close();
            return false;
        }
        return true;
    }

    bool Connected() const {
        return pipe != INVALID_HANDLE_VALUE;
    }

    void Close() {
        if (pipe != INVALID_HANDLE_VALUE) {
            CloseHandle(pipe);
            pipe = INVALID_HANDLE_VALUE;
        }
        header_used = body_used = 0;
        body.clear();
    }

private:
    // This thread is the sole reader. Consume only bytes already buffered, retaining partial
    // frames across polls instead of blocking ReadFile on a peer that stopped mid-frame.
    bool ReadAvailable(char* dest, DWORD total, DWORD& used) {
        DWORD available = 0;
        if (!PeekNamedPipe(pipe, nullptr, 0, nullptr, &available, nullptr)) {
            return false;
        }
        if (available == 0) {
            return true;
        }
        const DWORD remaining = total - used;
        const DWORD amount = available < remaining ? available : remaining;
        DWORD got = 0;
        if (!ReadFile(pipe, dest + used, amount, &got, nullptr) || got == 0 || got > amount) {
            return false;
        }
        used += got;
        return true;
    }

    HANDLE pipe = INVALID_HANDLE_VALUE;
    std::uint32_t header[2]{};
    DWORD header_used = 0;
    DWORD body_used = 0;
    std::string body;
};

std::string ActivityJson(const Core::Bloodborne::PartyPanel& panel, const bbcoop_lobby& lobby,
                         std::int64_t started) {
    const int size = lobby.team_size > 0 ? lobby.team_size : BBCOOP_LOBBY_TEAM;
    bbcoop_duel duel{};
    bbcoop_duel_view(&duel);
    bbcoop_invasion invasion{};
    bbcoop_invasion_view(&invasion);

    DiscordActivity::PresenceSnapshot snapshot;
    snapshot.location = AreaName(panel.map);
    if (panel.map == 0 && lobby.in_team) {
        snapshot.location = "Team lobby";
    }
    snapshot.session_started_unix = started;
    if (panel.local_level >= 4 && panel.local_level <= 544) {
        snapshot.level = panel.local_level;
    }
    if (panel.local_stats_valid) {
        const auto& a = panel.local_offensive_stats;
        if (const auto mask = BbHunterBuild::Mask({a[0], a[1], a[2], a[3]})) {
            snapshot.build = BbHunterBuild::DiscordShort(*mask);
        }
    }
    snapshot.boss_fighting = panel.local_boss_fight;
    snapshot.boss = panel.local_boss_name;
    snapshot.boss_started_unix = panel.local_boss_started_unix;
    snapshot.host = lobby.in_team && lobby.leader;
    snapshot.guest = lobby.in_team && !lobby.leader;
    snapshot.members = lobby.member_count;
    snapshot.capacity = size;
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

    const bool has_party = lobby.in_team && lobby.team[0] != '\0' &&
                           !snapshot.invading && !snapshot.invasion_searching &&
                           DiscordActivity::ValidPartyCount(snapshot.members, size);
    // Keep Discord's native party count and join behavior. The formatter must
    // not also append a textual count when party.size is sent.
    snapshot.discord_party_counter = has_party;
    DiscordActivity::PresencePrivacy privacy;
    if (const char* show_area = std::getenv("BB_DISCORD_SHOW_AREA")) {
        privacy.show_location = std::strcmp(show_area, "1") == 0;
    }
    if (const char* value = std::getenv("BB_DISCORD_SHOW_LEVEL")) {
        privacy.show_level = std::strcmp(value, "1") == 0;
    }
    if (const char* value = std::getenv("BB_DISCORD_SHOW_BUILD")) {
        privacy.show_build = std::strcmp(value, "1") == 0;
    }
    if (const char* value = std::getenv("BB_DISCORD_SHOW_BOSS")) {
        privacy.show_boss = std::strcmp(value, "1") == 0;
    }
    const auto shown = DiscordActivity::Describe(
        snapshot, privacy, DiscordActivity::PresenceLayout::ReferenceCard);
    std::string activity = "{\"details\":" + Json(shown.details) + ",\"state\":" +
                           Json(shown.state);
    if (shown.start > 0) {
        activity += fmt::format(",\"timestamps\":{{\"start\":{}}}", shown.start);
    }
    activity += ",\"assets\":{\"large_image\":\"yharnam\",\"large_text\":" +
                Json("BBSC: Yharnam Together") + "}";
    if (has_party) {
        // One party for the whole team (Discord groups its members), and the secret to join it.
        activity += fmt::format(",\"party\":{{\"id\":{},\"size\":[{},{}]}}",
                                Json(std::string{"yt-"} + lobby.team), lobby.member_count, size);
        const std::string secret =
            JoinOffered() ? DiscordActivity::JoinSecret(lobby.code, lobby.team, lobby.join,
                                                        BBCOOP_JOIN_INVITE_ONLY, lobby.member_count,
                                                        size)
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
        const auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        if (!DiscordActivity::GameSnapshotFresh(panel.rpc_snapshot_steady_ms, now_ms)) {
            panel = {};
        }
        static bbcoop_lobby lobby; // large: kept off this thread's stack
        if (bbcoop_lobby_view(&lobby) == 0) {
            lobby = {};
        }
        const std::string activity = ActivityJson(panel, lobby, started);
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
