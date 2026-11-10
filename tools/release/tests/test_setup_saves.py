# SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""B50: the setup itself must never copy into, remove or rename player saves.

An upstream #554 user report coincided with an update. Its actual cause was
not proven to be the installer, so this is a defense-in-depth source guard:
even a broken *staged* release must not overwrite user/ and savedata/.
Do not open an actual user's files or run the installer during these tests.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
SETUP = ROOT / "tools/release/setup.iss"


def sections(text):
    blocks, current = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.fullmatch(r"\[([A-Za-z]+)\]", line)
        if m:
            current = m.group(1).lower()
            blocks.setdefault(current, [])
        elif current is not None and line and not line.startswith(";"):
            blocks[current].append(line)
    return blocks


class SetupMustNotTouchUserSaves(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contents = SETUP.read_text(encoding="utf-8-sig")
        cls.blocks = sections(cls.contents)

    def test_install_file_entries_exclude_user_owned_state(self):
        files = self.blocks.get("files", [])
        self.assertTrue(files, "No [Files] entries to protect")
        for line in files:
            if not re.search(r"\bSource\s*:", line, re.I):
                continue
            excludes = re.search(r'\bExcludes:\s*"([^"]*)"', line, re.I)
            self.assertIsNotNone(excludes, "Source entry has no savedata exclusion: " + line)
            patterns = {p.strip().casefold() for p in excludes.group(1).split(",")}
            for name in ("user", "savedata"):
                self.assertIn(fr"\{name}\*", patterns, line)
            for setting in ("bbport.ini", "mods.json", "patches.json"):
                self.assertIn(setting, patterns, line)
            dest = re.search(r'\bDestDir:\s*"([^"]*)"', line, re.I)
            self.assertIsNotNone(dest, line)
            self.assertEqual(dest.group(1).lower(), "{app}")

    def test_no_delete_sections_touch_files_or_saves(self):
        for section_name in ("installdelete", "uninstalldelete"):
            for line in self.blocks.get(section_name, []):
                m = re.search(r'\bName:\s*"([^"]*)"', line, re.I)
                self.assertIsNotNone(m, line)
                destination = m.group(1).lower()
                self.assertTrue(
                    destination.startswith(r"{autoprograms}" + "\\") or
                    destination.startswith(r"{autodesktop}" + "\\"),
                    f"{section_name} removes non-shortcut: {line}"
                )
                for part in re.split(r"[\\/]", destination):
                    self.assertNotIn(part, ("user", "savedata"))

    def test_pascal_script_never_deletes_saves(self):
        contents = "\n".join(self.blocks.get("code", []))
        for destructive in ("DelTree", "DeleteFile", "RemoveDir", "RenameFile"):
            self.assertNotRegex(contents, rf"\b{destructive}\s*\(")

    def test_release_check_also_blocks_private_user_dirs(self):
        check = (ROOT / "tools/release/check_release.py").read_text(encoding="utf-8")
        self.assertIn("PLAYER_FOLDERS", check)
        self.assertIn('"user"', check)
        self.assertIn('"savedata"', check)

    def test_launcher_uninstall_only_cleans_generated_artifacts(self):
        import ast
        coop = (ROOT / "bbport/launcher/bbport_coop.py").read_text(encoding="utf-8")
        module = ast.parse(coop)
        made = next(
            ast.literal_eval(node.value)
            for node in module.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "MADE_FOLDERS"
                    for t in node.targets)
        )
        self.assertEqual(set(made), {"out", "event-patch"})
        self.assertTrue(set(made).isdisjoint({"user", "savedata", "coop-game"}))
        uninstall = coop.split("def uninstall(install):", 1)[1].split(
            "\ndef view_roots(", 1
        )[0]
        self.assertIn("for name in MADE_FOLDERS:", uninstall)
        self.assertIn("remove_tree(install / name)", uninstall)
        self.assertNotIn("remove_tree(install / 'user')", uninstall)
        self.assertNotIn("remove_tree(install / 'savedata')", uninstall)

    def test_negative_fixture_detects_an_unprotected_staged_release(self):
        poisoned = self.contents.replace(
            r"\user\*,\savedata\*", "", 1
        )
        self.assertNotEqual(poisoned, self.contents)
        file_line = next(x for x in sections(poisoned)["files"] if "Excludes:" in x)
        patterns = set(file_line.split('Excludes: "', 1)[1].split('"', 1)[0].split(","))
        self.assertNotIn(r"\user\*", patterns)
        self.assertNotIn(r"\savedata\*", patterns)


if __name__ == "__main__":
    unittest.main()
