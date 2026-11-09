# SPDX-License-Identifier: GPL-2.0-or-later
"""B14: execute the exact Windows-only BBPort resource controls with no game build."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bbport" / "build.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "ultimate-native-client-windows.yml"
B10 = ROOT / ".github" / "workflows" / "ultimate-batch-10-build-diagnostics.yml"


class WinResourceSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.bash = shutil.which("bash")
        start = cls.source.index("    windows_cmake_flags=()")
        end = cls.source.index("    cmake -S gpu -B out/gpu", start)
        cls.production_shell = cls.source[start:end]

    def test_shell_is_well_formed_no_platform_build(self):
        if not self.bash:
            self.skipTest("No Bash")
        run = subprocess.run([self.bash, "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)

    def selection(self, jobs=None, no_debug=None):
        if not self.bash:
            self.skipTest("No Bash")
        env = os.environ.copy()
        for var, val in (("BB_BUILD_JOBS", jobs), ("BB_WINDOWS_NO_DEBUG_SYMBOLS", no_debug)):
            env.pop(var, None)
            if val is not None:
                env[var] = str(val)
        script = (
            "set -euo pipefail\n" + self.production_shell
            + '\nprintf "JOBS=%s\\n" "${windows_ninja_args[*]}"\n'
            + 'printf "CMAKE_C=%s\\n" "${windows_cmake_flags[0]:-}"\n'
            + 'printf "CMAKE_CXX=%s\\n" "${windows_cmake_flags[1]:-}"\n'
        )
        return subprocess.run(
            [self.bash, "-c", script], env=env, capture_output=True, text=True,
            timeout=7,
        )

    def test_default_developer_build_preserves_debug_and_ninja_defaults(self):
        r = self.selection()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("JOBS=\n", r.stdout)
        self.assertIn("CMAKE_C=\n", r.stdout)
        self.assertIn("CMAKE_CXX=\n", r.stdout)

    def test_ci_low_memory_preserves_O2_and_limits_actual_ninja_to_two_jobs(self):
        r = self.selection(jobs=2, no_debug=1)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("JOBS=-j 2", r.stdout)
        self.assertIn("CMAKE_C=-DCMAKE_C_FLAGS_RELWITHDEBINFO=-O2 -g0 -DNDEBUG", r.stdout)
        self.assertIn("CMAKE_CXX=-DCMAKE_CXX_FLAGS_RELWITHDEBINFO=-O2 -g0 -DNDEBUG", r.stdout)

    def test_invalid_worker_counts_fail_closed_before_cmake(self):
        for jobs in ("0", "33", "-1", "1x", "abc", "12345"):
            with self.subTest(jobs=jobs):
                r = self.selection(jobs=jobs, no_debug=1)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn("BB_BUILD_JOBS must be an integer from 1 to 32", r.stderr)
        for jobs in ("1", "32"):
            r = self.selection(jobs=jobs, no_debug=1)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(f"JOBS=-j {jobs}", r.stdout)

    def test_ci_verifies_real_pe_and_keeps_failure_diagnostics(self):
        w = self.workflow
        for token in (
            "export BB_BUILD_JOBS=2",
            "export BB_WINDOWS_NO_DEBUG_SYMBOLS=1",
            "export BB_WINDOWS_STAGED_LINK=1",
            "BBPORT_PRODUCTION_WINDOWS_PE_BUILD_PASS_NO_GAME",
            "NO_GAME_ASSETS_NO_SERVER_NO_GITHUB_RELEASE_NO_UPLOAD_PASS",
            "GPU_INCREMENTAL_RETRY_PASSED_BUT_INITIAL_BUILD_FAILED",
            "GPU_FIRST_LINK_OR_COMPILER_FAILURES",
            "exit 1",
            "CMAKE_C_FLAGS_RELWITHDEBINFO",
            "CMAKE_CXX_FLAGS_RELWITHDEBINFO",
        ):
            self.assertIn(token, w, token)
        self.assertNotIn("ninja() { command ninja -j", w)
        self.assertIn('ninja "${windows_ninja_args[@]}" -C out/gpu', self.source)
        self.assertIn("report_bbport_build_failure 'Windows client/GPU/play targets'", self.source)

    def _run_real_production_stage_loop(self, failed_stage=""):
        """Run the extracted production stage control, mocking only Ninja itself."""
        if not self.bash:
            self.skipTest("No Bash")
        first = self.source.index("    if [[ ${BB_WINDOWS_STAGED_LINK:-0} == 1 ]]; then")
        # B16 checks EXE presence *after* staged Ninja; extract only the
        # real three-stage loop, not the replaced final copy command.
        last = self.source.index("
    fi
    bbsc_win_phase=validate-native-outputs", first) + len("
    fi")
        production_loop = self.source[first:last]
        shell = (
            "set -euo pipefail\n"
            'windows_ninja_args=(-j 2)\n'
            'report_bbport_build_failure() { echo "MOCK_REPORT:$1" >&2; }\n'
            'ninja() {\n'
            '  printf "NINJA_TARGETS:%s\\n" "$*" \n'
            '  if [[ "$BB_FAKE_FAIL_STAGE" == "net" && " $* " == *" bbnet "* ]]; then return 37; fi\n'
            '  if [[ "$BB_FAKE_FAIL_STAGE" == "gpu" && " $* " == *" bbgpu "* ]]; then return 38; fi\n'
            '  if [[ "$BB_FAKE_FAIL_STAGE" == "final" && " $* " == *" bb-probe "* ]]; then return 39; fi\n'
            '  return 0\n'
            '}\n'
            + production_loop + '\n'
            'echo STAGED_SUCCESS\n'
        )
        with tempfile.TemporaryDirectory(prefix="bbsc-b14-staged-") as td:
            (Path(td) / "out").mkdir()
            env = os.environ.copy()
            env["BB_WINDOWS_STAGED_LINK"] = "1"
            env["BB_FAKE_FAIL_STAGE"] = failed_stage
            run = subprocess.run(
                [self.bash, "-c", shell], cwd=td, env=env,
                capture_output=True, text=True, timeout=8
            )
            output = (Path(td) / "out/gpu-build.log").read_text()
        return run, output

    def test_prod_staged_ninja_builds_network_before_gpu_before_exes(self):
        run, log = self._run_real_production_stage_loop()
        self.assertEqual(run.returncode, 0, run.stderr)
        for stage in ("net", "gpu", "final"):
            self.assertIn("WINDOWS_NINJA_STAGE_PASS: " + stage, run.stdout)
        self.assertLess(log.index("bbnet"), log.index("bbgpu"))
        self.assertLess(log.index("bbgpu"), log.index("bb-probe bb-gpu-capabilities bb-play"))
        self.assertEqual(log.count("NINJA_TARGETS:-j 2 -C out/gpu"), 3)

    def test_prod_staged_ninja_preserves_raw_failed_stage_status(self):
        for stage, rc in (("net", 37), ("gpu", 38), ("final", 39)):
            with self.subTest(stage=stage):
                run, log = self._run_real_production_stage_loop(stage)
                self.assertEqual(run.returncode, rc, run.stdout + run.stderr)
                self.assertIn("WINDOWS_NINJA_STAGE_FAILED: " + stage, run.stderr)
                self.assertIn("MOCK_REPORT:Windows " + stage + " stage", run.stderr)
                self.assertNotIn("STAGED_SUCCESS", run.stdout)
                self.assertIn("NINJA_TARGETS:-j 2 -C out/gpu", log)

    def test_obsolete_b10_exact_allowlist_is_not_used_for_later_b14(self):
        old = B10.read_text(encoding="utf-8")
        self.assertIn("github.base_ref == 'experiment/ultimate-batch-09-windows-savedata-fault-tests-20261108'", old)


if __name__ == "__main__":
    unittest.main()
