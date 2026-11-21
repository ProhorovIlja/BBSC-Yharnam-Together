# SPDX-License-Identifier: GPL-2.0-or-later
"""Display-free regression for status redraw and launcher Tk setters."""
import ast
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "bbport/launcher/bbport_launcher_win.py"
sys.path.insert(0, str(SOURCE.parent))
if sys.platform == "win32":
    import bbport_launcher_win as launcher


class SourceSyntax(unittest.TestCase):
    def test_main_launcher_parses_without_tk_or_windows_runtime(self):
        ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))


@unittest.skipUnless(sys.platform == "win32", "Windows launcher requires Windows APIs")
class PaintWorkTests(unittest.TestCase):
    def test_status_line_coalesces_identical_text_spinner_and_wrap(self):
        line = launcher.StatusLine.__new__(launcher.StatusLine)
        line.ui = types.SimpleNamespace(px=lambda n: n)
        line.text, line.glyph, line.spinner = mock.Mock(), mock.Mock(), mock.Mock()
        line._text_state = line._glyph_state = None
        line._busy = False
        line.wraplength = 240
        for width in (244, 244, 500, 500):
            line.wrap(types.SimpleNamespace(width=width))
        line.text.configure.assert_called_once_with(wraplength=496)
        line.text.configure.reset_mock()
        for _ in range(50):
            line.set("Checking", busy=True)
        line.text.configure.assert_called_once_with(text="Checking", fg=launcher.TEXT)
        line.spinner.start.assert_called_once()
        line.glyph.pack_forget.assert_called_once()
        line.text.configure.reset_mock()
        for _ in range(50):
            line.set("✓ Ready")
        line.spinner.stop.assert_called_once()
        line.glyph.pack.assert_called_once()
        self.assertEqual(line.text.configure.call_count, 1)
        self.assertEqual(line.glyph.configure.call_count, 1)
        line.set("Loading", busy=True)
        line.set("✓ Ready")
        self.assertEqual(line.spinner.start.call_count, 2)
        self.assertEqual(line.spinner.stop.call_count, 2)

    def test_card_hover_cache_skips_same_computed_color(self):
        card = mock.Mock()
        card.glow = 0
        card.corners = [mock.Mock(), mock.Mock()]
        card._glow_colors = (None, None)
        app = types.SimpleNamespace(
            tk=types.SimpleNamespace(TclError=RuntimeError),
            cards=set(), hot_card=None,
        )
        for _ in range(40):
            launcher.Launcher.light(app, card, 0.5)
        card.configure.assert_called_once()
        for corner in card.corners:
            corner.itemconfigure.assert_called_once()
        launcher.Launcher.light(app, card, 0.75)
        self.assertEqual(card.configure.call_count, 2)
        for corner in card.corners:
            self.assertEqual(corner.itemconfigure.call_count, 2)

    def test_flow_wrap_recomputes_only_when_label_width_changes(self):
        label = mock.Mock()
        app = types.SimpleNamespace(
            label=mock.Mock(return_value=label),
            px=lambda n: n,
        )
        launcher.Launcher.flow(app, None, "Text")
        callback = label.bind.call_args.args[1]
        for width in (84, 84, 84, 200, 200, 200):
            callback(types.SimpleNamespace(width=width))
        self.assertEqual(label.configure.call_args_list,
                         [mock.call(wraplength=80), mock.call(wraplength=196)])


if __name__ == "__main__":
    unittest.main()
