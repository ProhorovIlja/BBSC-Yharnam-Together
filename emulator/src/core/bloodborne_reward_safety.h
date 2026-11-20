// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace Core::Bloodborne::RewardSafety {

struct Owner {
    int slot;
    std::uint64_t generation;
    bool Valid() const { return slot >= 0 && generation != 0; }
    bool operator==(const Owner&) const = default;
};

// Native AddTradeItems is void. While delivery is ambiguous, do not issue the
// same goods request on every tick (or on a rapid rejoin).
class ReturnAttempts {
public:
    bool Begin(std::int32_t goods) {
        if (std::ranges::find(requested, goods) != requested.end()) {
            return false;
        }
        requested.push_back(goods);
        return true;
    }
    void Reset() { requested.clear(); }

private:
    std::vector<std::int32_t> requested;
};

using Time = std::chrono::steady_clock::time_point;

template <typename T>
struct Pending {
    T value;
    Time due;
    Owner owner;
};

template <typename T>
bool HasDue(const std::vector<Pending<T>>& queue, Owner owner, Time now) {
    return owner.Valid() && std::ranges::any_of(queue, [&](const Pending<T>& item) {
        return item.owner == owner && item.due <= now;
    });
}

// Call only when native item delivery is ready. A mismatched entry is never granted.
template <typename T>
std::vector<T> TakeDue(std::vector<Pending<T>>& queue, Owner owner, Time now) {
    std::vector<T> result;
    if (!owner.Valid()) {
        return result;
    }
    std::erase_if(queue, [&](const Pending<T>& item) {
        if (item.owner != owner) {
            return true;
        }
        if (item.due > now) {
            return false;
        }
        result.push_back(item.value);
        return true;
    });
    return result;
}

// Adapted to the live ledger from the bounded journal reader in PR #139.
inline constexpr std::size_t MaxLedgerBytes = 64 * 1024;

inline std::optional<std::string> ReadLedger(const std::filesystem::path& path) {
    std::error_code error;
    const auto status = std::filesystem::symlink_status(path, error);
    if (status.type() == std::filesystem::file_type::not_found &&
        (!error || error == std::errc::no_such_file_or_directory)) {
        return std::string{};
    }
    if (error || !std::filesystem::is_regular_file(status)) {
        return std::nullopt;
    }
    const auto size = std::filesystem::file_size(path, error);
    if (error || size > MaxLedgerBytes) {
        return std::nullopt;
    }
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        return std::nullopt;
    }
    std::string text(static_cast<std::size_t>(size), '\0');
    if (!in.read(text.data(), static_cast<std::streamsize>(size)) ||
        in.peek() != std::char_traits<char>::eof() || !in.eof() || in.bad()) {
        return std::nullopt;
    }
    return text;
}

// Single writer (game thread). Replace only after a successful write and close.
// This avoids truncating the last usable file, but does not fsync or acknowledge savedata.
inline bool WriteLedger(const std::filesystem::path& path, std::string_view encoded) {
    std::error_code error;
    if (encoded.size() > MaxLedgerBytes) {
        return false;
    }
    if (encoded.empty()) {
        std::filesystem::remove(path, error);
        return !error;
    }
    auto temp = path;
    temp += ".tmp";
    std::ofstream out(temp, std::ios::binary | std::ios::trunc);
    if (!out) {
        return false;
    }
    out << encoded;
    out.close();
    if (out) {
        std::filesystem::rename(temp, path, error);
        if (!error) {
            return true;
        }
    }
    std::filesystem::remove(temp, error);
    return false;
}

} // namespace Core::Bloodborne::RewardSafety
