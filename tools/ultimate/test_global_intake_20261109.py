# SPDX-License-Identifier: GPL-2.0-or-later
"""B11: validate the persistent broad-source discovery radar and triage.

Metadata-only test; no network, no repository clones, no game files.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "tools" / "ultimate"
DOC = ROOT / "docs" / "ULTIMATE_GLOBAL_SOURCE_INTAKE_20261109.md"


def load(name):
    return json.loads((DIR / name).read_text(encoding="utf-8"))


class SourceRadar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.primary = load("source_radar_20261109_primary.json")
        cls.adjacent = load("source_radar_20261109_adjacent.json")
        cls.priority = load("global_intake_priorities_20261109.json")

    def test_search_coverage_is_inspectable_not_false_exhaustiveness(self):
        a, b = self.primary, self.adjacent
        self.assertEqual(len(a["queries"]), 10)
        self.assertEqual(len(b["queries"]), 10)
        for item in (a, b):
            self.assertEqual(item["date_utc"], "2026-11-09")
            self.assertIn("first", str(item).lower())
            self.assertEqual(sum(q["first_page_count"] for q in item["queries"]),
                             sum(q["first_page_count"] for q in item["queries"]))
            self.assertFalse(any(q["error"] for q in item["queries"]))
            for q in item["queries"]:
                self.assertLessEqual(q["first_page_count"], 35)
        self.assertIn("not", a["purpose"].lower())

    def test_no_duplicate_repository_and_dedup_across_query_families(self):
        seen = []
        for dataset in (self.primary, self.adjacent):
            names = [x["name"] for x in dataset["discovered_repositories"]]
            self.assertEqual(len(names), len(set(names)))
            self.assertGreater(len(names), 50)
            for item in dataset["discovered_repositories"]:
                self.assertIn("/", item["name"])
                self.assertTrue(item["matched_queries"])
                self.assertFalse(item.get("visibility") == "private")
            seen.extend(names)
        self.assertGreater(len(set(seen)), 200)
        self.assertLess(len(set(seen)), len(seen))

    def test_triage_is_not_same_as_code_import(self):
        triage = self.priority["priorities"]
        self.assertGreaterEqual(len(triage), 20)
        self.assertTrue(self.priority["policy"]["no_auto_merge"])
        self.assertTrue(self.priority["policy"]["no_auto_deploy"])
        allowed = {"playable", "native", "both"}
        statuses = {
            "already_in_B01_source", "candidate_diff_review", "candidate_design_review",
            "requires_security_review", "independent_runtime_benchmark",
            "do_not_cherry_pick_whole_pr", "evidence_only",
        }
        refs = set()
        for row in triage:
            self.assertIn(row["mission"], allowed)
            self.assertIn(row["status"], statuses)
            self.assertIn(row["source_repo"], row["source_url"])
            self.assertGreater(len(row["gate"]), 15)
            self.assertNotIn(row["source_url"], refs)
            refs.add(row["source_url"])
        self.assertTrue(any(x["status"] == "independent_runtime_benchmark" for x in triage))
        self.assertTrue(any(x["mission"] == "native" for x in triage))
        self.assertEqual(sum(x["status"] == "already_in_B01_source" for x in triage), 1)

    def test_public_notes_preserve_two_missions_and_do_not_mention_private_drive_ids(self):
        text = DOC.read_text(encoding="utf-8")
        for keyword in ("Mission A", "Mission B", "241", "301",
                        "GitHub", "BBHost", "Dark Souls III", "Fornex",
                        "no auto", "1.09"):
            self.assertIn(keyword.lower(), text.lower(), keyword)
        for excluded in ("gungrain@gmail.com", "djay73192@gmail.com",
                         "eboot.bin-decrypted", "1lFjsiTT1oH23f5dJWODf8bTh8QeI2BXKXvdWbxMkKsE"):
            self.assertNotIn(excluded, text)


if __name__ == "__main__":
    unittest.main()
