# SPDX-License-Identifier: GPL-2.0-or-later
"""Headless regression for the actual Windows launcher Co-op -> 3D map callback.

Uses only the method's source AST and fake UI state; needs no game dump,
Tk display, real account, network connection, or installed Windows runtime.
The upstream PR #537 also supplies the real Windows GUI regression in
test_launcher_look.py; this test catches accidental omission on Linux CI.
"""
import ast
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace

LAUNCHER = Path(__file__).resolve().parents[1] / "launcher" / "bbport_launcher_win.py"


class Variable:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value


class HostCell:
    def __init__(self):
        self.visible = True

    def grid(self):
        self.visible = True

    def grid_remove(self):
        self.visible = False


class FakeApp:
    def __init__(self):
        self.coop_done = True
        self.coop_change_job = "previous"
        self.coop_vars = {
            "game": Variable(""),
            "server_type": Variable("local"),
            "host_ip": Variable("192.0.2.2"),
        }
        self.coop = {}
        self.coop_searching = True
        self.coop_host_cell = HostCell()
        self.map_refreshes = 0
        self.status_refreshes = 0
        self.step_refreshes = 0

    def refresh_map(self):
        self.map_refreshes += 1

    def coop_server_row_follows(self):
        pass

    def coop_show_step(self):
        self.step_refreshes += 1

    def coop_show_game(self):
        pass


def real_method_and_saves():
    source = LAUNCHER.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(LAUNCHER))
    matches = [node for node in ast.walk(tree)
               if isinstance(node, ast.FunctionDef) and node.name == "coop_changed"]
    if len(matches) != 1:
        raise AssertionError("Expected exactly one live coop_changed method")
    node = matches[0]
    lines = source.splitlines(keepends=True)
    function_source = textwrap.dedent("".join(lines[node.lineno - 1:node.end_lineno]))
    saves = []
    fake_coop = SimpleNamespace(save_settings=lambda location, state: saves.append(dict(state)),
                                is_this_pc=lambda ip: False)
    namespace = {"bbport_coop": fake_coop, "PORT_DIR": Path("/synthetic-test")}
    exec(compile(function_source, str(LAUNCHER), "exec"), namespace)
    return namespace["coop_changed"], saves


class GameFolderRefreshTests(unittest.TestCase):
    def test_map_refreshes_once_per_distinct_game_folder_not_for_other_fields(self):
        changed, saves = real_method_and_saves()
        app = FakeApp()
        app.map_game_seen = ""
        changed(app)
        self.assertEqual(app.map_refreshes, 0)

        app.coop_vars["game"].value = "C:/Bloodborne/CUSA03173"
        changed(app)
        self.assertEqual(app.map_refreshes, 1)
        self.assertEqual(app.map_game_seen, "C:/Bloodborne/CUSA03173")
        self.assertEqual(saves[-1]["game"], "C:/Bloodborne/CUSA03173")

        changed(app)
        app.coop_vars["host_ip"].value = "198.51.100.10"
        changed(app)
        self.assertEqual(app.map_refreshes, 1, "non-game edits must not redraw the map")

        app.coop_vars["game"].value = "D:/OtherGame"
        changed(app)
        self.assertEqual(app.map_refreshes, 2)
        self.assertEqual(saves[-1]["game"], "D:/OtherGame")
        self.assertEqual(app.coop_change_job, None)
        self.assertEqual(len(saves), 5)

    def test_no_updates_before_setup_is_ready(self):
        changed, saves = real_method_and_saves()
        app = FakeApp()
        del app.coop_done
        app.coop_vars["game"].value = "C:/Bloodborne"
        changed(app)
        self.assertEqual(app.map_refreshes, 0)
        self.assertEqual(saves, [])

    def test_public_server_choice_does_not_create_spurious_map_refresh(self):
        changed, saves = real_method_and_saves()
        app = FakeApp()
        app.map_game_seen = ""
        app.coop_vars["server_type"].value = "global"
        changed(app)
        self.assertEqual(app.map_refreshes, 0)
        self.assertEqual(app.coop["role"], "guest")
        self.assertFalse(app.coop_host_cell.visible)
        self.assertEqual(len(saves), 1)


if __name__ == "__main__":
    unittest.main()
