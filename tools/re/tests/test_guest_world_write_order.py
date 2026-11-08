# SPDX-License-Identifier: GPL-2.0-or-later
"""B07 regression: a delayed world-file worker must not overwrite a newer fallback.

Compile the real production C++ per-file revision and commit functions, and
the B06 staged file writer, with synthetic file paths. No game dump, save,
network account, or complete client compilation is involved.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
FLAGS = ROOT / "emulator/src/core/bloodborne_flags_store.cpp"


class GuestWorldWriteOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = FLAGS.read_text(encoding="utf-8")

    def test_worker_and_queue_full_fallback_share_revision_fence(self):
        code = self.code
        body = code.split("void SaveGuestWorldChanges() {", 1)[1].split(
            "\nvoid ForgetGuestWorldChanges()", 1
        )[0]
        self.assertIn("GuestWorldWriteStateFor(path)", body)
        self.assertIn("newest_revision.fetch_add(1, std::memory_order_acq_rel)", body)
        self.assertIn("CommitLatestGuestWorldSnapshot(state, revision, path, text)", body)
        self.assertIn("!Coop::CoopOffMain().Post(write)", body)
        self.assertIn("write();", body)
        self.assertLess(body.index("newest_revision.fetch_add("),
                        body.index("Coop::CoopOffMain().Post(write)"))

    def test_per_path_commits_and_atomic_staging_are_serialized(self):
        text = self.code
        idx = text.index("struct GuestWorldWriteState {")
        end = text.index("void SaveGuestWorldChanges() {", idx)
        part = text[idx:end]
        self.assertIn("std::map<std::filesystem::path, std::shared_ptr<GuestWorldWriteState>>", part)
        self.assertIn("std::scoped_lock lock{guest_world_writer_index_mutex}", part)
        self.assertIn("std::scoped_lock lock{state->commit_mutex}", part)
        self.assertLess(part.index("std::scoped_lock lock{state->commit_mutex}"),
                        part.index("ReplaceGuestMetadataFile(path, text);"))
        self.assertIn("newest_revision.load(std::memory_order_acquire) != revision", part)
        self.assertNotIn("std::filesystem::remove(path", part)

    def test_compile_production_cpp_and_reordered_snapshots(self):
        text = self.code
        a = text.index("bool ReplaceGuestMetadataFile(")
        b = text.index("\n}\n\nstd::filesystem::path GuestProgressFile()", a) + 2
        real_writer = text[a:b]
        a = text.index("struct GuestWorldWriteState {")
        b = text.index("\nvoid SaveGuestWorldChanges() {", a)
        real_guard = text[a:b]
        self.assertIn("CommitLatestGuestWorldSnapshot(", real_guard)
        compiler = shutil.which("g++") or shutil.which("c++")
        if compiler is None:
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
namespace fmt {
    template <class A, class B>
    std::string format(const char*, A a, B b) {
        return ".tmp-" + std::to_string(a) + "-" + std::to_string(b);
    }
}
// EXACT_PRODUCTION_WRITER
// EXACT_PRODUCTION_FENCE
#define CHECK(cond) do { if (!(cond)) return __LINE__; } while (0)
std::string read(const std::filesystem::path& p) {
    std::ifstream stream(p, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(stream), {});
}
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    namespace fs = std::filesystem;
    const fs::path root{argv[1]};
    const fs::path slot1 = root / "hunter-slot-1.world";
    const fs::path slot2 = root / "hunter-slot-2.world";
    const auto s1 = GuestWorldWriteStateFor(slot1);
    const auto s2 = GuestWorldWriteStateFor(slot2);
    CHECK(s1 && s2 && s1 != s2);
    CHECK(s1 == GuestWorldWriteStateFor(slot1)); // Stable guard for same path.

    // Worker accepted old snapshot, but the new snapshot ran synchronously
    // because the worker queue filled. A delayed old callback must do nothing.
    const u64 old_revision = s1->newest_revision.fetch_add(1) + 1;
    const u64 new_revision = s1->newest_revision.fetch_add(1) + 1;
    CHECK(CommitLatestGuestWorldSnapshot(s1, new_revision, slot1, "latest progress"));
    CHECK(read(slot1) == "latest progress");
    CHECK(CommitLatestGuestWorldSnapshot(s1, old_revision, slot1, "stale progress"));
    CHECK(read(slot1) == "latest progress");

    // A different character's path is isolated from slot1's revision number.
    const u64 slot2_rev = s2->newest_revision.fetch_add(1) + 1;
    CHECK(CommitLatestGuestWorldSnapshot(s2, slot2_rev, slot2, "slot 2 progress"));
    CHECK(read(slot2) == "slot 2 progress");
    const u64 slot1_rev3 = s1->newest_revision.fetch_add(1) + 1;
    CHECK(CommitLatestGuestWorldSnapshot(s1, slot1_rev3, slot1, ""));
    CHECK(read(slot1).empty());
    CHECK(read(slot2) == "slot 2 progress");

    // Multiple queued old snapshots all lose to newest data.
    const u64 r4 = s1->newest_revision.fetch_add(1) + 1;
    const u64 r5 = s1->newest_revision.fetch_add(1) + 1;
    const u64 r6 = s1->newest_revision.fetch_add(1) + 1;
    CHECK(CommitLatestGuestWorldSnapshot(s1, r6, slot1, "final world"));
    CHECK(CommitLatestGuestWorldSnapshot(s1, r5, slot1, "too late 5"));
    CHECK(CommitLatestGuestWorldSnapshot(s1, r4, slot1, "too late 4"));
    CHECK(read(slot1) == "final world");

    // Failed atomic replacement still preserves the last committed snapshot.
    const fs::path blocked = root / "no-replacement";
    fs::create_directory(blocked);
    { std::ofstream file(blocked / "sentinel"); file << "do not delete"; }
    const auto sb = GuestWorldWriteStateFor(blocked);
    const u64 blocked_rev = sb->newest_revision.fetch_add(1) + 1;
    CHECK(!CommitLatestGuestWorldSnapshot(sb, blocked_rev, blocked, "new data"));
    CHECK(read(blocked / "sentinel") == "do not delete");
    CHECK(read(slot1) == "final world");
    return 0;
}
"""
        fixture = fixture.replace("// EXACT_PRODUCTION_WRITER", real_writer)
        fixture = fixture.replace("// EXACT_PRODUCTION_FENCE", real_guard)
        with tempfile.TemporaryDirectory(prefix="bbsc-b07-") as td:
            file = Path(td) / "fixture.cpp"
            executable = Path(td) / "fixture"
            folder = Path(td) / "synthetic"
            folder.mkdir()
            file.write_text(fixture, encoding="utf-8")
            build = subprocess.run(
                [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra",
                 "-Werror", "-pthread", str(file), "-o", str(executable)],
                capture_output=True, text=True, timeout=40,
            )
            self.assertEqual(build.returncode, 0, build.stderr[-3500:])
            run = subprocess.run([str(executable), str(folder)],
                                 capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0,
                             f"production guard test line {run.returncode}: {run.stderr}")


if __name__ == "__main__":
    unittest.main()
