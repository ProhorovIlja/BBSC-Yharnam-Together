// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
//
// B82: actual production GameLinkPeer source, no substituted transport.
// Deterministic assertions on wire entries/ordering, not speculative ping.
#include <iostream>
#include <string>
#include <vector>

#include "coop/game_link.h"

using namespace BloodborneCoop;

namespace {
bool Check(bool value, const char* expr, int line) {
    if (!value) std::cerr << "FAIL line " << line << ": " << expr << '\n';
    return value;
}
#define CHECK(expr) do { if (!Check((expr), #expr, __LINE__)) return 1; } while (false)

std::vector<u8> Packet(u32 channel, u8 mark, size_t bytes = 1) {
    std::vector<u8> data(8 + bytes, mark);
    for (size_t i = 0; i < 4; ++i) {
        data[i] = static_cast<u8>(channel >> (8 * i));
        data[i + 4] = static_cast<u8>(bytes >> (8 * i));
    }
    return data;
}

int FrameHitchDropsObsoleteStatesBeforeWire() {
    GameLinkPeer host{"host", 1};
    GameLinkPeer guest{"guest", 2};
    for (int i = 0; i < 1000; ++i) {
        host.Send(PacketClass::Unreliable, Packet(6, static_cast<u8>(i)), i);
        host.Send(PacketClass::Unreliable, Packet(4, static_cast<u8>(i)), i);
        if (i == 10 || i == 700) {
            host.Send(PacketClass::Reliable, Packet(0x42, static_cast<u8>(i)), i);
        }
    }
    const auto frames = host.Flush(1001);
    size_t count = 0, reliable = 0, unreliable = 0;
    std::vector<u8> delivered;
    for (const auto& frame : frames) {
        const auto bytes = EncodeGameFrame(frame);
        const auto decoded = DecodeGameFrame(bytes);
        CHECK(decoded.has_value());
        for (const auto& entry : decoded->entries) {
            ++count;
            reliable += entry.packet_class == PacketClass::Reliable;
            unreliable += entry.packet_class == PacketClass::Unreliable;
        }
        for (const auto& packet : guest.Receive(*decoded, 1001)) {
            delivered.push_back(packet.back());
        }
    }
    CHECK(count == 4); // without coalescing: 2002 wire entries
    CHECK(reliable == 2 && unreliable == 2);
    CHECK((delivered == std::vector<u8>{10, static_cast<u8>(700),
                                         static_cast<u8>(999), static_cast<u8>(999)}));
    CHECK(host.Unacked() == 2);
    // ACK goes through the same production reliability layer.
    for (const auto& frame : guest.Flush(1002)) {
        (void)host.Receive(frame, 1003);
    }
    CHECK(host.Unacked() == 0);
    CHECK(host.Resends() == 0);
    return 0;
}

int NonNativeBodiesDoNotDisappear() {
    GameLinkPeer peer{"peer", 3};
    peer.Send(PacketClass::Unreliable, std::vector<u8>{6, 0}, 0);
    peer.Send(PacketClass::Unreliable, std::vector<u8>{6, 1}, 0);
    std::vector<u8> malformed = Packet(6, 4);
    malformed[4] = 99;
    peer.Send(PacketClass::Unreliable, malformed, 0);
    peer.Send(PacketClass::Unreliable, malformed, 0);
    size_t n = 0;
    for (const auto& frame : peer.Flush(0)) n += frame.entries.size();
    CHECK(n == 4);
    return 0;
}

int LatestWinsAcrossSeparateFlushes() {
    GameLinkPeer sender{"sender", 5};
    GameLinkPeer receiver{"receiver", 6};
    sender.Send(PacketClass::Unreliable, Packet(6, 1), 0);
    auto old = sender.Flush(0);
    sender.Send(PacketClass::Unreliable, Packet(6, 2), 10);
    auto fresh = sender.Flush(10);
    CHECK(old.size() == 1 && fresh.size() == 1);
    const auto received = receiver.Receive(fresh[0], 10);
    CHECK(received.size() == 1 && received[0].back() == 2);
    CHECK(receiver.Receive(old[0], 20).empty());
    CHECK(receiver.DroppedOld() == 1);
    return 0;
}

int Party23And5Backlog() {
    for (int n : {2, 3, 5}) {
        for (int member = 1; member < n; ++member) {
            GameLinkPeer host{"host", 1};
            GameLinkPeer guest{"member_" + std::to_string(member), static_cast<u32>(10 + member)};
            for (int i = 0; i < 500; ++i) {
                host.Send(PacketClass::Unreliable, Packet(6, static_cast<u8>(i)), i);
            }
            const auto frames = host.Flush(501);
            size_t total = 0;
            for (const auto& frame : frames) {
                total += frame.entries.size();
                const auto received = guest.Receive(frame, 501);
                CHECK(received.size() == 1);
                CHECK(received[0].back() == static_cast<u8>(499));
            }
            CHECK(total == 1);
            CHECK(host.Unacked() == 0);
        }
    }
    return 0;
}
} // namespace

int main() {
    if (FrameHitchDropsObsoleteStatesBeforeWire() != 0) return 1;
    if (NonNativeBodiesDoNotDisappear() != 0) return 1;
    if (LatestWinsAcrossSeparateFlushes() != 0) return 1;
    if (Party23And5Backlog() != 0) return 1;
    std::cout << "B82_GAME_LINK_COALESCE_REAL_PRODUCTION_PASS\n";
    return 0;
}
