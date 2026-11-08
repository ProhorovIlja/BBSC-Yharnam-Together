# SPDX-License-Identifier: GPL-2.0-or-later
"""B02 source provenance and no-wire-version-bump checks. Does not deploy/build."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "tools/ultimate/batch_02_manifest.json"


def blob_sha(path):
    raw = (ROOT / path).read_bytes()
    return hashlib.sha1(("blob %d\0" % len(raw)).encode() + raw).hexdigest()


class BatchTwoSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(PLAN.read_text(encoding="utf-8"))
        cls.reconnect, cls.lamps = cls.plan["integrated"]

    def test_provenance_and_release_guards(self):
        self.assertEqual(self.plan["batch_id"], "B02-2026-11-08")
        self.assertEqual(self.plan["parent_pr"], 32)
        self.assertTrue(self.plan["no_fornex_changes"])
        self.assertTrue(self.plan["no_deploy"])
        self.assertTrue(self.plan["no_game_or_save_assets"])
        self.assertTrue(self.plan["tests_only"])
        self.assertIn("NOT_PLAYTESTED", self.plan["disposition"])
        self.assertGreaterEqual(len(self.plan["release_gates"]), 6)

    def test_exact_reconnect_source_and_no_wire_protocol_drift(self):
        p = "server/coop/game_link.h"
        self.assertEqual(blob_sha(p), self.reconnect["integrated_game_link_blob"])
        source = (ROOT / p).read_text(encoding="utf-8")
        self.assertIn("constexpr u8 GameFrameVersion = 1;", source)
        self.assertIn("constexpr u8 GamePacketsType = 0x40;", source)
        self.assertFalse(self.reconnect["wire_format_changed"])
        self.assertEqual(self.reconnect["game_frame_version"], 1)
        self.assertIn("RestartStreams(heard_before);", source)
        self.assertIn("static constexpr u32 JoinHelloChannel = 0x42;", source)
        self.assertIn("out.queued_ms > *old_heard_ms", source)
        self.assertIn("fresh.push_back(std::move(*out));", source)

    def test_2_3_5_player_source_reproductions_and_actual_helpers(self):
        path = "emulator/tests/bloodborne/test_bloodborne_game_link.cpp"
        self.assertEqual(blob_sha(path), self.reconnect["test_blob"])
        s = (ROOT / path).read_text(encoding="utf-8")
        self.assertIn("WhatGreetedTheMembersNewGameGoesToItAfterTheRestart", s)
        self.assertIn("AThreeOrFiveHunterPartyKeepsEachRejoinStreamSeparate", s)
        self.assertIn("u8{2}, u8{3}, u8{5}", s)
        self.assertIn("Carry(host_to_guest, new_guest", s)

    def test_no_duplicate_unmerged_lamp_patch(self):
        self.assertEqual(self.lamps["source_pr"], 488)
        self.assertEqual(self.lamps["selected_action"], "ALREADY_PRESENT_NO_DUPLICATE_PATCH")
        self.assertEqual(blob_sha("tools/re/tests/test_team_world_lamps_regression.py"),
                         self.lamps["test_blob"])
        self.assertIn("FlagChanges WithoutRelitLamps",
                      (ROOT / "emulator/src/core/bloodborne_party.cpp").read_text(encoding="utf-8"))
        self.assertIn("ForgetRelitLamps();",
                      (ROOT / "emulator/src/core/bloodborne_flags_store.cpp").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
