"""B35: actual production patch selector must follow OFFLINE/ONLINE launch mode.

No proprietary Bloodborne image, game save, GUI or running server is used.
The imported module is the real bbport/scripts/patches.py from this checkout.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import patches


class OfflineOnlinePatchSelection(unittest.TestCase):
    def test_online_mode_is_from_launch_environment_not_release_channel(self):
        self.assertFalse(patches.online_game({}))
        self.assertFalse(patches.online_game({"BB_ONLINE": "0"}))
        self.assertTrue(patches.online_game({"BB_ONLINE": "1"}))
        self.assertTrue(patches.online_game({"SHADPS4_BLOODBORNE_SEAMLESS_COOP": "1"}))
        self.assertTrue(patches.online_game({"BB_ONLINE": "0", "SHADPS4_BLOODBORNE_SEAMLESS_COOP": "1"}))
        self.assertFalse(patches.online_game({"BB_ONLINE": "true"}))

    def test_release_offline_cheats_return_but_unchanged_tweaks_stay_online(self):
        choices = {"cheat_no_death": "1", "cheat_silent": "1",
                   "cheat_rally_no_decay": "1", "debug_camera": "1",
                   "tweak_camera_distance": "1", "tweak_ragdoll": "1",
                   "tweak_no_rally": "0"}
        offline = patches.effect_patches(choices, production=True, online=False)
        online_release = patches.effect_patches(choices, production=True, online=True)
        online_dev = patches.effect_patches(choices, production=False, online=True)
        for patch in ("Player No Dead (Read note)", "Player Silent (Read note)",
                      "No Rally Decay", "Restore Debug Camera"):
            self.assertIn(patch, offline)
            self.assertNotIn(patch, online_release)
            self.assertNotIn(patch, online_dev)
        for patch in ("Increased camera distance", "DS1-like physics"):
            self.assertIn(patch, offline)
            self.assertIn(patch, online_release)
            self.assertIn(patch, online_dev)

    def test_saved_offline_toggle_cannot_be_reactivated_in_online_launch(self):
        enabled = {key: "1" for key in patches.DEV_TOOL_KEYS}
        with mock.patch.dict(os.environ, {"BB_ONLINE": "1"}, clear=True):
            forbidden = set(patches.OFFLINE_TOOL_PATCH_NAMES)
            selected = patches.effect_patches(enabled, production=True)
            self.assertFalse(forbidden.intersection(selected))
        with mock.patch.dict(os.environ, {"BB_ONLINE": "0"}, clear=True):
            selected = patches.effect_patches({"cheat_stealth": "1"}, production=True)
            self.assertIn("Player Stealth (Read note)", selected)

    def test_seamless_coop_flag_also_forbids_cheats_even_without_bb_online(self):
        with mock.patch.dict(os.environ, {"SHADPS4_BLOODBORNE_SEAMLESS_COOP": "1"}, clear=True):
            self.assertNotIn("Player No Dead (Read note)",
                             patches.effect_patches({"cheat_no_death": "1"}, production=False))

    def test_extra_patch_names_and_relabelled_entries_cannot_revive_known_cheats(self):
        names = ["60 FPS++", "No Rally Decay", "Player No Dead (Read note)",
                 "Increased camera distance", "Restore Debug Menu (READ NOTES)",
                 "No Rally Decay", "Unrelated safe-by-policy name"]
        self.assertEqual(patches.filter_online_dev_patches(names, online=True),
                         ["60 FPS++", "Increased camera distance", "Unrelated safe-by-policy name"])
        self.assertEqual(patches.filter_online_dev_patches(names, online=False), names)
        # Unknown external-code names are NOT magically classified as safe
        # by this gate. A separate reviewed mod policy remains mandatory.

    def test_patch_file_pipeline_filters_both_extra_and_external_known_names(self):
        source = (ROOT / "scripts" / "patches.py").read_text(encoding="utf-8")
        self.assertIn("names=filter_online_dev_patches(names)", source)
        self.assertIn("external=[entry for entry in external if entry[0] in allowed]", source)
        self.assertLess(source.index("names=filter_online_dev_patches(names)"),
                        source.index("names=validate_patch_requirements(names,a.game_dir)"))

    def test_windows_launcher_offline_scrubs_inherited_online_credentials(self):
        source = (ROOT / "launcher" / "bbport_launcher_win.py").read_text(encoding="utf-8")
        start = source.index("    for old in ('BB_ONLINE', 'SHADPS4_BLOODBORNE_SEAMLESS_COOP',")
        end = source.index("    if s.get('online'):", start)
        scrub = source[start:end]
        self.assertIn("env.pop(old, None)", scrub)
        self.assertIn("'BB_SHADNET_PASSWORD'", scrub)
        self.assertIn("'BB_SHADNET_SERVER_KEY'", scrub)
        self.assertIn("env['BB_ONLINE'] = '1'", source[end:end + 220])
        coop = (ROOT / "launcher" / "bbport_coop.py").read_text(encoding="utf-8")
        self.assertIn("'SHADPS4_BLOODBORNE_SEAMLESS_COOP': '1'", coop)


if __name__ == "__main__":
    unittest.main()
