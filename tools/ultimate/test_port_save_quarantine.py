"""Offline-only self tests; no real player files are loaded."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from port_save_quarantine import (
    MANIFEST, SnapshotError, stage_snapshot, verify_snapshot,
)


class QuarantineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "savedata").mkdir()
        (self.root / "savedata_party").mkdir()
        (self.root / "savedata" / "hunters").mkdir()
        (self.root / "savedata" / "hunters" / "userdata0000").write_bytes(
            b"private test character\x00\x01" * 12
        )
        (self.root / "savedata" / "hunters" / "userdata0010").write_bytes(
            b"settings only"
        )
        (self.root / "savedata" / "hunters" / "interrupted.bbtmp").write_bytes(
            b"never archive unfinished save"
        )
        (self.root / "savedata_party" / "party.txt").write_text("private test party")

    def test_solo_stages_only_to_quarantine_not_party(self):
        previous_party = (self.root / "savedata_party" / "party.txt").read_bytes()
        previous_solo = (self.root / "savedata" / "hunters" / "userdata0000").read_bytes()
        ready = stage_snapshot(self.root, "solo")
        self.assertEqual(ready.suffix, ".ready")
        self.assertEqual(ready.parent.name, "ultimate_quarantine")
        result = verify_snapshot(ready)
        self.assertEqual(result["source_kind"], "solo")
        self.assertEqual(len(result["files"]), 2)
        self.assertEqual((ready / "hunters" / "userdata0000").read_bytes(), previous_solo)
        self.assertFalse((ready / "hunters" / "interrupted.bbtmp").exists())
        self.assertEqual((self.root / "savedata_party" / "party.txt").read_bytes(), previous_party)
        self.assertEqual((self.root / "savedata" / "hunters" / "userdata0000").read_bytes(), previous_solo)

    def test_existing_quarantines_are_never_overwritten(self):
        first = stage_snapshot(self.root, "solo")
        second = stage_snapshot(self.root, "party")
        self.assertNotEqual(first, second)
        self.assertEqual(verify_snapshot(first)["source_kind"], "solo")
        self.assertEqual(verify_snapshot(second)["source_kind"], "party")
        self.assertEqual((self.root / "savedata_party" / "party.txt").read_text(),
                         "private test party")

    def test_tampering_and_extra_files_rejected(self):
        ready = stage_snapshot(self.root, "solo")
        (ready / "hunters" / "userdata0000").write_bytes(b"same-size corrupt" + b"x" * 230)
        with self.assertRaises(SnapshotError):
            verify_snapshot(ready)
        ready2 = stage_snapshot(self.root, "solo")
        (ready2 / "unmanifested.txt").write_text("not an approved snapshot file")
        with self.assertRaises(SnapshotError):
            verify_snapshot(ready2)
        ready3 = stage_snapshot(self.root, "solo")
        m = ready3 / MANIFEST
        d = json.loads(m.read_text())
        d["files"][0]["path"] = "../outside"
        m.write_text(json.dumps(d))
        with self.assertRaises(SnapshotError):
            verify_snapshot(ready3)

    def test_empty_sources_do_not_create_quarantine(self):
        for file in (self.root / "savedata").rglob("*"):
            if file.is_file():
                file.unlink()
        with self.assertRaisesRegex(SnapshotError, "no complete"):
            stage_snapshot(self.root, "solo")
        self.assertFalse((self.root / "save_backups").exists())

    def test_rejects_symlink_source_or_snapshot(self):
        other = self.root / "other"
        other.mkdir()
        symlink = self.root / "savedata" / "hunters" / "outside-link"
        try:
            symlink.symlink_to(other, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted in this Windows runner")
        with self.assertRaises(SnapshotError):
            stage_snapshot(self.root, "solo")
        symlink.unlink()
        ready = stage_snapshot(self.root, "solo")
        (ready / "hunters" / "outside-link").symlink_to(other, target_is_directory=True)
        with self.assertRaises(SnapshotError):
            verify_snapshot(ready)

    def test_locked_or_broken_copy_preserves_every_active_source(self):
        active_solo = (self.root / "savedata" / "hunters" / "userdata0000")
        before = active_solo.read_bytes()
        active_party = (self.root / "savedata_party" / "party.txt")
        party_before = active_party.read_bytes()
        import port_save_quarantine as mod

        real = mod._copy_one
        calls = 0

        def fail_after_one(source, dest):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise PermissionError("simulated antivirus lock / copy error")
            return real(source, dest)

        with mock.patch.object(mod, "_copy_one", side_effect=fail_after_one):
            with self.assertRaises(PermissionError):
                stage_snapshot(self.root, "solo")
        self.assertEqual(active_solo.read_bytes(), before)
        self.assertEqual(active_party.read_bytes(), party_before)
        staging_root = self.root / "save_backups" / "ultimate_quarantine"
        self.assertEqual(list(staging_root.glob("*")), [])
        # A prior completed snapshot also stays intact after a later failure.
        prior = stage_snapshot(self.root, "solo")
        with mock.patch.object(mod, "_copy_one", side_effect=PermissionError("disk full")):
            with self.assertRaises(PermissionError):
                stage_snapshot(self.root, "party")
        self.assertEqual(verify_snapshot(prior)["source_kind"], "solo")

    def test_post_promotion_verification_failure_removes_only_new_candidate(self):
        import port_save_quarantine as mod
        old_ready = stage_snapshot(self.root, "solo")
        real_verify = mod.verify_snapshot

        def fail_promoted(candidate):
            if candidate == old_ready:
                return real_verify(candidate)
            raise SnapshotError("simulated manifest validation failure")

        with mock.patch.object(mod, "verify_snapshot", side_effect=fail_promoted):
            with self.assertRaisesRegex(SnapshotError, "simulated"):
                stage_snapshot(self.root, "party")
        self.assertEqual(real_verify(old_ready)["source_kind"], "solo")
        self.assertEqual(list(old_ready.parent.glob("*.ready")), [old_ready])
        self.assertEqual((self.root / "savedata_party" / "party.txt").read_text(),
                         "private test party")

    def test_backup_parent_symlink_is_not_followed(self):
        outside = self.root / "external"
        outside.mkdir()
        root = self.root / "save_backups"
        try:
            root.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted in this Windows runner")
        with self.assertRaises(SnapshotError):
            stage_snapshot(self.root, "solo")
        self.assertEqual(list(outside.iterdir()), [])

    def test_source_changes_mid_copy_are_rejected(self):
        import port_save_quarantine as mod
        real = mod._copy_one

        def mutate_after_first(source, dest):
            digest = real(source, dest)
            if source.name == "userdata0000":
                source.write_bytes(b"changed while scan runs")
            return digest
        with mock.patch.object(mod, "_copy_one", side_effect=mutate_after_first):
            with self.assertRaises(SnapshotError):
                stage_snapshot(self.root, "solo")
        self.assertEqual(list((self.root / "save_backups" /
                               "ultimate_quarantine").glob("*.ready")), [])

    def test_forged_manifest_never_escapes_quarantine(self):
        ready = stage_snapshot(self.root, "solo")
        manifest = ready / MANIFEST
        obj = json.loads(manifest.read_text())
        obj["files"][0]["path"] = "/tmp/unsafe"
        manifest.write_text(json.dumps(obj))
        with self.assertRaises(SnapshotError):
            verify_snapshot(ready)
        obj["files"][0]["path"] = "..\\..\\malicious"
        manifest.write_text(json.dumps(obj))
        with self.assertRaises(SnapshotError):
            verify_snapshot(ready)


if __name__ == "__main__":
    unittest.main()
