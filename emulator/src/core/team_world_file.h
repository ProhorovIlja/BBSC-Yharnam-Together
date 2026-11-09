// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// B28: the guest's own world must be written successfully BEFORE the
// host/team world's flag blocks are applied to the loaded save. Keep this
// small file operation free of game/emulator dependencies for Windows/Linux
// regression tests. The rename changes one destination at once; it does not
// claim an OS crash-durability guarantee without a directory fsync.
#include <filesystem>
#include <fstream>
#include <iterator>
#include <limits>
#include <optional>
#include <string>
#include <string_view>
#include <system_error>

namespace BloodborneCoop::TeamWorldFile {

inline bool WriteWholeFileChecked(const std::filesystem::path& dest, std::string_view text) {
    if (text.size() > static_cast<size_t>(std::numeric_limits<std::streamsize>::max())) {
        return false;
    }
    std::filesystem::path partial = dest;
    partial += ".part";

    std::ofstream file{partial, std::ios::binary | std::ios::trunc};
    if (!file.is_open()) {
        return false;
    }
    file.write(text.data(), static_cast<std::streamsize>(text.size()));
    file.flush();
    const bool written = file.good();
    file.close();
    if (!written || !file.good()) {
        std::error_code cleanup_error;
        std::filesystem::remove(partial, cleanup_error);
        return false;
    }

    std::error_code move_error;
    std::filesystem::rename(partial, dest, move_error);
    if (move_error) {
        std::error_code cleanup_error;
        std::filesystem::remove(partial, cleanup_error);
        return false;
    }
    return true;
}

// Missing/unreadable originals cannot be treated as an empty, valid snapshot.
// Callers distinguish *verified absent* with filesystem::exists(path, error)
// before calling this function. A present but broken backup is not expendable.
inline std::optional<std::string> ReadExistingFileChecked(const std::filesystem::path& path) {
    std::ifstream file{path, std::ios::binary};
    if (!file.is_open()) {
        return std::nullopt;
    }
    std::string bytes{std::istreambuf_iterator<char>{file}, std::istreambuf_iterator<char>{}};
    if (file.bad()) {
        return std::nullopt;
    }
    return bytes;
}

// A restore is only complete when its temporary private-world file has
// actually been retired. A failed delete must leave it available to retry.
// Already-absent files are an idempotent success.
inline bool RemoveWorldFileChecked(const std::filesystem::path& path) {
    std::error_code error;
    const bool removed = std::filesystem::remove(path, error);
    if (error) {
        return false;
    }
    if (removed) {
        return true;
    }
    const bool still_exists = std::filesystem::exists(path, error);
    return !error && !still_exists;
}

} // namespace BloodborneCoop::TeamWorldFile
