// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
// B82: execute the actual shared client/server GameLinkPeer retransmission path.
// No fake network implementation or native Bloodborne files required.
#include <iostream>
#include <vector>

#include "coop/game_link.h"

using namespace BloodborneCoop;

namespace {
bool Check(bool good, const char* what, int line) {
    if (!good) std::cerr << "B82 FAIL at " << line << ": " << what << '\n';
    return good;
}
#define CHECK(expr) do { if (!Check((expr), #expr, __LINE__)) return 1; } while (false)

std::vector<u8> Packet(u32 channel, u8 mark) {
    std::vector<u8> bytes(9);
    for (int i = 0; i < 4; ++i) bytes[i] = static_cast<u8>(channel >> (8*i));
    bytes[4] = 1; // one-byte native payload
    bytes[8] = mark;
    return bytes;
}
int ReliableBacklogResendOrderAndUniqueness() {
    GameLinkPeer host{"host", 1};
    for (int i = 0; i < 100; ++i) {
        host.Send(PacketClass::Reliable, Packet(0x31, static_cast<u8>(i)), 0);
    }
    size_t lost = 0;
    for (const auto& frame : host.Flush(0)) lost += frame.entries.size();
    CHECK(lost == 100);
    for (int i = 0; i < 1000; ++i) {
        host.Send(PacketClass::Reliable, Packet(0x42, static_cast<u8>(i)), 200);
    }
    const auto frames = host.Flush(200);
    std::vector<u32> wire;
    for (const auto& frame : frames) {
        const auto decoded = DecodeGameFrame(EncodeGameFrame(frame));
        CHECK(decoded.has_value());
        for (const auto& entry : decoded->entries) {
            CHECK(entry.packet_class == PacketClass::Reliable);
            wire.push_back(entry.seq);
        }
    }
    CHECK(wire.size() == 1064);
    for (u32 i = 0; i < 1000; ++i) CHECK(wire[i] == i + 100);
    for (u32 i = 0; i < 64; ++i) CHECK(wire[1000 + i] == i);
    CHECK(host.Unacked() == 1100);
    CHECK(host.Resends() == 64);
    const auto deferred = host.Flush(201);
    std::vector<u32> backlog;
    for (const auto& frame : deferred) {
        for (const auto& entry : frame.entries) backlog.push_back(entry.seq);
    }
    CHECK(backlog.size() == 36);
    for (u32 i = 0; i < 36; ++i) CHECK(backlog[i] == i + 64);
    CHECK(host.Resends() == 100);
    CHECK(host.Flush(202).empty());
    return 0;
}

int EveryEnemyUnreliablePacketIsPreserved() {
    GameLinkPeer host{"host", 1};
    GameLinkPeer guest{"guest", 2};
    for (u8 enemy = 0; enemy < 25; ++enemy) {
        host.Send(PacketClass::Unreliable, Packet(4, enemy), 0);
    }
    std::vector<u8> received;
    size_t sent = 0;
    for (const auto& frame : host.Flush(0)) {
        sent += frame.entries.size();
        for (const auto& packet : guest.Receive(frame, 0)) {
            received.push_back(packet.back());
        }
    }
    CHECK(sent == 25);
    CHECK(received.size() == 25);
    for (u8 i = 0; i < 25; ++i) CHECK(received[i] == i);
    CHECK(host.Unacked() == 0);
    return 0;
}

int FreshPacketsNotRepeatedEvenWithZeroResendDelay() {
    GameLinkPeer::Settings settings;
    settings.resend_ms = 0; // source-policy regression, not a shipped setting
    GameLinkPeer host{"host", 1, settings};
    host.Send(PacketClass::Reliable, Packet(0x42, 7), 0);
    host.Send(PacketClass::Reliable, Packet(0x29, 9), 0);
    size_t entries = 0;
    for (const auto& frame : host.Flush(0)) entries += frame.entries.size();
    CHECK(entries == 2 && host.Unacked() == 2 && host.Resends() == 0);
    return 0;
}

int IndependentTwoThreeFiveMemberStreams() {
    for (int team = 2; team <= 5; ++team) {
        if (team == 4) continue;
        for (int member = 1; member < team; ++member) {
            GameLinkPeer host{"host", 1};
            GameLinkPeer guest{"guest", static_cast<u32>(member + 10)};
            host.Send(PacketClass::Reliable, Packet(0x42, 11), 0);
            for (const auto& frame : host.Flush(0)) {
                const auto received = guest.Receive(frame, 0);
                CHECK(received.size() == 1 && received[0].back() == 11);
            }
            for (const auto& frame : guest.Flush(10)) {
                (void)host.Receive(frame, 10);
            }
            CHECK(host.Unacked() == 0);
            CHECK(host.Resends() == 0);
        }
    }
    return 0;
}
} // namespace

int main() {
    if (ReliableBacklogResendOrderAndUniqueness()) return 1;
    if (EveryEnemyUnreliablePacketIsPreserved()) return 1;
    if (FreshPacketsNotRepeatedEvenWithZeroResendDelay()) return 1;
    if (IndependentTwoThreeFiveMemberStreams()) return 1;
    std::cout << "B82_REAL_GAME_LINK_RETRANSMISSION_PASS\n";
    return 0;
}
