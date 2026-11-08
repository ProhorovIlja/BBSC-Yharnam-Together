# SPDX-License-Identifier: GPL-2.0-or-later
"""B10: exercise the exact bbport/build.sh failure reporter without building games.

The regression reproduces set -euo pipefail with a Ninja log containing only
[N/M] progress lines. The original grep returned 1 and cut off the diagnostics.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "bbport" / "build.sh"


class BuildFailureReporting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = BUILD.read_text(encoding="utf-8")
        start = cls.source.index("report_bbport_build_failure() {")
        end = cls.source.index("\n}\n\n# Kaniel", start) + 2
        cls.production_function = cls.source[start:end]
        cls.bash = shutil.which("bash")

    def run_report(self, lines, exists=True, fail_ninja=False):
        if self.bash is None:
            self.skipTest("bash required to exercise the production Windows/MSYS2 shell")
        with tempfile.TemporaryDirectory(prefix="bbsc-b10-") as td:
            path = Path(td) / "gpu-build.log"
            if exists:
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            call = (
                'if ! false; then '
                'report_bbport_build_failure "synthetic Ninja failure" "$1"; '
                'exit 1; fi'
                if fail_ninja else
                'report_bbport_build_failure "synthetic Ninja failure" "$1"; '
                'echo REPORTER_RETURNED_SUCCESS'
            )
            source = "set -euo pipefail\n" + self.production_function + "\n" + call
            return subprocess.run(
                [self.bash, "-c", source, "bbsc-b10-test", str(path)],
                capture_output=True, text=True, timeout=10,
            )

    def test_no_nonprogress_lines_cannot_abort_failure_reporter(self):
        out = self.run_report([f"[{i}/433] Compiling..." for i in range(1, 434)])
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("NO_COMPILER_DIAGNOSTIC_IN_LOG", out.stderr)
        self.assertIn("BBPORT_NATIVE_BUILD_FAILURE: synthetic Ninja failure", out.stderr)
        self.assertIn("REPORTER_RETURNED_SUCCESS", out.stdout)
        self.assertLess(len(out.stderr), 2500)

    def test_failing_ninja_always_exits_nonzero_with_marker(self):
        out = self.run_report(["[431/433] Linking bb-probe.exe"], fail_ninja=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("BBPORT_NATIVE_BUILD_FAILURE", out.stderr)
        self.assertIn("NO_COMPILER_DIAGNOSTIC_IN_LOG", out.stderr)

    def test_first_eight_diagnostics_only_and_bounded_line_length(self):
        logs = ["[1/433] Build object"] + [
            f"ld.lld: error: undefined symbol: item_{i} " + "x" * 1400
            for i in range(15)
        ]
        out = self.run_report(logs)
        self.assertEqual(out.returncode, 0, out.stderr[:2000])
        first = out.stderr.split("FIRST_COMPILER_OR_LINKER_ERRORS_MAX_8:", 1)[1]
        first = first.split("NONPROGRESS_LOG_TAIL_MAX_12:", 1)[0]
        self.assertEqual(first.count("ld.lld: error:"), 8)
        self.assertIn("item_0", first)
        self.assertNotIn("item_13", first)
        self.assertLess(len(out.stderr), 15000)

    def test_missing_log_is_reported_not_silent(self):
        out = self.run_report([], exists=False)
        self.assertEqual(out.returncode, 0)
        self.assertIn("BUILD_LOG_MISSING", out.stderr)

    def test_both_platform_ninja_failure_paths_call_exact_helper(self):
        script = self.source
        win = script.split(
            "if ! ninja -C out/gpu bb-probe bb-gpu-capabilities bb-play", 1
        )[1].split("\n    fi", 1)[0]
        linux = script.split("if ! ninja -C out/gpu bbgpu", 1)[1].split("\nfi", 1)[0]
        self.assertIn("report_bbport_build_failure 'Windows client/GPU/play targets'", win)
        self.assertIn("report_bbport_build_failure 'Linux GPU library'", linux)
        self.assertIn("exit 1", win)
        self.assertIn("exit 1", linux)
        self.assertIn("|| true", self.production_function)


if __name__ == "__main__":
    unittest.main()
