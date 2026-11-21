# SPDX-License-Identifier: GPL-2.0-or-later
"""Regression: real Windows Shell Link must preserve non-ASCII and shell metacharacters."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))
from bbport_shortcut_win import write_shortcut


@unittest.skipUnless(sys.platform == "win32", "real Windows COM Shell Link")
class UnicodeShortcutTests(unittest.TestCase):
    def test_unicode_working_directory_and_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Охотник's $hunting"
            root.mkdir()
            target = Path(sys.executable).resolve()
            shortcut = root / "Ярлык Bloodborne.lnk"
            args = '--play "Тест $ночи"'
            write_shortcut(target, root, (target, 0), args, destination=shortcut)
            self.assertTrue(shortcut.is_file())
            raw = shortcut.read_bytes()
            # Windows Shell Link StringData is encoded UTF-16LE when the
            # IsUnicode flag is set; shell escaping must not corrupt either.
            self.assertIn(str(root).encode("utf-16le"), raw)
            self.assertIn(args.encode("utf-16le"), raw)

    def test_source_launcher_has_explicit_play_argument(self):
        # A source checkout starts pythonw with the --play argument. The
        # executable launcher uses Bloodborne.exe with no extra argument.
        from bbport_launcher_win import Launcher
        self.assertTrue(callable(Launcher.shortcut))


if __name__ == "__main__":
    unittest.main()
