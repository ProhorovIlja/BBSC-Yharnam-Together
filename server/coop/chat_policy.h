// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// A transport-independent, server-side admission gate for future text chat.
// Never derive a sender id, a team id, or a cross-server audience from a client packet.
// This helper is deliberately NOT wired to the game protocol until the client and server
// have authenticated sender/session plumbing. Global means THIS shard only.
#include <algorithm>
#include <cstdint>
#include <deque>
#include <set>
#include <span>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace BloodborneCoop::Comms {

enum class Scope : std::uint8_t { Global = 1, Team = 2, Direct = 3 };
enum class Status : std::uint8_t {
    Ok, UnknownSender, Disabled, InvalidText, RateLimited, NoTeam, Unavailable, Capacity
};

struct Peer {
    std::string id;    // authenticated account id on this server
    std::string team;  // live authoritative TeamLobby id, empty if not in a team
    bool online = true;
    bool can_send = true;
    bool receive_global = true;
    bool receive_team = true;
    bool receive_direct = true;
    std::set<std::string> blocked; // authenticated account ids blocked by this recipient
};

struct Request {
    Scope scope = Scope::Team;
    std::string text;
    std::string recipient; // exact server-resolved account id for Direct; NOT a display name
};

struct Decision {
    Status status = Status::Unavailable;
    std::vector<std::string> recipients; // excludes sender; success is also an acknowledgement
    [[nodiscard]] bool allowed() const { return status == Status::Ok; }
};

// Strict scalar UTF-8. Controls and invisible/bidirectional overrides must not enter chat.
// The renderer MUST still display text as text, never as HTML or executable markup.
[[nodiscard]] inline bool ValidText(std::string_view text) {
    if (text.empty() || text.size() > 512) return false;
    std::size_t characters = 0;
    bool visible = false;
    for (std::size_t i = 0; i < text.size();) {
        const auto first = static_cast<unsigned char>(text[i]);
        std::uint32_t cp = 0;
        std::size_t width = 0;
        if (first < 0x80) {
            cp = first;
            width = 1;
        } else if (first >= 0xc2 && first <= 0xdf) {
            cp = first & 0x1f;
            width = 2;
        } else if (first >= 0xe0 && first <= 0xef) {
            cp = first & 0x0f;
            width = 3;
        } else if (first >= 0xf0 && first <= 0xf4) {
            cp = first & 0x07;
            width = 4;
        } else {
            return false;
        }
        if (i + width > text.size()) return false;
        for (std::size_t j = 1; j < width; ++j) {
            const auto b = static_cast<unsigned char>(text[i + j]);
            if ((b & 0xc0) != 0x80) return false;
            cp = (cp << 6) | (b & 0x3f);
        }
        if ((width == 2 && cp < 0x80) || (width == 3 && cp < 0x800) ||
            (width == 4 && cp < 0x10000) || cp > 0x10ffff ||
            (cp >= 0xd800 && cp <= 0xdfff)) return false;
        if (cp < 0x20 || (cp >= 0x7f && cp <= 0x9f) ||
            (cp >= 0x202a && cp <= 0x202e) || (cp >= 0x2066 && cp <= 0x2069) ||
            cp == 0x200b || cp == 0x200e || cp == 0x200f || cp == 0xfeff ||
            cp == 0x2028 || cp == 0x2029) return false;
        visible |= cp != 0x20 && cp != 0xa0;
        if (++characters > 240) return false;
        i += width;
    }
    return visible;
}

class Gate {
public:
    // Caller supplies a monotonic clock in milliseconds. Not thread-safe: run on the server's
    // serialized dispatch path (or protect Gate with the dispatch mutex).
    [[nodiscard]] Decision Route(std::string_view authenticated_sender, const Request& request,
                                 std::span<const Peer> current_roster, std::int64_t now_ms,
                                 bool global_on_this_shard) {
        const auto sender = std::find_if(current_roster.begin(), current_roster.end(),
            [&](const Peer& p) { return p.id == authenticated_sender; });
        if (sender == current_roster.end() || sender->id.empty() || !sender->online)
            return {Status::UnknownSender, {}};
        if (!sender->can_send) return {Status::Disabled, {}};
        if (!ValidText(request.text)) return {Status::InvalidText, {}};
        const Status rate = Take(sender->id, now_ms);
        if (rate != Status::Ok) return {rate, {}};

        if (request.scope == Scope::Global && !global_on_this_shard)
            return {Status::Unavailable, {}};
        if (request.scope == Scope::Team && sender->team.empty())
            return {Status::NoTeam, {}};
        if (request.scope != Scope::Global && request.scope != Scope::Team &&
            request.scope != Scope::Direct)
            return {Status::Unavailable, {}};
        if (request.scope == Scope::Direct &&
            (request.recipient.empty() || request.recipient == sender->id))
            return {Status::Unavailable, {}};

        Decision out{Status::Ok, {}};
        std::set<std::string> unique;
        for (const Peer& recipient : current_roster) {
            if (!recipient.online || recipient.id.empty() || recipient.id == sender->id ||
                recipient.blocked.contains(sender->id)) continue;
            bool eligible = false;
            switch (request.scope) {
                case Scope::Global: eligible = recipient.receive_global; break;
                case Scope::Team:
                    eligible = recipient.receive_team && recipient.team == sender->team;
                    break;
                case Scope::Direct:
                    eligible = recipient.receive_direct && recipient.id == request.recipient;
                    break;
            }
            if (eligible && unique.insert(recipient.id).second)
                out.recipients.push_back(recipient.id);
        }
        // Deliberately indistinguishable for a blocked, offline or unknown private recipient.
        if (request.scope == Scope::Direct && out.recipients.empty())
            return {Status::Unavailable, {}};
        return out;
    }

    void Clear(std::string_view account_id) { sends_.erase(std::string(account_id)); }

private:
    struct Bucket {
        std::int64_t last = 0;
        std::deque<std::int64_t> times;
    };
    // Six messages / ten seconds per authenticated sender, across all channels.
    [[nodiscard]] Status Take(const std::string& id, std::int64_t now) {
        if (now < 0) return Status::Unavailable;
        auto found = sends_.find(id);
        if (found == sends_.end()) {
            if (sends_.size() >= 4096) {
                std::erase_if(sends_, [now](const auto& pair) {
                    return now >= pair.second.last && now - pair.second.last >= 10000;
                });
                if (sends_.size() >= 4096) return Status::Capacity;
            }
            found = sends_.emplace(id, Bucket{}).first;
        }
        Bucket& bucket = found->second;
        // A clock rollback must not silently reopen a flood allowance.
        if (now < bucket.last) return Status::Unavailable;
        while (!bucket.times.empty() && now - bucket.times.front() >= 10000)
            bucket.times.pop_front();
        bucket.last = now;
        if (bucket.times.size() >= 6) return Status::RateLimited;
        bucket.times.push_back(now);
        return Status::Ok;
    }
    std::unordered_map<std::string, Bucket> sends_;
};

} // namespace BloodborneCoop::Comms
