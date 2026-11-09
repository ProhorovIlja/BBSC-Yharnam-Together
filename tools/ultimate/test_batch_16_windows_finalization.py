# SPDX-License-Identifier: GPL-2.0-or-later
"""B16: execute ACTUAL final Windows build shell commands, with synthetic PE stubs.

No game files, login details, private saves, deployment or actual Windows link.
The full Windows native CI separately checks real compiler output and PE headers.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "bbport" / "build.sh"
WINDOWS_CI = ROOT / ".github/workflows/ultimate-native-client-windows.yml"
EXECUTABLES = ("bb-probe.exe", "bb-gpu-capabilities.exe", "bb-play.exe")


class WindowsNativeFinalization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bash = shutil.which("bash")
        cls.production = SOURCE.read_text(encoding="utf-8")
        start = cls.production.index("    bbsc_win_phase=validate-native-outputs")
        end = cls.production.index("\n    exit 0", start) + len("\n    exit 0")
        cls.real_finalization = cls.production[start:end]

    def run_actual_finalization(self, missing=None, override_cp=""):
        if not self.bash:
            self.skipTest("Bash unavailable")
        with tempfile.TemporaryDirectory(prefix="bbsc-16-win-final-") as td:
            root = Path(td)
            (root / "out/gpu").mkdir(parents=True)
            for name in EXECUTABLES:
                if name != missing:
                    (root / "out/gpu" / name).write_bytes(b"MZ\x00B16-TEST-ONLY\x00")
            script = (
                "set -euo pipefail\n"
                "build_mode=production\n"
                "bbsc_win_phase=initial\n"
                'trap \'rc=$?; if ((rc != 0)); then echo "EXIT_AT:$bbsc_win_phase rc=$rc" >&2; fi\' EXIT\n'
                + override_cp + "\n"
                + self.real_finalization + "\n"
            )
            result = subprocess.run(
                [self.bash, "-c", script], cwd=td, capture_output=True,
                text=True, timeout=12, env=os.environ.copy()
            )
            copied = {}
            for name in EXECUTABLES:
                path = root / "out" / name
                copied[name] = path.read_bytes() if path.is_file() else None
            mode = root / "out/build-mode.txt"
            return result, copied, mode.read_text() if mode.exists() else None

    def test_build_sh_bash_syntax(self):
        if not self.bash:
            self.skipTest("Bash unavailable")
        a = subprocess.run([self.bash, "-n", str(SOURCE)],
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(a.returncode, 0, a.stderr)

    def test_real_shell_validates_then_copies_and_checks_all_three(self):
        r, copied, mode = self.run_actual_finalization()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("WINDOWS_NATIVE_FINALIZATION_BEGIN", r.stdout)
        for name in EXECUTABLES:
            self.assertIn("WINDOWS_NATIVE_TARGET_READY: " + name, r.stdout)
            self.assertTrue(copied[name].startswith(b"MZ"))
        self.assertIn("WINDOWS_NATIVE_COPY_COMMAND_PASS", r.stdout)
        self.assertIn("WINDOWS_NATIVE_COPY_IDENTITY_PASS", r.stdout)
        self.assertIn("WINDOWS_NATIVE_BUILD_MODE: production", r.stdout)
        self.assertEqual(mode.strip(), "production")

    def test_missing_linker_output_exits_before_copy_and_reports_exact_target(self):
        for missing in EXECUTABLES:
            with self.subTest(missing=missing):
                r, copied, mode = self.run_actual_finalization(missing=missing)
                self.assertEqual(r.returncode, 46, r.stdout + r.stderr)
                self.assertIn("WINDOWS_NATIVE_TARGET_MISSING_OR_EMPTY: " + missing, r.stderr)
                self.assertIn("EXIT_AT:validate-native-outputs rc=46", r.stderr)
                self.assertNotIn("WINDOWS_NATIVE_COPY_BEGIN", r.stdout)
                self.assertTrue(all(data is None for data in copied.values()))
                self.assertIsNone(mode)

    def test_real_script_reports_copy_failure_and_retains_raw_error_code(self):
        r, copied, mode = self.run_actual_finalization(
            override_cp="cp() { return 37; }"
        )
        self.assertEqual(r.returncode, 37, r.stderr)
        self.assertIn("WINDOWS_NATIVE_COPY_BEGIN", r.stdout)
        self.assertIn("WINDOWS_NATIVE_COPY_FAILED: rc=37", r.stderr)
        self.assertIn("EXIT_AT:copy-native-outputs rc=37", r.stderr)
        self.assertIsNone(mode)

    def test_real_script_rejects_modified_output_without_writing_mode(self):
        corrupt = (
            'cp() { command cp "$@"; '
            'printf "damaged" >> out/bb-play.exe; return 0; }'
        )
        r, copied, mode = self.run_actual_finalization(override_cp=corrupt)
        self.assertEqual(r.returncode, 47, r.stderr)
        self.assertIn("WINDOWS_NATIVE_COPIED_OUTPUT_MISMATCH: bb-play.exe", r.stderr)
        self.assertIn("EXIT_AT:verify-copied-outputs rc=47", r.stderr)
        self.assertIsNone(mode)

    def test_actual_windows_ci_checks_pre_retry_output_file_presence(self):
        w = WINDOWS_CI.read_text(encoding="utf-8")
        for text in (
            "WINDOWS_NATIVE_PRE_RETRY_OUTPUT",
            "WINDOWS_NATIVE_CLIENT_BUILD_FAILED",
            "GPU_INCREMENTAL_RETRY_PASSED_BUT_INITIAL_BUILD_FAILED",
            "VALID_AMD64_PE32_PLUS",
            "B16_PRODUCTION_OUTPUT_FINALIZATION_FIXTURE_PASS",
        ):
            self.assertIn(text, w)
        self.assertIn("WINDOWS_NATIVE_EXIT_PHASE:", self.production)


if __name__ == "__main__":
    unittest.main()
