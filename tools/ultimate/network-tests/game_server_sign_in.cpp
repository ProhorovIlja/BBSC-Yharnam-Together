// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <gtest/gtest.h>

#include "core/bloodborne_game_server.h"

using namespace Core::Bloodborne;

// Discord audit A1 (Ozi's logs, 2026-11-01): the unseen teammate's game never signed in to the
// game's own server, and nothing said so. What the game did with its server, as the http layer
// notes it: asked (ss.info), signed in (/basic_utils/login answered), or failed.
TEST(GameServerSignIn, FollowsTheGamesRequests) {
    GameServerSignInLog log;
    EXPECT_EQ(log.State(), GameServerSignIn::NotTried);
    log.Asked();
    EXPECT_EQ(log.State(), GameServerSignIn::Trying);
    log.Answered("https://ss4.scej-network.jp:20443/bb-eu/ss.info", true);
    EXPECT_EQ(log.State(), GameServerSignIn::Trying); // ss.info alone is no sign-in
    log.Answered("https://ss4.scej-network.jp:20443/basic_utils/login", true);
    EXPECT_EQ(log.State(), GameServerSignIn::SignedIn);
    // A later failure (one request of many in play) does not undo the sign-in.
    log.Answered("https://ss4.scej-network.jp:20443/wandering_ghost/get", false);
    EXPECT_EQ(log.State(), GameServerSignIn::SignedIn);
    EXPECT_EQ(log.Failures(), 0u);
}

// The rig's no-game-server-join (2026-11-10): ss.info timed out, again and again.
TEST(GameServerSignIn, AFailureBeforeTheSignInIsFailed) {
    GameServerSignInLog log;
    log.Asked();
    log.Answered("https://ss4.scej-network.jp:20443/bb-eu/ss.info", false);
    log.Answered("https://ss4.scej-network.jp:20443/bb-eu/ss.info", false);
    EXPECT_EQ(log.State(), GameServerSignIn::Failed);
    EXPECT_EQ(log.Failures(), 2u);
    // A sign-in that comes through after all is a sign-in.
    log.Answered("https://ss4.scej-network.jp:20443/basic_utils/login", true);
    EXPECT_EQ(log.State(), GameServerSignIn::SignedIn);
}

TEST(GameServerSignIn, KnowsTheGameServersUrls) {
    EXPECT_TRUE(IsGameServerUrl("https://ss4.scej-network.jp:20443/bb-eu/ss.info"));
    EXPECT_TRUE(IsGameServerUrl("https://ss4.scej-network.jp:20443"));
    EXPECT_FALSE(IsGameServerUrl("http://42.189.91.13:31315/v1/users/p3d45846901dff8/feed"));
    EXPECT_FALSE(IsGameServerUrl("http://192.168.0.147:20443/basic_utils/login"));
}

// The team screen says it plainly once the save is open (the title, where the sign-in happens,
// is behind): Ozi's guest loaded with no sign-in at all; one whose server never answered failed.
// PC rig 2026-11-14 (#559 red): the sign-in goes to the address ss.info hands back, so a
// tracker that only follows ss4.scej-network.jp:20443 never saw it and warned every healthy game.
TEST(GameServerSignIn, TheSignInCountsOnTheAddressSsInfoHandsBack) {
    EXPECT_TRUE(IsGameServerRequest("https://ss4.scej-network.jp:20443/bb-eu/ss.info"));
    EXPECT_TRUE(IsGameServerRequest("http://192.168.0.147:20443/basic_utils/login"));
    EXPECT_TRUE(IsGameServerRequest("https://seamlesshunt.com:20443/basic_utils/login"));
    EXPECT_FALSE(IsGameServerRequest("http://42.189.91.13:31315/v1/users/p3d45846901dff8/feed"));
    GameServerSignInLog log;
    log.Asked();
    log.Answered("https://ss4.scej-network.jp:20443/bb-eu/ss.info", true);
    log.Asked();
    log.Answered("http://192.168.0.147:20443/basic_utils/login", true);
    EXPECT_EQ(log.State(), GameServerSignIn::SignedIn);
    log.SaveOpened();
    EXPECT_EQ(log.Notice(), "");
}

TEST(GameServerSignIn, UnrelatedUrlsCannotPretendToBeLoginOrDiscovery) {
    EXPECT_FALSE(IsGameServerRequest("https://other.example/?host=ss4.scej-network.jp:20443"));
    EXPECT_FALSE(IsGameServerRequest("https://ss4.scej-network.jp:20443@other.example/"));
    EXPECT_FALSE(IsGameServerRequest("https://other.example/basic_utils/login_backup"));
    EXPECT_FALSE(IsGameServerRequest("https://other.example/#/basic_utils/login"));
    EXPECT_FALSE(IsGameServerRequest("https://other.example/status?path=/basic_utils/login"));
    EXPECT_TRUE(IsGameServerRequest("https://[::1]:20443/basic_utils/login?attempt=1"));

    GameServerSignInLog log;
    log.Asked();
    log.Answered("https://other.example/status?path=/basic_utils/login", true);
    log.Answered("https://other.example/basic_utils/login_backup", false);
    EXPECT_EQ(log.State(), GameServerSignIn::Trying);
    EXPECT_EQ(log.Failures(), 0u);
    log.Answered("https://[::1]:20443/basic_utils/login?attempt=1", true);
    EXPECT_EQ(log.State(), GameServerSignIn::SignedIn);
}

TEST(GameServerSignIn, TheTeamScreenSaysWhenTheGameIsNotSignedIn) {
    EXPECT_EQ(GameServerNotice(GameServerSignIn::SignedIn, true), "");
    EXPECT_EQ(GameServerNotice(GameServerSignIn::NotTried, false), ""); // the title, not yet
    EXPECT_EQ(GameServerNotice(GameServerSignIn::Trying, false), "");
    const std::string offline = GameServerNotice(GameServerSignIn::NotTried, true);
    EXPECT_NE(offline.find("offline"), std::string::npos) << offline;
    EXPECT_NE(offline.find("teammates will not see you"), std::string::npos) << offline;
    const std::string failed = GameServerNotice(GameServerSignIn::Failed, false);
    EXPECT_NE(failed.find("20443"), std::string::npos) << failed;
    EXPECT_FALSE(GameServerNotice(GameServerSignIn::Trying, true).empty());
    for (const auto state :
         {GameServerSignIn::NotTried, GameServerSignIn::Trying, GameServerSignIn::Failed}) {
        EXPECT_LE(GameServerNotice(state, true).size(), 95u);
    }
}

// Ozi's guest as the log keeps it: its save opened with nothing asked of the game server.
TEST(GameServerSignIn, ASaveOpenedWithNoSignInIsOffline) {
    GameServerSignInLog log;
    EXPECT_EQ(log.Notice(), "");
    EXPECT_TRUE(log.SaveOpened());
    EXPECT_FALSE(log.SaveOpened()); // the next character's is no first one
    EXPECT_TRUE(log.WasSaveOpened());
    EXPECT_EQ(log.Notice(), GameServerNotice(GameServerSignIn::NotTried, true));
    GameServerSignInLog healthy;
    healthy.Asked();
    healthy.Answered("https://ss4.scej-network.jp:20443/basic_utils/login", true);
    healthy.SaveOpened();
    EXPECT_EQ(healthy.Notice(), "");
}
