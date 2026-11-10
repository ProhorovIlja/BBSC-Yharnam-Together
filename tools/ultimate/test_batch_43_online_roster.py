"""B43 source-level contract for selected-server population and roster UX.

Real C++ integration uses server/tests/test_team_lobby.cpp; the full Docker
CTest job actually recompiles the protobuf, server and team tests. No network.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class HuntersOnlineRosterSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proto = (ROOT / "server/coop/coop.proto").read_text(encoding="utf-8")
        cls.lobby = (ROOT / "server/coop/team_lobby.cpp").read_text(encoding="utf-8")
        cls.client = (ROOT / "bbport/gpu/bbcoop/coop.cpp").read_text(encoding="utf-8")
        cls.header = (ROOT / "bbport/gpu/bbcoop.h").read_text(encoding="utf-8")
        cls.overlay = (ROOT / "bbport/gpu/shim/bbport_overlay.cpp").read_text(encoding="utf-8")
        cls.tests = (ROOT / "server/tests/test_team_lobby.cpp").read_text(encoding="utf-8")

    def test_authoritative_count_cannot_be_capped_list_size(self):
        self.assertIn("uint32 online_count = 16;", self.proto)
        self.assertIn("bool online_count_known = 17;", self.proto)
        fn = self.lobby.split("bbcoop::LobbyState TeamLobby::StateFor(", 1)[1]
        self.assertIn("state.set_online_count(static_cast<u32>(players.size()))", fn)
        self.assertIn("state.set_online_count_known(true)", fn)
        self.assertIn("lobby_players", fn)
        self.assertIn("ServerPopulationDoesNotEqualTruncatedList", self.tests)
        self.assertIn("first.online_count() == 23", self.tests)
        self.assertIn("first.players_size() <= 2", self.tests)
        self.assertIn("online_count() == 22", self.tests)

    def test_old_server_unknown_not_fake_zero(self):
        self.assertIn("int online_count_known;", self.header)
        self.assertIn("state->online_count_known() ? 1 : 0", self.client)
        self.assertIn("lobby.online_count_known", self.overlay)
        self.assertIn("T(\"unknown\", \"нет данных\")", self.overlay)

    def test_actual_clickable_in_game_browser_without_misleading_full_list(self):
        for code in ("struct PlayersPage", "void DrawPlayersPage(",
                     "OpenPlayersPage()", '"players_open"',
                     '"players_next"', '"players_prev"',
                     '"##players_filter"', '"players_close"',
                     '"players_find"', "LobbyRows::MayInvite(",
                     "players_page.typing", "Team::players_page.open = false;"):
            self.assertIn(code, self.overlay)
        self.assertIn("std::vector<const bbcoop_lobby_entry*> listed;", self.overlay)
        self.assertIn("lobby.player_count", self.overlay)
        self.assertIn("lobby.member_count", self.overlay)
        self.assertIn("std::to_string(lobby.online_count)", self.overlay)
        self.assertNotIn('state.set_online_count(static_cast<u32>(state.players_size()))',
                         self.lobby)


if __name__ == "__main__":
    unittest.main()
