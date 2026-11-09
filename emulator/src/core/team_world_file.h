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
#include <limits>
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

} // namespace BloodborneCoop::TeamWorldFile
