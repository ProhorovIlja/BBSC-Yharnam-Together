# SPDX-License-Identifier: GPL-2.0-or-later
"""Real OS file-size write failure against the extracted production world writer.

Disposable temp files only. No Bloodborne game/save binary is loaded.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
WORLD = ROOT / "emulator/src/core/bloodborne_server_world.cpp"


class FailClosedWorldWriter(unittest.TestCase):
    def test_failed_stream_never_replaces_existing_backup(self):
        cxx = shutil.which("c++")
        if not cxx:
            self.skipTest("C++20 compiler not available")
        source = WORLD.read_text(encoding="utf-8")
        start = source.index("bool WriteWholeFile(")
        end = source.index("// The worlds this slot's save made", start)
        production_writer = source[start:end]
        self.assertIn("file.flush();", production_writer)
        self.assertIn("file.close();", production_writer)
        with tempfile.TemporaryDirectory(prefix="bbsc-write-fail-") as directory:
            root = Path(directory)
            cpp = root / "write_fail.cpp"
            exe = root / "write_fail"
            cpp.write_text(r'''
#include <csignal>
#include <fstream>
#include <filesystem>
#include <iostream>
#include <iterator>
#include <string>
#include <sys/resource.h>
#define LOG_ERROR(...) ((void)0)
// ACTUAL_PRODUCTION_WRITER
int main(int argc, char** argv) {
    if (argc != 2) return 1;
    const std::filesystem::path old = argv[1];
    {
        std::ofstream out(old, std::ios::binary);
        out << "verified-old-world";
    }
    std::signal(SIGXFSZ, SIG_IGN);
    const rlimit zero{0, 0};
    if (setrlimit(RLIMIT_FSIZE, &zero) != 0) return 2;
    if (WriteWholeFile(old, "guest-world-takeover-would-be-unsafe")) return 3;
    const std::ifstream in(old, std::ios::binary);
    const std::string got{std::istreambuf_iterator<char>{in}, {}};
    if (got != "verified-old-world") return 4;
    if (std::filesystem::exists(old.string() + ".part")) return 5;
    std::cout << "real zero-byte stream failure left complete backup intact\n";
    return 0;
}
'''.replace("// ACTUAL_PRODUCTION_WRITER", production_writer), encoding="utf-8")
            build = subprocess.run(
                [cxx, "-std=c++20", "-Wall", "-Wextra", "-O2",
                 str(cpp), "-o", str(exe)],
                capture_output=True, text=True, timeout=45,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            try:
                result = subprocess.run(
                    [str(exe), str(root / "personal_world0")],
                    capture_output=True, text=True, timeout=10,
                )
            except OSError as exc:
                self.skipTest("OS resource-limit fixture unsupported: " + str(exc))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("complete backup intact", result.stdout)


if __name__ == "__main__":
    unittest.main()
