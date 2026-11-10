// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// B28: the guest's own world must be written successfully BEFORE the
// host/team world's flag blocks are applied to the loaded save. Keep this
// small file operation free of game/emulator dependencies for Windows/Linux
// regression tests. The rename changes one destination at once; it does not
// claim an OS crash-durability guarantee without a directory fsync.
#include <array>
#include <algorithm>
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

// B64: non-destructive source snapshot archive for future home-world migration.
// This is intentionally NOT "rename old then delete source on failure".
// A filename picked by a caller is considered occupied if it exists or is a
// dangling symlink. It is NEVER overwritten. Caller chooses a new versioned
// name and only treats true as a verified archive. The source remains unchanged
// even on success. A crash during the copy can leave an incomplete *candidate*
// but cannot damage the original; callers must NEVER auto-restore an unverified
// candidate. This protects ordinary process errors, not OS power-loss
// durability (no cross-platform file/directory fsync guarantee).
inline bool CopyVerifiedWorldArchiveNoClobber(const std::filesystem::path& source,
                                             const std::filesystem::path& archive) {
    namespace fs = std::filesystem;
    if (source == archive || source.parent_path() != archive.parent_path()) {
        return false;
    }
    std::error_code err;
    const fs::file_status original = fs::symlink_status(source, err);
    if (err || !fs::is_regular_file(original)) return false; // reject symlinks
    err.clear();
    const fs::file_status target = fs::symlink_status(archive, err);
    if (err && err != std::errc::no_such_file_or_directory) return false;
    if (target.type() != fs::file_type::not_found) return false;
    err.clear();
    const std::uintmax_t size = fs::file_size(source, err);
    if (err || size == 0 || size > 64u * 1024u * 1024u) return false;
    err.clear();
    if (!fs::copy_file(source, archive, fs::copy_options::none, err) || err) {
        return false; // source unchanged, no pre-existing target touched
    }
    // Verify by streaming, rather than assuming a successful copy means the
    // whole file was written. Never delete or rename the actual source.
    const auto verify = [&] {
        std::ifstream old_file{source, std::ios::binary};
        std::ifstream new_file{archive, std::ios::binary};
        if (!old_file || !new_file) return false;
        std::array<char, 4096> a{}, b{};
        std::uintmax_t read = 0;
        do {
            old_file.read(a.data(), static_cast<std::streamsize>(a.size()));
            new_file.read(b.data(), static_cast<std::streamsize>(b.size()));
            const auto n = old_file.gcount();
            if (n != new_file.gcount() || old_file.bad() || new_file.bad()) return false;
            if (!std::equal(a.begin(), a.begin() + n, b.begin())) return false;
            read += static_cast<std::uintmax_t>(n);
            if (n == 0) break;
        } while (true);
        return read == size;
    };
    err.clear();
    const bool valid_size = fs::file_size(archive, err) == size && !err;
    if (!valid_size || !verify()) {
        // It is OUR just-created copy, not an existing named backup.
        std::error_code cleanup;
        fs::remove(archive, cleanup);
        return false;
    }
    return true;
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
