// SPDX-FileCopyrightText: Copyright 2026 BBSC Yharnam Together contributors
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <algorithm>
#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <system_error>

namespace BbNgxPaths {
// NGX consumes wide paths, then may convert them with the C locale on Linux. Keep its path
// strings ASCII through private directory aliases; the OS resolves the original native bytes.
// Problem/provenance: Awakenchan/LanternEngine#104, 49df4762e84a259c79ceff5d4cec6963b0e7f8a0.
class Paths final {
public:
    Paths(const std::filesystem::path& runtime, const std::filesystem::path& data) {
        const auto runtime_absolute = std::filesystem::absolute(runtime);
        const auto data_absolute = std::filesystem::absolute(data);
        if (!std::filesystem::is_directory(runtime_absolute) ||
            !std::filesystem::is_directory(data_absolute)) {
            throw std::system_error(std::make_error_code(std::errc::not_a_directory),
                                    "NGX runtime/data directory is missing");
        }
#ifdef _WIN32
        runtime_ = runtime_absolute.native();
        data_ = data_absolute.native();
#else
        try {
            auto rt = runtime_absolute;
            auto dt = data_absolute;
            const auto ascii = [](const std::string& s) {
                return std::all_of(s.begin(), s.end(), [](unsigned char c) { return c < 128; });
            };
            if (!ascii(rt.native()) || !ascii(dt.native())) {
                // mkdtemp creates a unique directory with mode 0700. Do not use a caller's
                // potentially non-ASCII TMPDIR: NGX must receive ASCII even under LANG=C.
                char pattern[] = "/tmp/bbport-ngx-XXXXXX";
                const char* made = ::mkdtemp(pattern);
                if (!made) throw std::system_error(errno, std::generic_category(), "NGX aliases");
                staging_ = made;
                rt = staging_ / "runtime";
                dt = staging_ / "data";
                std::filesystem::create_directory_symlink(runtime_absolute, rt);
                std::filesystem::create_directory_symlink(data_absolute, dt);
            }
            const auto wide_ascii = [](const std::string& s) {
                return std::wstring(s.begin(), s.end());
            };
            runtime_ = wide_ascii(rt.native());
            data_ = wide_ascii(dt.native());
        } catch (...) {
            Cleanup();
            throw;
        }
#endif
    }
    Paths(const Paths&) = delete;
    Paths& operator=(const Paths&) = delete;
    ~Paths() { Cleanup(); }
    const std::wstring& Runtime() const { return runtime_; }
    const std::wstring& Data() const { return data_; }
    const std::filesystem::path& Staging() const { return staging_; }

private:
    void Cleanup() noexcept {
        if (!staging_.empty()) {
            std::error_code error;
            std::filesystem::remove_all(staging_, error); // removes aliases, never their targets
            staging_.clear();
        }
    }
    std::filesystem::path staging_;
    std::wstring runtime_, data_;
};
} // namespace BbNgxPaths
