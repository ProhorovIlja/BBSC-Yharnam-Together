"""B47 source-level guard: local Unicode-aware Hunters browser filtering.

The C++20 standalone integration test exercises actual utf-8 and malformed
bytes. Source inspection verifies real overlay routing uses this function.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class UnicodeHuntersBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overlay = (ROOT / "bbport/gpu/shim/bbport_overlay.cpp").read_text(encoding="utf-8")
        cls.header = (ROOT / "bbport/gpu/bbcoop/roster_filter.h").read_text(encoding="utf-8")
        cls.test = (ROOT / "bbport/gpu/bbcoop/tests/test_roster_filter.cpp").read_text(encoding="utf-8")

    def test_real_players_page_uses_fold_but_identity_remains_account_id(self):
        page = self.overlay.split("void DrawPlayersPage(", 1)[1].split(
            "void SyncChatAudience(", 1)[0]
        self.assertIn('#include "../bbcoop/roster_filter.h"', self.overlay)
        self.assertIn("BbRoster::FoldPlayerSearch(players_page.filter)", page)
        self.assertIn("BbRoster::FoldPlayerSearch(player->name).find(query)", page)
        self.assertIn("BbRoster::AppendUniqueOnline(listed, lobby.members[i]", page)
        self.assertIn("BbRoster::AppendUniqueOnline(listed, lobby.players[i]", page)
        self.assertIn("const bool self = p.id[0] && lobby.me[0]", page)
        self.assertNotIn("std::tolower(static_cast<unsigned char>(c))", page)

    def test_explicit_casefold_subset_without_locale_or_third_party_plugins(self):
        for token in ("FoldPlayerSearch(", "std::string_view", "0x0410",
                      "0x040F", "0x0391", "0x00C0", "0x03C2",
                      "out.reserve(source.size())", "if (!valid"):
            self.assertIn(token, self.header)
        for token in ("ОХОТНИК", "ёжик", "ÉLITE", "ΑΘΗΝΑ",
                      "std::string damaged", "std::string unfinished"):
            self.assertIn(token, self.test)

    def test_no_privacy_or_network_semantic_changes(self):
        self.assertIn("bbcoop_lobby_request(BBCOOP_TEAM_SEARCH, friends.query);", self.overlay)
        self.assertIn("player->name", self.overlay)
        self.assertIn("player.id[0]", self.header if "player.id[0]" in self.header else
                      (ROOT / "bbport/gpu/bbcoop/roster_dedup.h").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
