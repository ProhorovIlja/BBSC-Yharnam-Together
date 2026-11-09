// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
// Test production C++ helper with the real Qt6 matching session/room types.
// The separate CI source contract verifies the full DoLeaveRoom call order.
#include <iostream>
#include <QString>
#include "matching_lifecycle_guard.h"

#define CHECK(value) do { if (!(value)) { \
    std::cerr << "B25 failed at line " << __LINE__ << ": " #value << '\n'; return 1; \
} } while (false)

int main() {
    MatchingSessionState host;
    host.initialized = true;
    host.ctxId = 1;
    host.roomId = 501;
    host.isRoomOwner = true;
    host.myMemberId = 0x11;

    // All five members have an independent active room reference.
    Room room;
    room.roomId = host.roomId;
    room.maxSlot = 5;
    for (int i = 0; i < 5; ++i) {
        RoomMember member;
        member.npid = QStringLiteral("Hunter%1").arg(i + 1);
        member.userId = i + 1;
        CHECK(room.addMember(member)->memberId != 0);
    }
    CHECK(room.members.size() == 5);
    CHECK(room.isFull());

    CHECK(!MatchingLifecycleGuard::MayEnterRoom(host));
    CHECK(MatchingLifecycleGuard::RoomRequiringCleanup(host) == 501);

    // Original bug: ContextStop cleared initialized before the disconnect.
    // A stopped context still owns an occupied room until it has left.
    host.initialized = false;
    host.ctxId = 0;
    CHECK(MatchingLifecycleGuard::RoomRequiringCleanup(host) == 501);
    CHECK(!MatchingLifecycleGuard::MayEnterRoom(host));

    // Likewise, a second join/create must be blocked before roomId overwrite.
    MatchingSessionState guest = host;
    guest.roomId = 501;
    guest.initialized = true;
    guest.myMemberId = 0x22;
    CHECK(!MatchingLifecycleGuard::MayEnterRoom(guest));
    CHECK(MatchingLifecycleGuard::RoomRequiringCleanup(guest) == 501);

    // B25 calls the real server's DoLeaveRoom *before* clearing these fields;
    // model the state after the production reset, not the algorithm itself.
    host.roomId = 0;
    host.myMemberId = 0;
    host.isRoomOwner = false;
    CHECK(MatchingLifecycleGuard::RoomRequiringCleanup(host) == 0);
    CHECK(MatchingLifecycleGuard::MayEnterRoom(host));
    CHECK(!MatchingLifecycleGuard::MayEnterRoom(guest));
    guest.roomId = 0;
    CHECK(MatchingLifecycleGuard::MayEnterRoom(guest));

    // Repeated ContextStop/disconnect after cleanup are idempotent for room IDs.
    CHECK(MatchingLifecycleGuard::RoomRequiringCleanup(host) == 0);
    CHECK(MatchingLifecycleGuard::RoomRequiringCleanup(guest) == 0);

    std::cout << "B25_REAL_QT6_ROOM_LIFECYCLE_GUARD_PASS\n";
    return 0;
}
