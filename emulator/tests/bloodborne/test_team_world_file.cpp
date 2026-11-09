// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
// B28: compile the exact production file writer on Linux AND Windows. The
// caller-side gate is checked separately against bloodborne_server_world.cpp.
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include "core/team_world_file.h"

namespace fs = std::filesystem;
using BloodborneCoop::TeamWorldFile::WriteWholeFileChecked;

#define CHECK(condition) do { if (!(condition)) { \
    std::cerr << "B28_CHECK_FAILED line " << __LINE__ << ": " #condition << '\n'; \
    return 1; \
} } while (false)

std::string Read(const fs::path& path) {
    std::ifstream file(path, std::ios::binary);
    return {std::istreambuf_iterator<char>{file}, {}};
}

int main() {
    const auto token = std::chrono::steady_clock::now().time_since_epoch().count();
    const fs::path root = fs::temp_directory_path() /
                          ("bbsc-b28-guest-world-" + std::to_string(token));
    fs::create_directories(root);
    const fs::path personal = root / "personal_world_1";
    const std::string first("guest-world\0own-flags", 21);
    CHECK(WriteWholeFileChecked(personal, first));
    CHECK(Read(personal) == first);
    CHECK(!fs::exists(fs::path(personal.string() + ".part")));

    // Updating a real existing slot must replace it without a torn file,
    // including on Windows. The previous data must never survive partially.
    const std::string next = "guest-world-boss-alive-and-own-lamps";
    CHECK(WriteWholeFileChecked(personal, next));
    CHECK(Read(personal) == next);
    CHECK(!fs::exists(fs::path(personal.string() + ".part")));

    // Missing parent: the caller must see failure, never assume success.
    const fs::path missing = root / "does-not-exist" / "world";
    CHECK(!WriteWholeFileChecked(missing, "unsafe"));
    CHECK(!fs::exists(missing));

    // An unwriteable/invalid staging path must NOT destroy the current
    // snapshot or allow the caller to switch to the borrowed team's state.
    const fs::path partial = fs::path(personal.string() + ".part");
    fs::create_directory(partial);
    bool applied_team_flags = false;
    if (WriteWholeFileChecked(personal, "new-own-world")) {
        applied_team_flags = true;
    }
    CHECK(!applied_team_flags);
    CHECK(Read(personal) == next);
    fs::remove(partial);

    // A retry after the obstruction goes away must work for the same slot.
    CHECK(WriteWholeFileChecked(personal, "safe-on-retry"));
    CHECK(Read(personal) == "safe-on-retry");

    fs::remove_all(root);
    std::cout << "B28_REAL_PRODUCTION_PERSONAL_WORLD_FILE_WRITE_GATE_PASS\n";
    return 0;
}
