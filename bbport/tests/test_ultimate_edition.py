# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline contracts for separate Ultimate Windows TEST edition."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bbport" / "launcher"))
import bbport_coop as coop


def release(tag, draft=False, sum_present=True):
    name = "YharnamTogether-" + tag + "-setup.exe"
    assets = [{"name": name, "browser_download_url": "https://example.test/" + name}]
    if sum_present:
        assets.append({"name": name + ".sha256", "browser_download_url": "https://example.test/sum"})
    return {"tag_name": tag, "draft": draft, "assets": assets}


class TestEdition(unittest.TestCase):
    def test_repository_and_tag_pinning(self):
        self.assertIn("repositories/1450213757/releases?", coop.RELEASES_API)
        self.assertNotIn("repositories/1405692683/releases?", coop.RELEASES_API)
        for tag in ("v1.4.0-test.1", "v2.0.0-test.22"):
            self.assertIsNotNone(coop.TEST_EDITION_TAG.fullmatch(tag))
        for tag in ("v1.4.0", "v9.9.9", "v1.4.0-test", "v1.4.0-test.2-extra"):
            self.assertIsNone(coop.TEST_EDITION_TAG.fullmatch(tag))

    def test_only_verified_edition_updates(self):
        updates = [release("v9.9.9"), release("v1.4.0-test.3", draft=True),
                   release("v1.4.0-test.2"), release("v1.4.0-test.1")]
        with mock.patch.object(coop, "fetch_releases", return_value=updates):
            self.assertEqual(coop.fetch_newest_release()["version"], "1.4.0-test.2")
        with mock.patch.object(coop, "fetch_releases",
                               return_value=[release("v1.4.0-test.9", sum_present=False)]):
            self.assertIsNone(coop.fetch_newest_release())
        with mock.patch.object(coop, "fetch_releases", return_value={"message": "rate limit"}):
            with self.assertRaises(ValueError):
                coop.fetch_newest_release()

    def test_portable_marker_survives_update(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "portable.txt").write_text("TEST", encoding="utf-8")
            self.assertIn("/PORTABLE=1", coop.setup_command(root / "update.exe", root))
            (root / "portable.txt").unlink()
            self.assertNotIn("/PORTABLE=1", coop.setup_command(root / "update.exe", root))

    def test_installer_is_separate(self):
        script = (ROOT / "tools/release/setup.iss").read_text(encoding="utf-8")
        self.assertIn("AppId={{49B8B926-DC94-4371-B4B7-729839E6E32E}", script)
        self.assertNotIn("6E0B4C2A-3F7D-4B8E-9A51-2C8D7E4F1B63", script)
        self.assertIn('#define ShortName "BBSC Yharnam Together TEST"', script)
        builder = (ROOT / "tools/make-release.ps1").read_text(encoding="utf-8")
        self.assertIn("Experimental edition requires a version", builder)
        self.assertIn('$top = "BBSC Yharnam Together TEST/"', builder)
        self.assertIn("Get-FileHash -Algorithm SHA256", builder)

    def test_launcher_edition_is_visible_and_isolated(self):
        launcher = (ROOT / "bbport/launcher/bbport_launcher_win.py").read_text(encoding="utf-8")
        for required in ("'bbsc-yharnam-test'", "'bloodborne-sh-test-update'",
                         "text=' TEST '", "BBSC: Yharnam Together TEST",
                         "if (PORT_DIR / 'portable.txt').is_file()"):
            self.assertIn(required, launcher)

    def test_launcher_version_resource_and_release_audit_are_test_only(self):
        import tempfile
        import sys
        sys.path.insert(0, str(ROOT / "bbport" / "packaging" / "windows"))
        sys.path.insert(0, str(ROOT / "tools" / "release"))
        import version_info
        import check_release
        content = version_info.text("1.4.0-test.1")
        self.assertIn("BBSC: Yharnam Together TEST", content)
        self.assertIn("ProhorovIlja/BBSC-Yharnam-Together", content)
        self.assertNotIn("Amanises-Yharnam-Together", content)
        self.assertEqual(check_release.LAUNCHER_PRODUCT, "BBSC: Yharnam Together TEST")
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "BLauncher.exe"
            marker = "VS_VERSION_INFO".encode("utf-16-le")
            original = "Yharnam Together: Bloodborne Seamless Co-op".encode("utf-16-le")
            file.write_bytes(marker + original)
            self.assertTrue(check_release.launcher_problems(file))
            file.write_bytes(marker + check_release.LAUNCHER_PRODUCT.encode("utf-16-le"))
            self.assertEqual(check_release.launcher_problems(file), [])
            file.write_bytes(file.read_bytes() + b"UPX0\x00")
            self.assertTrue(check_release.launcher_problems(file))

    def test_dlss_free_release_is_explicit_and_never_partial(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools" / "release"))
        import check_release
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            normal = check_release.check(root)
            self.assertTrue(any("bin/bbport_dlss.dll" in p for p in normal))
            self.assertTrue(any("bin/nvngx_dlss.dll" in p for p in normal))
            optional = check_release.check(root, without_dlss=True)
            self.assertFalse(any("DLSS" in p or "dlss" in p for p in optional))
            (root / "bin").mkdir()
            (root / "bin" / "nvngx_dlss.dll").write_bytes(b"synthetic dll placeholder")
            partial = check_release.check(root, without_dlss=True)
            self.assertTrue(any("partial DLSS runtime" in p for p in partial))
            for dll in ("bbport_dlss.dll", "nvngx_dlssg.dll"):
                (root / "bin" / dll).write_bytes(b"synthetic dll placeholder")
            full = check_release.check(root, without_dlss=True)
            self.assertFalse(any("partial DLSS runtime" in p for p in full))


if __name__ == "__main__":
    unittest.main()
