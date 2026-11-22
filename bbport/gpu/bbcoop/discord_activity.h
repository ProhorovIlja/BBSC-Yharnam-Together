// SPDX-FileCopyrightText: Copyright 2026 CLS_AMG
// SPDX-License-Identifier: GPL-2.0-or-later

// What the Discord status says and reads (discord_status.cpp), without a pipe: JSON text, a
// message's fields, and the secret a friend joins with.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

namespace DiscordActivity {

// Local Discord RPC packets are length-prefixed by an untrusted 32-bit field.
// The app's join/activity messages are small; refuse unusually large frames
// before allocation. This is OUR 1 MiB policy, not a claimed Discord limit.
constexpr std::uint32_t MaxIpcPayloadBytes = 1u << 20;
inline bool ValidIpcFrame(std::uint32_t opcode, std::uint32_t bytes) {
    return opcode <= 4 && bytes <= MaxIpcPayloadBytes;
}

inline std::string Json(const std::string& text) {
    std::string out = "\"";
    for (const char c : text) {
        if (c == '"' || c == '\\') {
            out += '\\';
            out += c;
        } else if (static_cast<unsigned char>(c) < 0x20) {
            out += ' ';
        } else {
            out += c;
        }
    }
    return out + '"';
}

// The text value of `"key":"..."` after `from` in a Discord message, "" if none.
inline std::string Field(const std::string& json, const std::string& key, std::size_t from = 0) {
    const std::string tag = "\"" + key + "\":\"";
    const std::size_t at = json.find(tag, from);
    if (at == std::string::npos) {
        return {};
    }
    std::string out;
    for (std::size_t i = at + tag.size(); i < json.size() && json[i] != '"'; ++i) {
        if (json[i] == '\\' && i + 1 < json.size()) {
            ++i;
        }
        out += json[i];
    }
    return out;
}

// The secret to join a team with room: its code ("c:", the leader has it), else its id ("t:")
// while it is listed; nothing for a full team or an invite-only one a member cannot hand out.
inline std::string JoinSecret(const char* code, const char* team, int join, int invite_only,
                              int members, int size) {
    if (members >= size) {
        return {};
    }
    if (code[0] != '\0') {
        return std::string{"c:"} + code;
    }
    return join != invite_only ? std::string{"t:"} + team : std::string{};
}

} // namespace DiscordActivity
