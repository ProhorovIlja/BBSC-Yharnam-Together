# SPDX-License-Identifier: GPL-2.0-or-later
"""B15: verify real dual-history merge and ABI/identity source invariants.

This is a source provenance and contract gate; it does NOT run a five-player
Bloodborne game, deploy servers, or inspect private game/save/account files.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tools" / "ultimate" / "batch_15_manifest.json"


def git_bytes(path):
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True, timeout=20)


class UltimateB15CombinedHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_history_is_real_two_parent_merge_not_a_cherry_pick_copy(self):
        m = self.m
        commit = git("cat-file", "-p", m["merge_commit"])
        self.assertEqual(commit.returncode, 0, commit.stderr)
        parent_lines = [x.split(" ", 1)[1] for x in commit.stdout.splitlines()
                        if x.startswith("parent ")]
        self.assertEqual(parent_lines, [m["client_parent_sha"], m["server_parent_sha"]])
        for sha in parent_lines:
            r = git("merge-base", "--is-ancestor", sha, "HEAD")
            self.assertEqual(r.returncode, 0,
                             "source history not preserved for " + sha)
        self.assertTrue(m["no_live_deploy"])
        self.assertTrue(m["no_proprietary_game_data"])

    def test_pinned_server_sources_are_identical_to_server_pr8(self):
        m = self.m
        self.assertGreaterEqual(len(m["pinned_server_files"]), 14)
        for item in m["pinned_server_files"]:
            with self.subTest(path=item["path"]):
                self.assertEqual(git_bytes(item["path"]), item["blob"],
                                 "server PR8 source changed without a new review")

    def test_shared_protocol_keeps_client_link_restart_and_identical_proto(self):
        m = self.m
        for p,sha in m["protocol_source_pins"].items():
            self.assertEqual(git_bytes(p), sha, p)
        link = (ROOT / "server/coop/game_link.h").read_text(encoding="utf-8")
        for token in ("constexpr u8 GameFrameVersion = 1;",
                      "JoinHelloChannel = 0x42",
                      "void RestartStreams(std::optional<s64> old_heard_ms)",
                      "out.queued_ms > *old_heard_ms",
                      "fresh.push_back(std::move(*out))"):
            self.assertIn(token, link)
        self.assertNotIn("void RestartStreams() {", link)
        proto = (ROOT / "server/coop/coop.proto").read_text(encoding="utf-8")
        self.assertIn("syntax = \"proto3\";", proto)

    def test_server_5p_admission_and_world_security_contract_stays_unchanged(self):
        src = (ROOT / "server/src/link_server.cpp").read_text(encoding="utf-8")
        self.assertIn("m_world.RequireAuthenticatedIdentity();", src)
        self.assertIn("m_link.SetPartyOf(", src)
        load = (ROOT / "server/loadtest/bbload.cpp").read_text(encoding="utf-8")
        self.assertIn('parser.value("team-size").toInt(), 2, 5', load)
        self.assertIn('parser.value("owners").toInt(), 0,', load)
        m = self.m
        self.assertTrue(m["five_hunter_synthetic_test_only"])
        self.assertFalse(m["claims_real_game_verified"])

    def test_old_server_diff_contracts_scoped_to_original_branches(self):
        files = [
            ".github/workflows/server-candidate-five-hunters.yml",
            ".github/workflows/server-hardening.yml",
        ]
        for path in files:
            content = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn("github.event_name == 'workflow_dispatch'", content)
            self.assertIn("github.head_ref == 'feature/server-", content)
            self.assertIn("git diff --name-only origin/main HEAD", content)

    def test_no_public_assets_or_runtime_deployment(self):
        m = self.m
        for token in ("no_live_deploy", "no_proprietary_game_data",
                      "no_public_release", "no_player_save_access"):
            self.assertTrue(m[token])
        self.assertEqual(m["changed_paths_count"], 22)
        paths = {x["path"] for x in m["pinned_server_files"]}
        self.assertNotIn("server/coop/game_link.h", paths)


if __name__ == "__main__":
    unittest.main()
