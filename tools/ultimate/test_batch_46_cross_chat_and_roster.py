"""B46: actual in-game player-browser dedup and cross-chat requirement ledger.

Always source-check real overlay integration rather than merely compiling an
unused helper. The separate portable C++ test covers collisions/double counts.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

class B46RosterAndHandoff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overlay = read("bbport/gpu/shim/bbport_overlay.cpp")
        cls.roster = read("bbport/gpu/bbcoop/roster_dedup.h")
        cls.cpp = read("bbport/gpu/bbcoop/tests/test_roster_dedup.cpp")
        cls.manifest = read("docs/ULTIMATE_CROSS_CHAT_SOURCE_MANIFEST.md")
        cls.requirements = read("docs/ULTIMATE_CROSS_CHAT_REQUIREMENTS_MASTER.md")

    def test_actual_browser_no_double_count(self):
        part = self.overlay.split("void DrawPlayersPage(",1)[1].split("void SyncChatAudience(",1)[0]
        self.assertIn("BbRoster::AppendUniqueOnline(listed, lobby.members[i]",part)
        self.assertIn("BbRoster::AppendUniqueOnline(listed, lobby.players[i]",part)
        self.assertIn("listed.size()",part)
        self.assertIn("lobby.online_count_known",part)
        self.assertNotIn("listed.push_back(&lobby.members[i])",part)
        self.assertNotIn("listed.push_back(&lobby.players[i])",part)
        self.assertIn("p.id[0] && lobby.me[0]",part)
        self.assertIn("if (!self && !in_my_team && p.id[0])",part)

    def test_same_display_name_distinct_accounts_never_merged(self):
        self.assertIn("std::strcmp(prior->id, player.id) == 0",self.roster)
        self.assertIn("if (player.id[0])",self.roster)
        self.assertIn("if (player.state == offline_state) return;",self.roster)
        self.assertIn("rows.size()==4",self.cpp)
        self.assertIn("rows[0]==&team_a",self.cpp)

    def test_historical_source_archive_complete_page_and_safe_index(self):
        self.assertIn("28 files", self.manifest)
        rows = re.findall(r"\| (HIST-\d{3}) \|", self.manifest)
        self.assertEqual(len(rows), 28)
        self.assertEqual(len(set(rows)), 28)
        self.assertIn("other unshared chats are not accessible", self.manifest.lower())
        self.assertNotIn("drive.google.com/file/d/", self.manifest)
        self.assertNotIn("docs.google.com/document/d/", self.requirements)
        self.assertNotIn("common-passwords.txt", self.manifest)

    def test_two_missions_and_all_high_priority_user_instructions_preserved(self):
        for s in ("Playab", "eboot", "Fornex", "LAN", "Henryk", "Iosefka",
                  "DBNO", "ActionEventInfo", "18", "Bloodtinge", "Arcane",
                  "quick match", "B46", "source", "updater", "Nightwatch",
                  "MOAL", "NPC", "Voice"):
            self.assertIn(s.lower(),self.requirements.lower())
        for p in ("#9", "#21", "#22", "#23", "#24", "#35", "#63", "#64",
                  "#69", "#70", "#72", "#73", "#79", "#80", "#93", "#95",
                  "#96", "#100", "#103"):
            self.assertIn(p,self.requirements)
        self.assertIn("Source-level CI",self.requirements)
        self.assertIn("not accessible",self.requirements)

if __name__ == "__main__":
    unittest.main()
