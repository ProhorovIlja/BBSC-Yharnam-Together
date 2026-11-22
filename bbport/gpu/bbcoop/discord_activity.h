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

// Decode JSON string values fully, including Unicode-escaped hunter names.
// This local IPC reader is not a generic JSON protocol parser.
namespace FieldDetail {

inline bool Hex4(const std::string& json, std::size_t& at, std::uint32_t& value) {
    value = 0;
    for (int i = 0; i < 4; ++i) {
        if (at == json.size()) return false;
        const char c = json[at++];
        const int digit = c >= '0' && c <= '9' ? c - '0' :
                          c >= 'a' && c <= 'f' ? c - 'a' + 10 :
                          c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1;
        if (digit < 0) return false;
        value = (value << 4) | static_cast<std::uint32_t>(digit);
    }
    return true;
}

inline void Utf8(std::string& out, std::uint32_t cp) {
    if (cp <= 0x7F) {
        out.push_back(static_cast<char>(cp));
    } else if (cp <= 0x7FF) {
        out.push_back(static_cast<char>(0xC0 | (cp >> 6)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else if (cp <= 0xFFFF) {
        out.push_back(static_cast<char>(0xE0 | (cp >> 12)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else {
        out.push_back(static_cast<char>(0xF0 | (cp >> 18)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 12) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    }
}

inline bool Quoted(const std::string& json, std::size_t& at, std::string& out) {
    if (at == json.size() || json[at++] != '"') return false;
    while (at < json.size()) {
        const char c = json[at++];
        if (c == '"') return true;
        if (static_cast<unsigned char>(c) < 0x20) return false;
        if (c != '\\') {
            out.push_back(c);
            continue;
        }
        if (at == json.size()) return false;
        const char escaped = json[at++];
        switch (escaped) {
        case '"': case '\\': case '/': out.push_back(escaped); break;
        case 'b': out.push_back('\b'); break;
        case 'f': out.push_back('\f'); break;
        case 'n': out.push_back('\n'); break;
        case 'r': out.push_back('\r'); break;
        case 't': out.push_back('\t'); break;
        case 'u': {
            std::uint32_t cp = 0;
            if (!Hex4(json, at, cp)) return false;
            if (cp >= 0xD800 && cp <= 0xDBFF) {
                if (at + 2 > json.size() || json[at] != '\\' || json[at + 1] != 'u') {
                    return false;
                }
                at += 2;
                std::uint32_t low = 0;
                if (!Hex4(json, at, low) || low < 0xDC00 || low > 0xDFFF) return false;
                cp = 0x10000 + ((cp - 0xD800) << 10) + (low - 0xDC00);
            } else if (cp >= 0xDC00 && cp <= 0xDFFF) {
                return false;
            }
            Utf8(out, cp);
            break;
        }
        default: return false;
        }
    }
    return false;
}

inline bool Whitespace(char c) {
    return c == ' ' || c == '\t' || c == '\r' || c == '\n';
}
} // namespace FieldDetail

// Reads a string-valued JSON object field after the from offset.
// Unlike substring matching, it handles legal spacing and never treats an
// escaped field-looking sequence inside a string as a real key.
inline std::string Field(const std::string& json, const std::string& key, std::size_t from = 0) {
    std::size_t at = 0;
    while (at < json.size()) {
        if (json[at] != '"') {
            ++at;
            continue;
        }
        const std::size_t start = at;
        std::string name;
        if (!FieldDetail::Quoted(json, at, name)) return {};
        std::size_t separator = at;
        while (separator < json.size() && FieldDetail::Whitespace(json[separator])) ++separator;
        if (start < from || separator == json.size() || json[separator] != ':' || name != key) {
            continue;
        }
        ++separator;
        while (separator < json.size() && FieldDetail::Whitespace(json[separator])) ++separator;
        std::string value;
        return FieldDetail::Quoted(json, separator, value) ? value : std::string{};
    }
    return {};
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
