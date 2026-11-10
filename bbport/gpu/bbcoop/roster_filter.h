// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Small allocation-bounded UTF-8 case fold for the local Hunters Online filter.
// Supports ASCII, Latin-1 capitals, Greek and Cyrillic (incl. Ё/ё); all other
// valid Unicode scalar values remain unchanged. This is deliberately NOT full
// Unicode normalization/collation, and does not change the server search API.
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>

namespace BbRoster {
[[nodiscard]] inline std::string FoldPlayerSearch(std::string_view source) {
    std::string out;
    out.reserve(source.size());
    for (std::size_t i = 0; i < source.size();) {
        const auto b0 = static_cast<std::uint8_t>(source[i]);
        std::uint32_t cp = 0;
        std::size_t length = 0;
        if (b0 < 0x80) { cp = b0; length = 1; }
        else if (b0 >= 0xC2 && b0 <= 0xDF) { cp = b0 & 0x1Fu; length = 2; }
        else if (b0 >= 0xE0 && b0 <= 0xEF) { cp = b0 & 0x0Fu; length = 3; }
        else if (b0 >= 0xF0 && b0 <= 0xF4) { cp = b0 & 0x07u; length = 4; }
        else { out.push_back(source[i++]); continue; }

        if (i + length > source.size()) {
            out.push_back(source[i++]);
            continue;
        }
        bool valid = true;
        for (std::size_t j = 1; j < length; ++j) {
            const auto b = static_cast<std::uint8_t>(source[i + j]);
            if ((b & 0xC0u) != 0x80u) { valid = false; break; }
            cp = (cp << 6) | (b & 0x3Fu);
        }
        if (!valid || (length == 2 && cp < 0x80) ||
            (length == 3 && cp < 0x800) || (length == 4 && cp < 0x10000) ||
            (cp >= 0xD800 && cp <= 0xDFFF) || cp > 0x10FFFF) {
            out.push_back(source[i++]);
            continue; // preserve malformed input rather than losing player IDs
        }
        i += length;

        if ((cp >= 'A' && cp <= 'Z') ||
            (cp >= 0x00C0 && cp <= 0x00D6) ||
            (cp >= 0x00D8 && cp <= 0x00DE) ||
            (cp >= 0x0391 && cp <= 0x03A1) ||
            (cp >= 0x03A3 && cp <= 0x03AB) ||
            (cp >= 0x0410 && cp <= 0x042F)) {
            cp += 0x20;
        } else if (cp >= 0x0400 && cp <= 0x040F) {
            cp += 0x50; // Ё, І, Ђ and other Cyrillic extensions
        } else if (cp == 0x03C2) {
            cp = 0x03C3; // Greek final sigma matches ordinary sigma
        }
        if (cp < 0x80) out.push_back(static_cast<char>(cp));
        else if (cp < 0x800) {
            out.push_back(static_cast<char>(0xC0u | (cp >> 6)));
            out.push_back(static_cast<char>(0x80u | (cp & 0x3Fu)));
        } else if (cp < 0x10000) {
            out.push_back(static_cast<char>(0xE0u | (cp >> 12)));
            out.push_back(static_cast<char>(0x80u | ((cp >> 6) & 0x3Fu)));
            out.push_back(static_cast<char>(0x80u | (cp & 0x3Fu)));
        } else {
            out.push_back(static_cast<char>(0xF0u | (cp >> 18)));
            out.push_back(static_cast<char>(0x80u | ((cp >> 12) & 0x3Fu)));
            out.push_back(static_cast<char>(0x80u | ((cp >> 6) & 0x3Fu)));
            out.push_back(static_cast<char>(0x80u | (cp & 0x3Fu)));
        }
    }
    return out;
}
[[nodiscard]] inline bool MatchesPlayerSearch(std::string_view nickname,
                                              std::string_view query) {
    return FoldPlayerSearch(nickname).find(FoldPlayerSearch(query)) != std::string::npos;
}
} // namespace BbRoster
