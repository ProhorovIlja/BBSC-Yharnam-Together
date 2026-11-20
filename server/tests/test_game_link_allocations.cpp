// SPDX-License-Identifier: GPL-2.0-or-later
// Exercise payload ownership in the real shared client/server stream, without network timing.
#include <cstdlib>
#include <iostream>
#include <new>
#include <vector>

#include "coop/game_link.h"

namespace {
constexpr size_t PayloadBytes = 4093; // distinguish packet allocations from container growth
bool measuring = false;
size_t payload_allocations = 0;
void* last_payload = nullptr;
}

void* operator new(size_t bytes) {
    void* allocation = std::malloc(bytes ? bytes : 1);
    if (!allocation)
        throw std::bad_alloc{};
    if (measuring && bytes == PayloadBytes) {
        ++payload_allocations;
        last_payload = allocation;
    }
    return allocation;
}
void operator delete(void* allocation) noexcept { std::free(allocation); }
void operator delete(void* allocation, size_t) noexcept { std::free(allocation); }

using namespace BloodborneCoop;
#define CHECK(value) do { if (!(value)) { std::cerr << __LINE__ << ": " << #value << '\n'; return false; } } while (false)

static bool UnreliableTransfersItsOwnedPayload() {
    GameLinkPeer host{"host", 1};
    std::vector<u8> packet(PayloadBytes, 0xA5);
    packet[0] = 4; // unreliable game channel
    packet[1] = packet[2] = packet[3] = 0;
    payload_allocations = 0;
    measuring = true;
    host.Send(PacketClass::Unreliable, packet, 0);
    measuring = false;
    CHECK(payload_allocations == 1);
    const void* queued_data = last_payload;
    payload_allocations = 0;
    measuring = true;
    const auto frames = host.Flush(0);
    measuring = false;
    CHECK(payload_allocations == 0);
    CHECK(frames.size() == 1 && frames[0].entries.size() == 1);
    CHECK(frames[0].entries[0].packet.data() == queued_data);
    CHECK(frames[0].entries[0].packet == packet);
    CHECK(host.Unacked() == 0 && host.UnackedBytes() == 0);
    const auto decoded = DecodeGameFrame(EncodeGameFrame(frames[0]));
    CHECK(decoded && *decoded == frames[0]);
    return true;
}

static bool ReliableRetainsItsPayloadForRetransmission() {
    GameLinkPeer host{"host", 1};
    std::vector<u8> packet(PayloadBytes, 0x19);
    packet[0] = 0x29;
    packet[1] = packet[2] = packet[3] = 0;
    host.Send(PacketClass::Reliable, packet, 0);
    measuring = true;
    payload_allocations = 0;
    const auto first = host.Flush(0);
    measuring = false;
    CHECK(payload_allocations == 1);
    CHECK(first.size() == 1 && first[0].entries[0].packet == packet);
    CHECK(host.Unacked() == 1 && host.UnackedBytes() == packet.size());
    const auto resent = host.Flush(150);
    CHECK(resent.size() == 1 && resent[0].entries[0].packet == packet);
    CHECK(host.Resends() == 1);
    host.Receive(GameFrame{"guest", 2, 1, 1, {}}, 160);
    CHECK(host.Unacked() == 0 && host.UnackedBytes() == 0);
    return true;
}

static bool FreshAndRetriedPacketsKeepWireOrderAcrossFrames() {
    GameLinkPeer::Settings settings;
    settings.frame_bytes = 32;
    GameLinkPeer peer{"host", 1, settings};
    const std::vector<u8> reliable(48, 0x29), visual(48, 4), next(48, 0x29);
    peer.Send(PacketClass::Reliable, reliable, 0);
    CHECK(peer.Flush(0).size() == 1);
    peer.Send(PacketClass::Unreliable, visual, 150);
    peer.Send(PacketClass::Reliable, next, 150);
    const auto frames = peer.Flush(150);
    CHECK(frames.size() == 3);
    for (const auto& frame : frames) {
        CHECK(frame.entries.size() == 1);
        const auto decoded = DecodeGameFrame(EncodeGameFrame(frame));
        CHECK(decoded && *decoded == frame);
    }
    CHECK(frames[0].entries[0].packet_class == PacketClass::Unreliable);
    CHECK(frames[1].entries[0].packet_class == PacketClass::Reliable);
    CHECK(frames[2].entries[0].packet_class == PacketClass::Reliable);
    CHECK(frames[1].entries[0].seq == frames[2].entries[0].seq + 1);
    CHECK(peer.Resends() == 1);
    return true;
}

int main() {
    if (!UnreliableTransfersItsOwnedPayload() || !ReliableRetainsItsPayloadForRetransmission() ||
        !FreshAndRetriedPacketsKeepWireOrderAcrossFrames())
        return 1;
    std::cout << "Shared stream: unreliable Flush payload allocations 1 -> 0; reliable resend preserved\n";
}
