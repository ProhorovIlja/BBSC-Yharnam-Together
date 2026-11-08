# SPDX-License-Identifier: GPL-2.0-or-later
"""B06: prove guest metadata replacement keeps previous bytes on failures.

Uses a production C++ helper extracted directly from bloodborne_flags_store.cpp,
a compiler, and synthetic small text files only. Does not read real saves.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
FLAGS = ROOT / "emulator/src/core/bloodborne_flags_store.cpp"


class GuestMetadataAtomicReplacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = FLAGS.read_text(encoding="utf-8")

    def test_all_four_progress_records_use_staging(self):
        text = self.source
        pickup = text.split("void SaveGuestProgress(", 1)[1].split("\n}", 1)[0]
        world = text.split("void SaveGuestWorldChanges()", 1)[1].split("\n}", 1)[0]
        owner = text.split("void ForgetSlotIfNewCharacter()", 1)[1].split(
            "\n// After the pickups", 1
        )[0]
        confirmed = text.split("void ConfirmGuestPickupsInOwnWorld()", 1)[1].split(
            "\n}", 1
        )[0]
        self.assertIn("ReplaceGuestMetadataFile(GuestProgressFile(),", pickup)
        self.assertIn("CommitLatestGuestWorldSnapshot(state, revision, path, text)", world)
        latest_commit = text.split("bool CommitLatestGuestWorldSnapshot(", 1)[1].split(
            "\nvoid SaveGuestWorldChanges()", 1
        )[0]
        self.assertIn("ReplaceGuestMetadataFile(path, text)", latest_commit)
        self.assertIn("ReplaceGuestMetadataFile(", owner)
        self.assertIn("GuestOwnerFile(),", owner)
        self.assertIn("ReplaceGuestMetadataFile(GuestConfirmedFile(),", confirmed)
        self.assertIn("return; // Do not clear this slot", owner)
        self.assertNotIn("std::ios::trunc", pickup + world + owner + confirmed)

    def test_production_helper_has_no_delete_then_replace_fallback(self):
        code = self.source
        fn = code.split("bool ReplaceGuestMetadataFile(", 1)[1].split(
            "\n}\n\nstd::filesystem::path GuestProgressFile()", 1
        )[0]
        self.assertIn("std::filesystem::rename(staged, path, error)", fn)
        self.assertIn("if (!written || file.fail())", fn)
        self.assertIn("std::filesystem::remove(staged, ignored)", fn)
        self.assertNotIn("std::filesystem::remove(path", fn)
        self.assertNotIn("std::filesystem::copy_file", fn)

    def test_compile_exact_cpp_replacement_and_injected_errors(self):
        text = self.source
        a = text.index("bool ReplaceGuestMetadataFile(")
        b = text.index("\n}\n\nstd::filesystem::path GuestProgressFile()", a) + 2
        helper = text[a:b]
        compiler = shutil.which("g++") or shutil.which("c++")
        if compiler is None:
            self.skipTest("C++20 compiler unavailable")
        # Only fmt::format for the temporary name is stubbed; the filesystem
        # function and its error paths are compiled unchanged from production.
        fixture = r"""
#include <atomic>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <string_view>
#include <system_error>
#include <unistd.h>
using u64 = std::uint64_t;
namespace fmt {
    template <typename A, typename B>
    std::string format(const char*, A a, B b) {
        return ".tmp-" + std::to_string(a) + "-" + std::to_string(b);
    }
}
// PRODUCTION_HELPER
#define CHECK(c) do { if (!(c)) return __LINE__; } while (0)
std::string read(const std::filesystem::path& p) {
    std::ifstream input(p, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(input), {});
}
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    namespace fs = std::filesystem;
    const fs::path root{argv[1]};
    const fs::path p = root / "hunter_progress.txt";
    { std::ofstream original(p); original << "old progress"; }
    CHECK(read(p) == "old progress");
    CHECK(ReplaceGuestMetadataFile(p, "new progress"));
    CHECK(read(p) == "new progress");
    CHECK(ReplaceGuestMetadataFile(p, ""));
    CHECK(read(p).empty());
    CHECK(ReplaceGuestMetadataFile(p, "keep me"));
    CHECK(read(p) == "keep me");
    // Missing parent: staging fails; an already present record is unaffected.
    CHECK(!ReplaceGuestMetadataFile(root / "missing" / "world.txt", "lost"));
    CHECK(read(p) == "keep me");
    // Destination is a nonempty directory. Staging succeeds, but atomic
    // rename must fail; the old destination's contents must not be removed.
    const fs::path dest_dir = root / "directory-destination";
    fs::create_directory(dest_dir);
    { std::ofstream existing(dest_dir / "flag.txt"); existing << "original"; }
    CHECK(!ReplaceGuestMetadataFile(dest_dir, "should never overwrite"));
    CHECK(fs::is_directory(dest_dir));
    CHECK(read(dest_dir / "flag.txt") == "original");
    CHECK(read(p) == "keep me");
    // Both failed operations must clean their own temp data, even if the
    // destination cannot be atomically replaced.
    for (const auto& entry : fs::directory_iterator(root)) {
        CHECK(entry.path().filename().string().find(".tmp-") == std::string::npos);
    }
    return 0;
}
"""
        fixture = fixture.replace("// PRODUCTION_HELPER", helper)
        with tempfile.TemporaryDirectory(prefix="bbsc-b06-") as tmp:
            path = Path(tmp) / "atomic.cpp"
            exe = Path(tmp) / "atomic"
            work = Path(tmp) / "synthetic-user"
            work.mkdir()
            path.write_text(fixture, encoding="utf-8")
            build = subprocess.run(
                [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                 str(path), "-o", str(exe)],
                capture_output=True, text=True, timeout=40
            )
            self.assertEqual(build.returncode, 0, build.stderr[-2500:])
            run = subprocess.run([str(exe), str(work)], capture_output=True,
                                 text=True, timeout=10)
            self.assertEqual(run.returncode, 0,
                             f"production C++ fixture line {run.returncode}: {run.stderr}")


if __name__ == "__main__":
    unittest.main()
