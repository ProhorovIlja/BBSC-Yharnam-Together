# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline tests only: never access the GitHub network."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).with_name("source_sweep.py")
spec = importlib.util.spec_from_file_location("source_sweep", SCRIPT)
sweep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweep)


def repo(name, **kw):
    data = dict(full_name=name, description="source candidate",
                default_branch="main", fork=False, license={"spdx_id": "GPL-3.0"},
                pushed_at="2026-11-08T00:00:00Z")
    data.update(kw)
    return data


class FakeAPI:
    def __init__(self, limit=100):
        self.calls = 0
        self.max_requests = limit
        self.seen = []

    def get(self, path, params=None):
        if self.calls >= self.max_requests:
            raise sweep.RequestLimit("request budget reached")
        self.calls += 1
        self.seen.append((path, params))
        if path == "/search/repositories":
            page = params["page"]
            return {
                "total_count": 3,
                "items": {
                    1: [repo("droogie/bbhost"), repo("example/bbhost")],
                    2: [repo("example/bbhost")],
                }.get(page, []),
            }
        if path == "/repos/droogie/bbhost":
            return repo("droogie/bbhost", fork=False)
        if path == "/repos/droogie/bbhost/branches":
            return [{"name": "master", "commit": {"sha": "deadbeef" * 5}}]
        if path == "/repos/droogie/bbhost/issues":
            return [
                {"number": 220, "title": "GPU device lost", "state": "open",
                 "updated_at": "2026-11-08T00:00:00Z", "comments": 1,
                 "body": "private screenshot must not be embedded", "labels": [{"name": "GPU"}]},
                {"number": 217, "title": "This is a PR, not an Issue",
                 "state": "open", "pull_request": {"url": "synthetic"}, "body": "test"},
                {"number": 100, "title": "Old fixed issue", "state": "closed",
                 "state_reason": "completed", "comments": 3, "body": "old log"},
            ]
        if path == "/repos/droogie/bbhost/pulls":
            return [{"number": 217, "title": "Network protocol candidate",
                     "state": "open", "draft": False,
                     "updated_at": "2026-11-08T00:00:00Z",
                     "head": {"sha": "f00d" * 10}}]
        if path.startswith("/repos/"):
            return repo(path.removeprefix("/repos/"))
        raise AssertionError(f"unexpected endpoint {path}")


class SweepTests(unittest.TestCase):
    def test_paginates_deduplicates_and_inspects_seed_before_search_hits(self):
        api = FakeAPI()
        report = sweep.scan(api, searches={"original-bbhost": "bbhost in:name fork:true"},
                            seeds=("droogie/bbhost",), search_pages=3,
                            search_page_size=2, inspect_repos=1)
        self.assertEqual(report["coverage"], "BOUNDED_DISCOVERY_NOT_ALL_GITHUB")
        self.assertEqual(len(report["repositories"]), 2)
        self.assertEqual(report["searches"][0]["pages"], 2)
        self.assertFalse(report["searches"][0]["truncated"])
        self.assertEqual(report["searches"][0]["matched_in_pages"], 3)
        bbhost = next(r for r in report["repositories"] if r["repo"] == "droogie/bbhost")
        self.assertEqual(bbhost["license"], "GPL-3.0")
        self.assertEqual(bbhost["branches"][0]["commit"], "deadbeef" * 5)
        self.assertEqual(bbhost["pull_requests"][0]["head_sha"], "f00d" * 10)
        self.assertEqual([i["number"] for i in bbhost["issues"]], [220, 100])
        self.assertEqual([i["state"] for i in bbhost["issues"]], ["open", "closed"])
        self.assertEqual(bbhost["issues"][0]["labels"], ["GPU"])
        self.assertFalse(bbhost["issue_truncated"])
        self.assertNotIn("private screenshot", str(report))
        self.assertNotIn("old log", str(report))
        self.assertIn("original-bbhost", bbhost["found_in"])
        self.assertIn("GitHub source sweep", sweep.markdown(report))
        self.assertEqual(api.calls, 6)
        self.assertNotIn("Authorization", str(report))

    def test_finite_budget_returns_explicit_partial_coverage(self):
        api = FakeAPI(limit=1)
        report = sweep.scan(api, searches={"q": "bbhost"}, seeds=(),
                            search_page_size=2, search_pages=4, inspect_repos=0)
        self.assertTrue(report["truncated"])
        self.assertTrue(report["searches"][0]["truncated"])
        self.assertEqual(report["request_count"], 1)
        self.assertTrue(any("budget" in note for note in report["warnings"]))

    def test_bad_repository_identity_is_ignored(self):
        self.assertIsNone(sweep.compact(repo("fake/../../not-a-repo")))
        self.assertIsNone(sweep.compact({"full_name": "not_a_repo"}))
        self.assertEqual(sweep.compact({"full_name": "example/name"})["license"], None)

    def test_branch_and_pr_page_limits_are_not_called_complete(self):
        class Full(FakeAPI):
            def get(self, path, params=None):
                if path.endswith("/branches"):
                    self.calls += 1
                    return [{"name": str(x), "commit": {"sha": str(x)}} for x in range(100)]
                if path.endswith("/pulls"):
                    self.calls += 1
                    return [{"number": x, "title": "candidate"} for x in range(100)]
                if path.endswith("/issues"):
                    self.calls += 1
                    return [{"number": x + 1, "title": "issue", "state": "open"} for x in range(100)]
                return super().get(path, params)
        api = Full()
        report = sweep.scan(api, searches={"x": "bbhost"}, seeds=("droogie/bbhost",),
                            search_pages=1, search_page_size=99, inspect_repos=1,
                            branch_pages=1, pr_pages=1)
        bbhost = next(r for r in report["repositories"] if r["repo"] == "droogie/bbhost")
        self.assertTrue(report["truncated"])
        self.assertTrue(bbhost["branch_truncated"] and bbhost["pr_truncated"] and bbhost["issue_truncated"])
        self.assertEqual(len(bbhost["branches"]), 100)
        self.assertEqual(len(bbhost["pull_requests"]), 100)
        self.assertEqual(len(bbhost["issues"]), 100)


if __name__ == "__main__":
    unittest.main()
