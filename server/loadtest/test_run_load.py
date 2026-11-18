# SPDX-License-Identifier: GPL-2.0-or-later
from contextlib import redirect_stderr
import io
from pathlib import Path
import subprocess
import tempfile
import sys
import time
import unittest

from unittest.mock import Mock

from run_load import local_build_fingerprint, print_refusals, stop_child, worker_result


class WorkerTests(unittest.TestCase):
    def spawn(self, code):
        child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
        self.addCleanup(stop_child, child)
        return child

    def test_one_nonempty_row(self):
        child = self.spawn("print('diagnostic'); print('{\"games\": 3}')")
        self.assertEqual(worker_result(child, time.monotonic() + 5), {"games": 3})

    def test_failed_empty_or_duplicate_worker_is_not_a_successful_sample(self):
        for code in ("raise SystemExit(1)", "print('{}')",
                     "print('{\"games\": 3}'); print('{\"games\": 3}')"):
            with self.subTest(code=code), self.assertRaises(RuntimeError):
                worker_result(self.spawn(code), time.monotonic() + 5)

    def test_timeout_has_bounded_cleanup(self):
        child = self.spawn("import time; time.sleep(30)")
        with self.assertRaises(subprocess.TimeoutExpired):
            worker_result(child, time.monotonic() + 0.2)
        stop_child(child)
        self.assertIsNotNone(child.poll())

class LocalBuildTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.home = Path(folder.name)
        self.log = self.home / "shadnet.log"
        self.server = Mock(returncode=None)
        self.server.poll.return_value = None

    def test_reads_checked_build_instead_of_simulator_placeholder(self):
        fingerprint = "bb-build 1;version=1.5.1-test;revision=abcd-dirty;protocol=5;"
        self.log.write_text("other output\nLink: games must run this server's build: "
                            + fingerprint + "\n", encoding="utf-8")
        self.assertEqual(local_build_fingerprint(self.log, self.server, 0), fingerprint)

    def test_reads_container_build_with_no_git_revision(self):
        fingerprint = "bb-build 1;version=dev;revision=;protocol=9;"
        self.log.write_text("Link: games must run this server's build: " + fingerprint + "\n",
                            encoding="utf-8")
        self.assertEqual(local_build_fingerprint(self.log, self.server, 0), fingerprint)

    def test_missing_disabled_and_malformed_build_fail_closed(self):
        for line in ("", "Link: this server's build is not checked",
                     "Link: games must run this server's build: bbload",
                     "Link: games must run this server's build: bb-build 1;version=dev;"):
            with self.subTest(line=line), self.assertRaises(RuntimeError):
                self.log.write_text(line + "\n", encoding="utf-8")
                local_build_fingerprint(self.log, self.server, 0)

    def test_early_server_exit_is_reported(self):
        self.log.touch()
        self.server.poll.return_value = self.server.returncode = 17
        with self.assertRaisesRegex(RuntimeError, "exited during startup: 17"):
            local_build_fingerprint(self.log, self.server, 0)

    def test_refusal_diagnostics_are_bounded_and_exclude_server_log(self):
        self.log.write_text("server refused: do not print\n", encoding="utf-8")
        (self.home / "bbload0.log").write_text(
            "bot0 refused: another build\n" * 10, encoding="utf-8")
        out = io.StringIO()
        with redirect_stderr(out):
            print_refusals(self.home)
        self.assertEqual(out.getvalue().count("another build"), 8)
        self.assertNotIn("do not print", out.getvalue())
