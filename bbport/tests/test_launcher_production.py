"""B36: production release metadata still gates engine debug extras, but a co-op
release now presents offline-only built-in cheat selections. Actual game patch
selection refuses them on any online launch (B35), independent of build_info."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))

if sys.platform == 'win32':
    import bbport_launcher_win as launcher


@unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
class ProductionBuildTests(unittest.TestCase):
    def install(self, text=None):
        root = Path(tempfile.mkdtemp())
        (root / 'scripts').mkdir()
        if text is not None:
            (root / 'scripts' / 'build_info.json').write_text(text, encoding='utf-8')
        return root

    def test_the_mark_makes_a_release(self):
        self.assertTrue(launcher.production_build(self.install('{"production": true}\n')))

    def test_no_mark_or_another_is_a_dev_build(self):
        for text in (None, '{"production": false}', '[]', 'not json'):
            with self.subTest(text=text):
                self.assertFalse(launcher.production_build(self.install(text)))

    def test_this_checkout_is_a_dev_build(self):
        self.assertFalse(launcher.PRODUCTION)

    def test_the_hidden_extras_are_the_debug_tools(self):
        keys = {key for key, _title, _on in launcher.EXTRAS}
        self.assertEqual(set(launcher.DEV_TOOL_EXTRAS), keys & {'debug_camera', 'debug_menu'})

    def test_offline_ui_keeps_all_known_cheats_and_online_patch_selector_is_independent(self):
        self.assertIn('cheat_no_death', {key for key, _title, _on in launcher.CHEATS})
        self.assertIn('cheat_rally_no_decay', {key for key, _title, _on in launcher.CHEATS})
        source = Path(launcher.__file__).read_text(encoding='utf-8')
        production = source.split('def build_cheats(self):', 1)[1].split('def build_online(self):', 1)[0]
        self.assertIn("if PRODUCTION:", production)
        self.assertIn("for key, title, _on in CHEATS:", production)
        self.assertIn("for key, title, _on in TWEAKS:", production)
        self.assertIn("self.play_coop_offline", source)



if __name__ == '__main__':
    unittest.main()
