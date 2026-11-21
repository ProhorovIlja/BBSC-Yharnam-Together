// SPDX-License-Identifier: GPL-2.0-or-later
// The production GameLinkPeer is shared by the Windows game client and server.
#include <iostream>
#include <vector>
#include "coop/game_link.h"

using namespace BloodborneCoop;
#define CHECK(x) do { if (!(x)) { std::cerr << "GameLink ACK failure line " << __LINE__ << ": " #x "\n"; return 1; } } while(false)
static std::vector<u8> Packet(u32 channel, u8 mark) {
    std::vector<u8> packet(9);
    for (int i = 0; i < 4; ++i) packet[i] = static_cast<u8>(channel >> (8 * i));
    packet[4] = 1;
    packet[8] = mark;
    return packet;
}
int FutureAckDoesNotRetireUnsentPackets() {
    GameLinkPeer host{"host", 1};
    GameLinkPeer guest{"guest", 2};
    host.Send(PacketClass::Reliable, Packet(0x29, 7), 0);
    for (const auto& frame : host.Flush(0)) {
        const auto delivered = guest.Receive(frame, 0);
        CHECK(delivered.size() == 1 && delivered[0].back() == 7);
    }
    (void)guest.Flush(10); // Deliberately drop valid ACK.
    host.Send(PacketClass::Reliable, Packet(0x42, 8), 10); // Assigned but not sent.
    CHECK(host.Unacked() == 2);
    const GameFrame impossible{.sender = "guest", .instance = 2,
                               .peer_instance = 1, .ack = 2, .entries = {}};
    (void)host.Receive(impossible, 20);
    CHECK(host.Unacked() == 2);
    const GameFrame extreme{.sender = "guest", .instance = 2,
                            .peer_instance = 1, .ack = 0xFFFFFFFFu, .entries = {}};
    (void)host.Receive(extreme, 30);
    CHECK(host.Unacked() == 2);
    const GameFrame valid{.sender = "guest", .instance = 2,
                          .peer_instance = 1, .ack = 1, .entries = {}};
    (void)host.Receive(valid, 40);
    CHECK(host.Unacked() == 1);
    for (const auto& frame : host.Flush(50)) {
        const auto delivered = guest.Receive(frame, 50);
        CHECK(delivered.size() == 1 && delivered[0].back() == 8);
    }
    for (const auto& frame : guest.Flush(60))
        (void)host.Receive(frame, 60);
    CHECK(host.Unacked() == 0);
    return 0;
}
int InvalidAckDoesNotSuppressInboundPayload() {
    GameLinkPeer host{"host", 1};
    GameFrame from_new{.sender = "remote", .instance = 7,
                       .peer_instance = 1, .ack = 999, .entries = {}};
    from_new.entries.push_back({PacketClass::Reliable, 0, Packet(0x42, 9)});
    const auto delivered = host.Receive(from_new, 10);
    CHECK(delivered.size() == 1 && delivered[0].back() == 9);
    return 0;
}
int IndependentTwoThreeFiveMemberAckWindows() {
    for (int team : {2, 3, 5}) {
        for (int member = 1; member < team; ++member) {
            GameLinkPeer host{"host", 1};
            GameLinkPeer guest{"guest", static_cast<u32>(member + 10)};
            host.Send(PacketClass::Reliable, Packet(0x42, 11), 0);
            for (const auto& frame : host.Flush(0)) {
                const auto delivered = guest.Receive(frame, 0);
                CHECK(delivered.size() == 1 && delivered[0].back() == 11);
            }
            for (const auto& frame : guest.Flush(10))
                (void)host.Receive(frame, 10);
            CHECK(host.Unacked() == 0);
        }
    }
    return 0;
}
int main() {
    if (FutureAckDoesNotRetireUnsentPackets()) return 1;
    if (InvalidAckDoesNotSuppressInboundPayload()) return 1;
    if (IndependentTwoThreeFiveMemberAckWindows()) return 1;
    std::cout << "Production GameLink future ACK and 2/3/5-member isolation passed\n";
}
