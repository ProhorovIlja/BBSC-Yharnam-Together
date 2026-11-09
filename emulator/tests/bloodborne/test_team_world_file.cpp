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
using BloodborneCoop::TeamWorldFile::ReadExistingFileChecked;
using BloodborneCoop::TeamWorldFile::RemoveWorldFileChecked;

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
    CHECK(ReadExistingFileChecked(personal).has_value() &&
          *ReadExistingFileChecked(personal) == first);
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
    CHECK(!ReadExistingFileChecked(missing).has_value());
    CHECK(RemoveWorldFileChecked(missing)); // missing is idempotent

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
    CHECK(*ReadExistingFileChecked(personal) == next);
    fs::remove(partial);

    // A retry after the obstruction goes away must work for the same slot.
    CHECK(WriteWholeFileChecked(personal, "safe-on-retry"));
    CHECK(Read(personal) == "safe-on-retry");
    CHECK(*ReadExistingFileChecked(personal) == "safe-on-retry");

    // A present but empty/corrupt backup is NOT a missing file. Production
    // has to parse it before allowing another guest/invader world switch.
    const fs::path empty = root / "invasion_home_empty";
    CHECK(WriteWholeFileChecked(empty, ""));
    const auto empty_content = ReadExistingFileChecked(empty);
    CHECK(empty_content && empty_content->empty());
    CHECK(fs::exists(empty));

    // Refuse to claim restoration is complete if an existing path cannot be
    // retired (e.g. nonempty directory from damaged user state).
    const fs::path blocked_delete = root / "invasion_home_blocked";
    fs::create_directory(blocked_delete);
    { std::ofstream marker{blocked_delete / "original-flags"}; marker << "preserve"; }
    CHECK(!RemoveWorldFileChecked(blocked_delete));
    CHECK(fs::exists(blocked_delete / "original-flags"));
    CHECK(Read(blocked_delete / "original-flags") == "preserve");
    fs::remove_all(blocked_delete);

    // A completed restore must really remove its backup, and can safely be
    // retried after the file already disappeared.
    CHECK(RemoveWorldFileChecked(personal));
    CHECK(!fs::exists(personal));
    CHECK(RemoveWorldFileChecked(personal));
    CHECK(RemoveWorldFileChecked(empty));

    fs::remove_all(root);
    std::cout << "B28_REAL_PRODUCTION_PERSONAL_WORLD_FILE_WRITE_GATE_PASS\n";
    return 0;
}
