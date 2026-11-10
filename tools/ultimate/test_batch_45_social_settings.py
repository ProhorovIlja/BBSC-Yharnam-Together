"""B45 regression guards for persisted independent social/map settings, genuine
team-vitals levels and deterministic 18+ build labels. Source checks are NOT
a substitute for clean native GPU compilation or real two-client gameplay.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class SocialPrefs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = read("bbport/gpu/shim/bbport_settings.h")
        cls.settings = read("bbport/gpu/shim/bbport_settings.cpp")
        cls.overlay = read("bbport/gpu/shim/bbport_overlay.cpp")
        cls.map_abi = read("bbport/gpu/bbcoop.h")
        cls.bridge = read("bbport/gpu/bbcoop/coop.cpp")
        cls.game = read("emulator/src/core/bloodborne_party.cpp")
        cls.panel = read("emulator/src/core/bloodborne_party.h")
        cls.build = read("bbport/gpu/bbcoop/build_archetype.h")

    def test_in_game_settings_roundtrip_all_preference_keys(self):
        keys = (
            "social_chat", "social_boss_events", "map_teammates",
            "map_teammate_names", "roster_levels", "roster_latency",
            "roster_builds", "share_build_stats",
        )
        for key in keys:
            with self.subTest(key=key):
                self.assertIn("std::atomic<bool> " + key, self.header)
                self.assertIn('key == "' + key + '"', self.settings)
                self.assertIn('put("' + key + '"', self.settings)

    def test_local_map_visibility_not_server_network_or_self_marker(self):
        self.assertIn('Toggle("map_teammates"', self.overlay)
        self.assertIn('Toggle("map_teammate_names"', self.overlay)
        self.assertIn('if (BbSettings::Get().map_teammates)', self.overlay)
        self.assertIn('BbSettings::Get().map_teammate_names ||', self.overlay)
        self.assertIn('if (view.has_me && view.map != 0)', self.overlay)
        self.assertIn('PlayerMark(draw, frame.At(view.map, view.x, view.z, view.y));',
                      self.overlay)
        self.assertIn('if (BbSettings::Get().map_teammate_names) caption = name;', self.overlay)

    def test_independent_chat_and_boss_feed_off_drops_backlog(self):
        self.assertIn('Toggle("social_chat"', self.overlay)
        self.assertIn('Toggle("social_boss_events"', self.overlay)
        self.assertIn('if (event.kind == BBCOOP_CHAT_TEXT && !BbSettings::Get().social_chat)',
                      self.overlay)
        self.assertIn('if (event.kind == BBCOOP_CHAT_BOSS_VICTORY && !BbSettings::Get().social_boss_events)',
                      self.overlay)
        self.assertIn('if (chat_enabled && (send || entered)', self.overlay)
        self.assertIn('chat_page.draft[0] = 0;', self.overlay)
        self.assertIn('std::erase_if(chat_page.history', self.overlay)
        self.assertIn('if (Team::open) Team::SyncChatAudience()', self.overlay)

    def test_real_teammate_level_not_fabricated_lobby_or_latency(self):
        self.assertIn('u32 level = 0;', self.panel)
        self.assertIn('.level = entry.level,', self.game)
        self.assertIn('uint32_t level; /* B45: from party vitals', self.map_abi)
        self.assertIn('out.level = member.level;', self.bridge)
        self.assertIn('out.level = live.level;', self.bridge)
        self.assertIn('if (privacy.roster_levels)', self.overlay)
        self.assertIn('p.level > 0 ? std::to_string(p.level) : "—"', self.overlay)
        self.assertIn('std::string("Ping: —")', self.overlay)
        self.assertIn('std::string("Build: —")', self.overlay)

    def test_build_rules_boundary_18_hybrids_and_privacy(self):
        self.assertIn('inline constexpr int Threshold = 18;', self.build)
        self.assertIn('constexpr std::optional<std::uint8_t> Mask(', self.build)
        self.assertIn('constexpr std::string_view English(', self.build)
        self.assertIn('constexpr std::string_view Russian(', self.build)
        self.assertIn('T("Share my build stats"', self.overlay)
        self.assertIn('does NOT broadcast stats yet.', self.overlay)

    def test_existing_pvp_quick_match_is_distinguished_from_pve(self):
        self.assertIn('T("Quick PvP invasion", "Быстрое вторжение PvP")', self.overlay)
        self.assertIn('T("Cancel PvP search", "Отменить поиск PvP")', self.overlay)
        self.assertIn('bbcoop_invade(invading ? 0 : 1)', self.overlay)
        self.assertIn('bbcoop_lobby_request(BBCOOP_TEAM_QUICK_MATCH, "")', self.overlay)


if __name__ == "__main__":
    unittest.main()
