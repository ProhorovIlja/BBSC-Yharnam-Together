// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
// Real Qt6/C++20 server matching type, not a reimplementation of the helper.
#include <iostream>
#include <QHash>
#include <QString>
#include "signaling_peer_scope.h"

#define CHECK(value) do { if (!(value)) { \
    std::cerr << "B24 CHECK failed at " << __LINE__ << ": " #value << '\n'; return 1; \
} } while (false)

static uint16_t Add(Room& room, const char* npid, const char* ip, uint16_t port) {
    RoomMember member;
    member.npid = QString::fromLatin1(npid);
    member.addr = QString::fromLatin1(ip);
    member.port = port;
    return room.addMember(member)->memberId;
}

int main() {
    Room party;
    party.roomId = 101;
    party.maxSlot = 5;
    auto hostId = Add(party, "Host", "10.0.0.1", 31314);
    const char* names[] = {"Guest1", "Guest2", "Guest3", "Guest4"};
    uint16_t ids[4] = {};
    for (int i = 0; i < 4; ++i) {
        ids[i] = Add(party, names[i], "10.0.0.2", static_cast<uint16_t>(31315+i));
    }
    CHECK(hostId != 0);
    CHECK(party.members.size() == 5);

    // The party host can resolve every one of the four independent remotes.
    for (int i = 0; i < 4; ++i) {
        const auto peer = SignalingPeerScope::Find(
            party, QStringLiteral("Host"), QString::fromLatin1(names[i]));
        CHECK(peer.has_value());
        CHECK(peer->memberId == ids[i]);
        CHECK(peer->roomPort == static_cast<uint16_t>(31315+i));
    }
    // A guest may resolve other guests as long as both remain in this room.
    CHECK(SignalingPeerScope::Find(party, "Guest4", "Guest2")->memberId == ids[1]);
    CHECK(!SignalingPeerScope::Find(party, "Host", "Host"));
    CHECK(!SignalingPeerScope::Find(party, "", "Guest1"));
    CHECK(!SignalingPeerScope::Find(party, "Host", ""));
    CHECK(!SignalingPeerScope::Find(party, "Outsider", "Guest1"));

    // A different room under the same title/matchingKey is NOT this party.
    Room otherParty;
    otherParty.roomId = 102;
    otherParty.maxSlot = 5;
    Add(otherParty, "OtherHost", "198.51.100.99", 31234);
    Add(otherParty, "Outsider", "203.0.113.99", 31777);
    CHECK(!SignalingPeerScope::Find(party, "Host", "Outsider"));
    CHECK(!SignalingPeerScope::Find(otherParty, "Host", "Outsider"));

    // A departed guest must immediately stop resolving, even if STUN still
    // contains the old NP ID -> endpoint mapping.
    party.members.remove(ids[1]);
    CHECK(!SignalingPeerScope::Find(party, "Host", "Guest2"));
    CHECK(SignalingPeerScope::Find(party, "Host", "Guest3")->memberId == ids[2]);
    // Rejoining as the same online ID uses the NEW member identity.
    const uint16_t newId = Add(party, "Guest2", "10.0.0.42", 31444);
    CHECK(SignalingPeerScope::Find(party, "Host", "Guest2")->memberId == newId);
    CHECK(SignalingPeerScope::Find(party, "Host", "Guest2")->roomPort == 31444);

    std::cout << "B24_FIVE_HUNTERS_ONE_ROOM_SIGNALING_SCOPE_PASS\n";
    return 0;
}
