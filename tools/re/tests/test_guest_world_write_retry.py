# SPDX-License-Identifier: GPL-2.0-or-later
"""B08: production C++ guest-world retry on worker idle.

Tests only synthetic metadata files and injected rename errors. Compiles the
exact B06 staged writer and B07/B08 revision/idle-retry helpers. No game data.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
FLAGS = ROOT / "emulator/src/core/bloodborne_flags_store.cpp"
RE = ROOT / "emulator/src/core/bloodborne_re.cpp"
HEADER = ROOT / "emulator/src/core/bloodborne_re_internal.h"


class GuestWorldWriteRetry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = FLAGS.read_text(encoding="utf-8")

    def test_worker_idle_wiring_and_bounded_retry_policy(self):
        code = self.source
        retry = code.split("size_t RetryFailedWorldFileWrites() {", 1)[1].split(
            "\nvoid SaveGuestWorldChanges()", 1
        )[0]
        self.assertIn("if (attempts >= 2)", retry)
        self.assertIn("state->retry_revision !=", retry)
        self.assertIn("state->newest_revision.load(std::memory_order_acquire)", retry)
        self.assertIn("state->retry_text.reset();", retry)
        self.assertIn("state->retry_failures = std::min<u32>(state->retry_failures + 1, 5)", retry)
        self.assertIn("ReplaceGuestMetadataFile(path, *state->retry_text)", retry)
        writer = code.split("void SaveGuestWorldChanges() {", 1)[1].split(
            "\nvoid ForgetGuestWorldChanges()", 1
        )[0]
        self.assertIn("CommitLatestGuestWorldSnapshot(state, revision, path, text)", writer)
        self.assertIn("Coop::CoopOffMain().Post([] {})", writer)
        self.assertIn("RetryFailedGuestWorldWritesOnWorker()", code)
        self.assertIn("void RetryFailedGuestWorldWritesOnWorker();",
                      HEADER.read_text(encoding="utf-8"))
        re_code = RE.read_text(encoding="utf-8")
        self.assertIn("ReadOffMainFile();\n                                                    RetryFailedGuestWorldWritesOnWorker();",
                      re_code)

    def test_compile_failed_write_then_idle_recovery_and_supersession(self):
        code = self.source
        a = code.index("bool ReplaceGuestMetadataFile(")
        b = code.index("\n}\n\nstd::filesystem::path GuestProgressFile()", a) + 2
        writer = code[a:b]
        a = code.index("struct GuestWorldWriteState {")
        b = code.index("\nvoid SaveGuestWorldChanges() {", a)
        guard_and_retry = code[a:b]
        compiler = shutil.which("g++") or shutil.which("c++")
        if not compiler:
            self.skipTest("C++20 compiler unavailable")
        fixture = r"""
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>
#include <unistd.h>
using u64 = std::uint64_t;
using u32 = std::uint32_t;
namespace fmt {
    template <typename A, typename B>
    std::string format(const char*, A a, B b) {
        return ".tmp-" + std::to_string(a) + "-" + std::to_string(b);
    }
}
// EXACT_WRITER
// EXACT_GUARD_AND_RETRY
#define CHECK(c) do { if (!(c)) return __LINE__; } while (0)
std::string read(const std::filesystem::path& p) {
    std::ifstream file(p, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(file), {});
}
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    namespace fs = std::filesystem;
    const fs::path root{argv[1]};
    const fs::path blocked = root / "hunter-world-1";
    fs::create_directory(blocked);
    { std::ofstream sentinel(blocked / "sentinel"); sentinel << "stay"; }
    const auto state = GuestWorldWriteStateFor(blocked);
    const u64 revision = state->newest_revision.fetch_add(1) + 1;
    CHECK(!CommitLatestGuestWorldSnapshot(state, revision, blocked, "new flags"));
    CHECK(state->retry_revision == revision);
    CHECK(state->retry_text && *state->retry_text == "new flags");
    CHECK(state->retry_failures == 1);
    CHECK(read(blocked / "sentinel") == "stay");
    // Force time forward without actually sleeping, keeping tests quick.
    state->retry_after = std::chrono::steady_clock::time_point{};
    const auto before = std::chrono::steady_clock::now();
    CHECK(RetryFailedWorldFileWrites() == 0); // Still blocked.
    CHECK(state->retry_failures == 2);
    CHECK(state->retry_after > before);
    CHECK(read(blocked / "sentinel") == "stay");

    // Recover the destination and retry the same latest snapshot.
    fs::remove(blocked / "sentinel");
    fs::remove(blocked);
    state->retry_after = std::chrono::steady_clock::time_point{};
    CHECK(RetryFailedWorldFileWrites() == 1);
    CHECK(read(blocked) == "new flags");
    CHECK(!state->retry_text && state->retry_revision == 0);
    CHECK(RetryFailedWorldFileWrites() == 0);

    // Superseded failure must never replay after a newer successful write.
    const fs::path superseded = root / "hunter-world-2";
    fs::create_directory(superseded);
    const auto state2 = GuestWorldWriteStateFor(superseded);
    const u64 old_rev = state2->newest_revision.fetch_add(1) + 1;
    CHECK(!CommitLatestGuestWorldSnapshot(state2, old_rev, superseded, "obsolete"));
    const u64 new_rev = state2->newest_revision.fetch_add(1) + 1;
    CHECK(new_rev > old_rev);
    fs::remove(superseded);
    CHECK(CommitLatestGuestWorldSnapshot(state2, new_rev, superseded, "correct world"));
    state2->retry_after = std::chrono::steady_clock::time_point{};
    CHECK(RetryFailedWorldFileWrites() == 0);
    CHECK(read(superseded) == "correct world");
    CHECK(!state2->retry_text);

    // Another failure is invalidated by a newer revision even if newer
    // write itself has not executed. An older snapshot is never resurrected.
    const fs::path obsolete = root / "hunter-world-3";
    fs::create_directory(obsolete);
    const auto state3 = GuestWorldWriteStateFor(obsolete);
    const u64 first = state3->newest_revision.fetch_add(1) + 1;
    CHECK(!CommitLatestGuestWorldSnapshot(state3, first, obsolete, "first"));
    (void)state3->newest_revision.fetch_add(1);
    state3->retry_after = std::chrono::steady_clock::time_point{};
    CHECK(RetryFailedWorldFileWrites() == 0);
    CHECK(!state3->retry_text && state3->retry_revision == 0);
    CHECK(fs::is_directory(obsolete));
    return 0;
}
"""
        fixture = fixture.replace("// EXACT_WRITER", writer).replace(
            "// EXACT_GUARD_AND_RETRY", guard_and_retry
        )
        with tempfile.TemporaryDirectory(prefix="bbsc-b08-") as td:
            code_path = Path(td) / "retry.cpp"
            binary = Path(td) / "retry"
            work = Path(td) / "synthetic"
            work.mkdir()
            code_path.write_text(fixture, encoding="utf-8")
            built = subprocess.run(
                [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-pthread", str(code_path), "-o", str(binary)],
                text=True, capture_output=True, timeout=40
            )
            self.assertEqual(built.returncode, 0, built.stderr[-3000:])
            run = subprocess.run([str(binary), str(work)], capture_output=True,
                                 text=True, timeout=10)
            self.assertEqual(run.returncode, 0,
                             f"compiled B08 fixture line {run.returncode}: {run.stderr}")


if __name__ == "__main__":
    unittest.main()
