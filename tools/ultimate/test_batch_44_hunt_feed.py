"""B44 grounded server boss-victory events and team-chat UI source contracts.

The actual C++ server/Protobuf tests run in a separate isolated Docker job.
The native UI still needs a clean Windows compile/runtime and real game trial.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


class BossVictoryFeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = source("server/coop/boss_victories.h")
        cls.game = source("emulator/src/core/bloodborne_map.cpp")
        cls.world = source("server/src/bloodborne_world.cpp")
        cls.proto = source("server/coop/coop.proto")
        cls.rig = source("server/tests/test_bloodborne_world.cpp")
        cls.client = source("emulator/src/core/bloodborne_server_world.cpp")
        cls.api = source("bbport/gpu/bbcoop/coop.cpp")
        cls.abi = source("bbport/gpu/bbcoop.h")
        cls.ui = source("bbport/gpu/shim/bbport_overlay.cpp")

    def test_game_and_server_use_identical_boss_progression_catalog(self):
        rows = set()
        part = self.game.split("std::span<const s32> AreaBossFlags(", 1)[1].split(
            "for (const Area& area)", 1)[0]
        for area, vals, count in re.findall(
                r"\{(0x[0-9a-f]+),\s*\{([\d,\s]+)\}\s*,\s*(\d+)\}", part):
            n = int(count)
            rows.update((int(area, 16), int(s)) for s in vals.split(",")[:n] if s.strip())
        catalog = {
            (int(a, 16), int(flag)) for a, flag in
            re.findall(r"\{(0x[0-9a-f]+)u,\s*(\d+)u\}", self.catalog)
        }
        self.assertEqual(len(rows), 16)
        self.assertEqual(catalog, rows)

    def test_authorized_host_known_live_map_transition_only(self):
        body = self.world.split("void Service::TakeWorld(", 1)[1].split(
            "void Service::TakeBoard(", 1)[0]
        for phrase in ("member.host", "world.host.MapState(map,", "before.map == map",
                       "WorldLogKind::MapFlagOn", "BossMapFlagIndex(map, entry.subject)",
                       "world.boss_notices_sent.insert(flag).second",
                       "AuthenticatedMember(member.online_id)",
                       "lobby.TeamOf(other.lobby) != team",
                       "event.set_kind(1)", "event.set_boss_flag(flag)"):
            self.assertIn(phrase, body)
        self.assertNotIn("set_from(member.name)", body)
        self.assertIn("BossVictoryAppearsExactlyOnceInsideTheRightTeam", self.rig)
        self.assertIn("other.chats.empty()", self.rig)

    def test_typed_events_bounded_client_inbox_and_c_bridge(self):
        for phrase in ("uint32 kind = 6;", "uint32 boss_flag = 7;"):
            self.assertIn(phrase, self.proto)
        self.assertIn("if (chat_inbox.size() >= 64) chat_inbox.pop_front()", self.client)
        self.assertIn("TakeTeamChatEvents(int most)", self.client)
        self.assertIn("SendTeamChatText(const std::string& text)", self.client)
        self.assertIn("TakeTeamChatEvents(int most)", source(
            "emulator/src/core/bloodborne_re_internal.h"))
        for phrase in ("bbcoop_chat_take(", "bbcoop_chat_send("):
            self.assertIn(phrase, self.api)
            self.assertIn(phrase, self.abi)

    def test_real_chat_ui_unread_boss_filters_and_status(self):
        for phrase in ('void PollChatEvents()', '"chat_open"', '"##team_chat_input"',
                       '"chat_send"', '"chat_boss_filter"', 'chat_page.unread',
                       '"chat_players"', '"chat_close"', 'void DrawChatPage(',
                       'Team::PollChatEvents()', 'chat_page.history.size() >= 64'):
            self.assertIn(phrase, self.ui)
        self.assertIn("BBCOOP_CHAT_BOSS_VICTORY", self.ui)
        self.assertIn('T("Your team defeated a boss", "Ваша команда победила босса")',
                      self.ui)
        self.assertIn("if (event.ack)", self.ui)
        self.assertIn("pending->refused = event.status != 0;", self.ui)


if __name__ == "__main__":
    unittest.main()
