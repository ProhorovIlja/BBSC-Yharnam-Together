// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later
// Adapted from merged upstream Yharnam Together PR #546 (2026-11-10):
// every retail Bloodborne 1.09 edition must receive co-op hooks.
#include <string_view>
#include <gtest/gtest.h>
#include "core/bloodborne_titles.h"
using namespace Core::Bloodborne;

TEST(Titles, EveryRetailReleaseIsBloodborne) {
    for (const std::string_view id :
         {"CUSA03173", "CUSA00207", "CUSA00208", "CUSA00900", "CUSA03179",
          "CUSA01363", "CUSA03023", "CUSA00299", "CUSA03014"}) {
        EXPECT_TRUE(IsBloodborneTitle(id)) << id;
        EXPECT_EQ(SeamlessCoopGameFor(id, "01.09"), CoopGame::Yes);
    }
}
TEST(Titles, UnrelatedOrMalformedIdsAreNeverBloodborne) {
    for (const std::string_view id :
         {"", "UNKNOWN", "CUSA00001", "CUSA0317", "CUSA031730",
          "cusa03173", "CUSA03173 "}) {
        EXPECT_FALSE(IsBloodborneTitle(id));
        EXPECT_EQ(SeamlessCoopGameFor(id, "01.09"), CoopGame::OtherGame);
    }
}
TEST(Titles, WrongSfoVersionDoesNotBypassExecutableSiteChecks) {
    EXPECT_EQ(SeamlessCoopGameFor("CUSA03173", "01.00"), CoopGame::OtherVersion);
    EXPECT_EQ(SeamlessCoopGameFor("CUSA00900", "Unknown"), CoopGame::OtherVersion);
    // This is not unguarded support for 1.00: the normal patch-site code
    // verification must still reject unmatched executable bytes.
    EXPECT_TRUE(GetsSeamlessCoop(CoopGame::OtherVersion));
    EXPECT_FALSE(GetsSeamlessCoop(CoopGame::OtherGame));
}
