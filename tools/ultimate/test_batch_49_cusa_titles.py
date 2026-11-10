"""B49: all nine legitimate Bloodborne 1.09 editions enable source-level co-op.

The launcher and game-check already accepted these titles; previously game
runtime refused all but CUSA03173 even with the same 1.09 executable, leaving
a flashing placeholder party HUD. Test never distributes or opens game assets.
"""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


def assigned_tuple(path, symbol):
    tree = ast.parse(source(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == symbol for t in node.targets
        ):
            return tuple(ast.literal_eval(node.value))
    raise AssertionError(f"{symbol} not found in {path}")


class NineRegionalRetailTitles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = source("emulator/src/core/bloodborne_titles.h")
        cls.patches = source("emulator/src/core/bloodborne_patches.cpp")
        cls.join = source("emulator/src/core/bloodborne_join.cpp")
        cls.tracer = source("emulator/src/core/bloodborne_re_tracer.cpp")
        cls.test = source("emulator/tests/bloodborne/test_bloodborne_titles.cpp")
        cls.cmake = source("emulator/tests/CMakeLists.txt")

    def test_cusa_catalog_matches_both_launcher_and_game_check(self):
        catalog = self.header.split("RetailTitles{", 1)[1].split("};", 1)[0]
        titles = re.findall(r'"(CUSA\d{5})"', catalog)
        self.assertEqual(len(titles), 9)
        self.assertEqual(len(set(titles)), 9)
        self.assertEqual(sorted(titles), sorted(assigned_tuple(
            "bbport/launcher/bbport_coop.py", "TITLE_IDS")))
        self.assertEqual(sorted(titles), sorted(assigned_tuple(
            "bbport/scripts/game_check.py", "SUPPORTED_TITLES")))
        self.assertIn("CUSA00900", titles)
        self.assertIn("CUSA03173", titles)

    def test_real_patch_gate_accepts_all_editions_but_requires_site_bytes(self):
        gate = self.patches.split("bool IsSeamlessCoopGame()", 1)[1].split("\n}", 1)[0]
        self.assertIn("SeamlessCoopGameFor(MemoryPatcher::g_game_serial, app_version)", gate)
        self.assertIn("GetsSeamlessCoop(game)", gate)
        self.assertNotIn('g_game_serial != "CUSA03173"', gate)
        self.assertIn('CoopGame::OtherGame', gate)
        installer = self.patches.split("void InstallSeamlessCoopPatches()", 1)[1]
        self.assertIn("if (!IsSeamlessCoopGame())", installer)
        self.assertIn('CoopSitesMatch(base, image_size, "seamless core"', installer)
        self.assertIn("all of the core or none", installer.lower())
        self.assertIn("OtherVersion", self.header)

    def test_join_diagnostics_and_real_gtest_use_shared_edition_gate(self):
        for unit in (self.join, self.tracer):
            self.assertIn('#include "core/bloodborne_titles.h"', unit)
            self.assertIn("IsBloodborneTitle(MemoryPatcher::g_game_serial)", unit)
            self.assertNotIn('MemoryPatcher::g_game_serial != "CUSA03173"', unit)
        self.assertIn("bloodborne/test_bloodborne_titles.cpp", self.cmake)
        self.assertIn("TEST(Titles, EveryRetailReleaseIsBloodborne)", self.test)
        self.assertIn("TEST(Titles, UnrelatedOrMalformedIdsAreNeverBloodborne)", self.test)
        self.assertIn("TEST(Titles, WrongSfoVersionDoesNotBypassExecutableSiteChecks)", self.test)


if __name__ == "__main__":
    unittest.main()
