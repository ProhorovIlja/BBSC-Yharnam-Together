// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// B68 offline-only append-only key-item debt revision staging. Never called by
// live game/save hooks before identity and grant-acknowledgement wiring exists.
// This protects against ordinary process errors, NOT OS power loss (no
// portable directory fsync), and is not a multi-file atomic save transaction.

#include <algorithm>
#include <array>
#include <charconv>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <optional>
#include <string>
#include <string_view>
#include <system_error>

namespace BloodborneCoop::PhantomKeyLedgerFile {

struct Revision {
    unsigned slot = 0;
    std::string character_fingerprint; // 32 hex ASCII bytes, not a player name
    std::uint64_t sequence = 0;
    std::string debt; // canonical EncodeOwedKeyItems or tombstone ""
    bool operator==(const Revision&) const = default;
};

inline bool Valid(const Revision& r) {
    if (r.slot >= 64 || r.sequence == 0 || r.character_fingerprint.size() != 32 ||
        r.debt.size() > 64 * 1024) return false;
    return std::all_of(r.character_fingerprint.begin(), r.character_fingerprint.end(),
                       [](unsigned char c) {
                           return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
                       });
}

inline std::uint64_t Checksum(std::string_view str) {
    std::uint64_t result = 14695981039346656037ull;
    for (unsigned char ch : str) {
        result ^= ch;
        result *= 1099511628211ull;
    }
    return result;
}

inline std::string Name(const Revision& r) {
    return "slot" + std::to_string(r.slot) + "-" + r.character_fingerprint +
           "-r" + std::to_string(r.sequence);
}

inline std::string Encode(const Revision& r) {
    return "BLOODBORNE_OWED_V1\n" + std::to_string(r.slot) + "\n" +
           r.character_fingerprint + "\n" + std::to_string(r.sequence) + "\n" +
           std::to_string(r.debt.size()) + "\n" +
           std::to_string(Checksum(r.debt)) + "\n" + r.debt;
}

inline std::optional<std::uint64_t> UInt(std::string_view str) {
    if (str.empty()) return std::nullopt;
    std::uint64_t value = 0;
    auto [it, error] = std::from_chars(str.data(), str.data() + str.size(), value);
    if (error != std::errc{} || it != str.data() + str.size()) return std::nullopt;
    return value;
}

inline std::optional<Revision> Decode(std::string_view text) {
    if (text.size() > 70 * 1024) return std::nullopt;
    const auto line = [&text]() -> std::optional<std::string_view> {
        const auto i = text.find('\n');
        if (i == text.npos) return std::nullopt;
        const auto first = text.substr(0, i);
        text.remove_prefix(i + 1);
        return first;
    };
    if (line() != "BLOODBORNE_OWED_V1") return std::nullopt;
    const auto slot = line();
    const auto fingerprint = line();
    const auto seq = line();
    const auto length = line();
    const auto checksum = line();
    if (!slot || !fingerprint || !seq || !length || !checksum) return std::nullopt;
    const auto nslot = UInt(*slot), nseq = UInt(*seq);
    const auto nlen = UInt(*length), nhash = UInt(*checksum);
    if (!nslot || !nseq || !nlen || !nhash || *nlen != text.size() ||
        *nslot >= 64) return std::nullopt;
    Revision r{static_cast<unsigned>(*nslot), std::string(*fingerprint),
               *nseq, std::string(text)};
    if (!Valid(r) || Checksum(r.debt) != *nhash || Encode(r) !=
        "BLOODBORNE_OWED_V1\n" + std::string(*slot) + "\n" +
        std::string(*fingerprint) + "\n" + std::string(*seq) + "\n" +
        std::string(*length) + "\n" + std::string(*checksum) + "\n" + r.debt) {
        return std::nullopt;
    }
    return r;
}

inline std::optional<Revision> ReadReady(const std::filesystem::path& dir) {
    namespace fs = std::filesystem;
    std::error_code err;
    if (dir.extension() != ".ready" || !fs::is_directory(fs::symlink_status(dir, err)) ||
        err) return std::nullopt;
    const auto file = dir / "ledger.txt";
    err.clear();
    if (!fs::is_regular_file(fs::symlink_status(file, err)) || err) return std::nullopt;
    const auto size = fs::file_size(file, err);
    if (err || size > 70 * 1024) return std::nullopt;
    std::ifstream in{file, std::ios::binary};
    if (!in) return std::nullopt;
    const std::string data{std::istreambuf_iterator<char>{in},
                           std::istreambuf_iterator<char>{}};
    if (in.bad()) return std::nullopt;
    auto parsed = Decode(data);
    if (!parsed || dir.filename() != Name(*parsed) + ".ready") return std::nullopt;
    return parsed;
}

inline bool CreateNewRevision(const std::filesystem::path& root, const Revision& r) {
    namespace fs = std::filesystem;
    if (!Valid(r)) return false;
    std::error_code err;
    if (!fs::is_directory(fs::symlink_status(root, err)) || err) return false;
    const auto lock = root / ".writer.lock";
    // Atomic mkdir is an exclusive writer marker; a stale lock blocks until
    // manual recovery, never an automatic delete after a crash.
    err.clear();
    if (!fs::create_directory(lock, err) || err) return false;
    const auto release = [&] {
        std::error_code ignored;
        fs::remove(lock, ignored);
    };
    const std::string name = Name(r);
    const auto pending = root / (name + ".pending");
    const auto ready = root / (name + ".ready");
    err.clear();
    const bool ready_exists = fs::exists(ready, err);
    if (err || ready_exists) { release(); return false; }
    err.clear();
    if (!fs::create_directory(pending, err) || err) { release(); return false; }
    bool success = false;
    {
        const std::string data = Encode(r);
        std::ofstream out{pending / "ledger.txt", std::ios::binary | std::ios::trunc};
        if (out) {
            out.write(data.data(), static_cast<std::streamsize>(data.size()));
            out.flush();
            success = out.good();
            out.close();
            success = success && out.good();
        }
        if (success) {
            std::ifstream in{pending / "ledger.txt", std::ios::binary};
            const std::string check{std::istreambuf_iterator<char>{in},
                                    std::istreambuf_iterator<char>{}};
            success = !in.bad() && Decode(check) == std::optional{r};
        }
        if (success) {
            err.clear();
            fs::rename(pending, ready, err);
            success = !err && ReadReady(ready) == std::optional{r};
        }
    }
    if (!success) {
        // Remove only this freshly created revision candidate, never an
        // older .ready or the underlying game save. An unexpected .ready
        // is not automatically touched.
        err.clear();
        fs::remove_all(pending, err);
    }
    release();
    return success;
}

} // namespace BloodborneCoop::PhantomKeyLedgerFile
