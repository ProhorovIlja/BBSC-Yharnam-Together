"""Compile the production DiscordPipe with a deterministic fake Win32 pipe."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "bbport/gpu/bbcoop/discord_status.cpp"

PRELUDE = r"""
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <deque>
#include <string>
#include <thread>
#include <vector>
#include "discord_activity.h"
using DiscordActivity::Field;
using DWORD = std::uint32_t;
using HANDLE = int;
constexpr int INVALID_HANDLE_VALUE = -1;
constexpr int GENERIC_READ = 1, GENERIC_WRITE = 2, OPEN_EXISTING = 3;
std::deque<char> inbound;
std::vector<std::string> outbound;
std::string last_join;
unsigned asks = 0, closes = 0;
bool broken = false;
bool write_error = false, short_write = false;
HANDLE CreateFileW(const wchar_t*, int, int, void*, int, int, void*) { return 1; }
bool CloseHandle(HANDLE) { ++closes; return true; }
bool PeekNamedPipe(HANDLE, void*, int, void*, DWORD* n, void*) {
    *n = static_cast<DWORD>(inbound.size());
    return !broken;
}
bool ReadFile(HANDLE, char* dest, DWORD amount, DWORD* got, void*) {
    // A synchronous read requesting more than the buffer could stall on Windows.
    assert(amount <= inbound.size());
    *got = amount;
    for (DWORD i = 0; i < amount; ++i) {
        dest[i] = inbound.front();
        inbound.pop_front();
    }
    return true;
}
bool WriteFile(HANDLE, const char* src, DWORD n, DWORD* wrote, void*) {
    if (write_error) {
        *wrote = 0;
        return false;
    }
    *wrote = short_write ? n - 1 : n;
    outbound.emplace_back(src, *wrote);
    return true;
}
namespace fmt {
std::string format(const char*, const std::string&) { return "{}"; }
}
std::string ApplicationId() { return "fixture"; }
void JoinFromDiscord(const std::string& secret) { last_join = secret; }
void NoteJoinRequest(const std::string&) { ++asks; }
#define LOG_WARNING(...) ((void)0)
std::string frame(std::uint32_t opcode, const std::string& body,
                  std::uint32_t override_length = 0) {
    const auto size = override_length ? override_length : static_cast<std::uint32_t>(body.size());
    std::string out(8, '\0');
    std::memcpy(out.data(), &opcode, 4);
    std::memcpy(out.data() + 4, &size, 4);
    return out + body;
}
void feed(const std::string& bytes) { inbound.insert(inbound.end(), bytes.begin(), bytes.end()); }
void ready() { feed(frame(1, R"({"evt":"READY"})")); }
"""

TEST = r"""
int main(int argc, char** argv) {
    assert(argc == 2);
    const std::string mode = argv[1];
    DiscordPipe pipe;
    if (mode == "timeout") {
        feed(frame(1, R"({"evt":"NOT_READY"})"));
        const auto start = std::chrono::steady_clock::now();
        assert(!pipe.Connect() && !pipe.Connected());
        assert(std::chrono::steady_clock::now() - start >= std::chrono::seconds(1));
    } else if (mode == "error") {
        feed(frame(1, R"({"evt":"ERROR"})"));
        assert(!pipe.Connect() && !pipe.Connected());
    } else {
        ready();
        assert(pipe.Connect() && pipe.Connected());
        if (mode == "fragment") {
            const auto join = frame(1, R"({"evt":"ACTIVITY_JOIN","secret":"t:room"})");
            for (std::size_t i = 0; i + 1 < join.size(); ++i) {
                feed(join.substr(i, 1));
                assert(pipe.Drain(false) && last_join.empty());
            }
            feed(join.substr(join.size() - 1));
            assert(pipe.Drain(false) && last_join == "t:room");
        } else if (mode == "limits") {
            feed(frame(3, std::string(65536, 'a')));
            assert(pipe.Drain(false) && outbound.back() == frame(4, std::string(65536, 'a')));
            feed(frame(1, {}, 65537));
            assert(!pipe.Drain(false) && !pipe.Connected());
        } else if (mode == "reconnect") {
            feed(frame(1, R"({"evt":"ACTIVITY_JOIN","secret":"stale"})").substr(0, 12));
            assert(pipe.Drain(false));
            broken = true;
            assert(!pipe.Drain(false) && closes == 1);
            broken = false;
            ready();
            assert(pipe.Connect());
            feed(frame(3, ""));
            assert(pipe.Drain(false) && outbound.back() == frame(4, "") && last_join.empty());
            feed(frame(2, ""));
            assert(!pipe.Drain(false) && !pipe.Connected());
        } else if (mode == "write_error" || mode == "short_write") {
            write_error = mode == "write_error";
            short_write = !write_error;
            assert(!pipe.Send(1, "{}") && !pipe.Connected() && closes == 1);
            const auto writes = outbound.size();
            assert(!pipe.Send(1, "{}") && outbound.size() == writes);
            write_error = short_write = false;
            ready();
            assert(pipe.Connect() && pipe.Connected());
            feed(frame(3, ""));
            assert(pipe.Drain(false) && outbound.back() == frame(4, ""));
        } else if (mode == "budget") {
            for (unsigned i = 0; i < 33; ++i) {
                feed(frame(1, R"({"evt":"ACTIVITY_JOIN_REQUEST"})"));
            }
            assert(pipe.Drain(false) && asks == 32);
            assert(pipe.Drain(false) && asks == 33);
        } else {
            assert(false);
        }
    }
}
"""


class DiscordReceiveTest(unittest.TestCase):
    def test_production_pipe(self):
        compiler = shutil.which("cl" if os.name == "nt" else "c++")
        self.assertIsNotNone(compiler, "C++ compiler required for production pipe regression")
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("class DiscordPipe {")
        end = source.index("\n};", start) + len("\n};")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            cpp = temp / "pipe.cpp"
            exe = temp / ("pipe.exe" if os.name == "nt" else "pipe")
            cpp.write_text(PRELUDE + source[start:end] + TEST, encoding="utf-8")
            include = SOURCE.parent
            if os.name == "nt":
                cmd = [compiler, "/nologo", "/std:c++20", "/EHsc", f"/I{include}", str(cpp),
                       f"/Fe:{exe}"]
            else:
                cmd = [compiler, "-std=c++20", "-Wall", "-Wextra", "-Werror", "-pthread",
                       "-I", str(include), str(cpp), "-o", str(exe)]
            subprocess.run(cmd, cwd=temp, check=True, timeout=60)
            for mode in ("fragment", "limits", "reconnect", "budget", "timeout", "error",
                         "write_error", "short_write"):
                with self.subTest(mode=mode):
                    subprocess.run([str(exe), mode], cwd=temp, check=True, timeout=6)


    def compile_and_run(self, source, include):
        compiler = shutil.which("cl" if os.name == "nt" else "c++")
        self.assertIsNotNone(compiler, "C++ compiler required for Discord regressions")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            exe = temp / ("presence.exe" if os.name == "nt" else "presence")
            if os.name == "nt":
                cmd = [compiler, "/nologo", "/std:c++20", "/EHsc", "/utf-8",
                       f"/I{include}", str(source), f"/Fe:{exe}"]
            else:
                cmd = [compiler, "-std=c++20", "-Wall", "-Wextra", "-Werror", "-pedantic",
                       "-I", str(include), str(source), "-o", str(exe)]
            subprocess.run(cmd, cwd=temp, check=True, timeout=60)
            subprocess.run([str(exe)], cwd=temp, check=True, timeout=6)

    def test_reused_presence_policy(self):
        self.compile_and_run(ROOT / "bbport/tests/test_discord_activity.cpp", ROOT / "bbport")

    def test_reused_boss_gauges_and_clock(self):
        self.compile_and_run(ROOT / "emulator/tests/bloodborne/test_ultimate_boss_presence.cpp",
                             ROOT / "emulator/src")

    def test_launcher_privacy(self):
        import sys
        subprocess.run([sys.executable, "-m", "py_compile", "bbport_coop.py",
                        "bbport_launcher_win.py"], cwd=ROOT / "bbport/launcher",
                       check=True, timeout=20)
        subprocess.run([sys.executable, "-m", "unittest",
                        "test_coop_launcher.DiscordStatusTests"], cwd=ROOT / "bbport/tests",
                       check=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
