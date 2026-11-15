# SPDX-License-Identifier: GPL-2.0-or-later
import subprocess
import sys
import time
import unittest

from run_load import stop_child, worker_result


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
