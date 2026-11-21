// SPDX-License-Identifier: GPL-2.0-or-later
#include <cstdint>
#include <iostream>
#include <limits>
#include <vector>
#include "coop/game_link.h"
using namespace BloodborneCoop;
#define REQUIRE(x) do { if (!(x)) { std::cerr << __LINE__ << ": " #x "\n"; return 1; } } while(false)
std::vector<u8> Packet(u32 channel, u8 marker) {
    std::vector<u8> bytes;
    GameLinkDetail::Put(bytes, channel);
    GameLinkDetail::Put(bytes, u32{1});
    bytes.push_back(marker);
    return bytes;
}
int main() {
    GameLinkPeer host{"host", 1};
    GameLinkPeer guest{"guest", 2};
    const auto world = Packet(0x29, 41), join = Packet(0x42, 42);
    host.Send(PacketClass::Reliable, world, 0);
    bool sent_world = false;
    for (const auto& frame: host.Flush(0)) {
        for (const auto& delivered: guest.Receive(frame, 0)) {
            REQUIRE(delivered == world);
            sent_world = true;
        }
    }
    REQUIRE(sent_world);
    (void)guest.Flush(10); // Drop guest's real ACK to emulate packet loss.
    host.Send(PacketClass::Reliable, join, 10); // queued but not yet sent
    REQUIRE(host.Unacked() == 2);
    const GameFrame future{"guest", 2, 1, 2, {}};
    (void)host.Receive(future, 20);
    REQUIRE(host.Unacked() == 2 && host.UnackedBytes() == world.size() + join.size());
    const GameFrame extreme{"guest", 2, 1, std::numeric_limits<u32>::max(), {}};
    (void)host.Receive(extreme, 30);
    REQUIRE(host.Unacked() == 2);
    const GameFrame valid{"guest", 2, 1, 1, {}};
    (void)host.Receive(valid, 40);
    REQUIRE(host.Unacked() == 1 && host.UnackedBytes() == join.size());
    bool got_join = false;
    for (const auto& frame: host.Flush(50)) {
        for (const auto& delivered: guest.Receive(frame, 50)) {
            REQUIRE(delivered == join);
            got_join = true;
        }
    }
    REQUIRE(got_join);
    for (const auto& frame: guest.Flush(60)) (void)host.Receive(frame, 60);
    REQUIRE(host.Unacked() == 0 && host.UnackedBytes() == 0);

    GameLinkPeer receiver{"receiver", 7};
    // A future ACK does not suppress *legitimate incoming* reliable payload.
    const GameFrame payload{"remote", 9, 7, 999, {{PacketClass::Reliable, 0, Packet(0x42, 55)}}};
    auto delivered = receiver.Receive(payload, 70);
    REQUIRE(delivered.size() == 1 && delivered.front() == Packet(0x42, 55));

    // The sender instance reset must not inherit an ACK window from a prior
    // remote run: a new join queued after restart stays pending until flush.
    GameLinkPeer restarting{"host", 3};
    restarting.Receive(GameFrame{"guest", 2, 3, 0, {}}, 1);
    restarting.Send(PacketClass::Reliable, world, 2);
    restarting.Flush(2);
    restarting.Receive(GameFrame{"guest", 5, 3, 0, {}}, 3); // remote restarted
    restarting.Send(PacketClass::Reliable, join, 4);
    const size_t pending = restarting.Unacked();
    restarting.Receive(GameFrame{"guest", 5, 3, 123, {}}, 5);
    REQUIRE(restarting.Unacked() == pending);
    // Combined #309 + #311 invariant: a stale recipient carrying a future
    // ACK and a different peer instance may neither reset the active stream
    // nor retire an unflushed reliable join packet.
    GameLinkPeer protected_host{"host", 8};
    protected_host.Receive(GameFrame{"guest", 2, 8, 0, {}}, 1);
    protected_host.Send(PacketClass::Reliable, world, 2);
    (void)protected_host.Flush(2);
    protected_host.Send(PacketClass::Reliable, join, 3);
    const auto old_unacked = protected_host.Unacked();
    protected_host.Receive(
        GameFrame{"guest", 3, 777, std::numeric_limits<u32>::max(),
                  {{PacketClass::Reliable, 0, Packet(0x42, 90)}}}, 4);
    REQUIRE(protected_host.Restarts() == 0);
    REQUIRE(protected_host.Unacked() == old_unacked);
    REQUIRE(protected_host.SilentFor(5) == 4);
    REQUIRE(protected_host.Flush(5).front().peer_instance == 2);
    std::cout << "GameLink impossible-ACK and queued world data preserved\n";
}
