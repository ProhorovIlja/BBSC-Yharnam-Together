// SPDX-License-Identifier: GPL-2.0-or-later
// Exercise payload ownership in the real shared client/server stream, without network timing.
#include <cstdlib>
#include <iostream>
#include <new>
#include <vector>

#include "coop/game_link.h"
#include "coop/coop_stream.h"

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

static bool WireRejectsImpossibleCountsAndSplitsAtTheWireLimit() {
    GameFrame malformed{"host", 1, 0, 0, {}};
    auto header = EncodeGameFrame(malformed);
    CHECK(!header.empty());
    header.back() = 0xff; // a nonzero high byte, but no entries
    CHECK(!DecodeGameFrame(header));
    malformed.entries.resize(65536);
    CHECK(EncodeGameFrame(malformed).empty());

    GameLinkPeer::Settings settings;
    settings.frame_bytes = 2'000'000;
    GameLinkPeer peer{"host", 1, settings};
    const std::vector<u8> payload{4, 0, 0, 0};
    for (size_t i = 0; i < 65536; ++i) peer.Send(PacketClass::Unreliable, payload, 0);
    const auto frames = peer.Flush(0);
    CHECK(frames.size() == 2);
    CHECK(frames[0].entries.size() == 65535 && frames[1].entries.size() == 1);
    for (const auto& frame : frames) {
        auto read = DecodeGameFrame(EncodeGameFrame(frame));
        CHECK(read && *read == frame);
    }
    settings.frame_bytes = 100;
    GameLinkPeer long_name{std::string(64, 'x'), 2, settings};
    long_name.Send(PacketClass::Unreliable, payload, 0);
    long_name.Send(PacketClass::Unreliable, payload, 0);
    const auto split = long_name.Flush(0);
    CHECK(split.size() == 2);
    for (const auto& frame : split) CHECK(EncodeGameFrame(frame).size() <= 100);
    return true;
}

static bool OwnedReceivePreservesPayloadStorageAndReliableOrder() {
    GameLinkPeer peer{"guest", 2};
    const std::vector<u8> first(PayloadBytes, 0x29), second(PayloadBytes, 0x2a);
    GameFrame later{"host", 1, 2, 0, {{PacketClass::Reliable, 1, second}}};
    GameFrame early{"host", 1, 2, 0, {{PacketClass::Reliable, 0, first}}};
    const auto* stored_later = later.entries[0].packet.data();
    const auto* stored_early = early.entries[0].packet.data();
    payload_allocations = 0;
    measuring = true;
    const auto held = peer.Receive(std::move(later), 0);
    const auto delivered = peer.Receive(std::move(early), 1);
    measuring = false;
    CHECK(held.empty() && peer.HeldBytes() == 0);
    CHECK(payload_allocations == 0 && delivered.size() == 2);
    CHECK(delivered[0].data() == stored_early && delivered[1].data() == stored_later);
    CHECK(delivered[0] == first && delivered[1] == second);
    CHECK(peer.Receive(GameFrame{"host", 1, 2, 0, {{PacketClass::Reliable, 0, first}}}, 2).empty());

    const GameFrame borrowed{"host", 1, 2, 0, {{PacketClass::Reliable, 2, first}}};
    const auto copied = peer.Receive(borrowed, 3);
    CHECK(copied.size() == 1 && copied[0] == first);
    CHECK(borrowed.entries[0].packet == first);
    return true;
}

static bool CoopStreamTransfersSingleAndReassemblesSplitMessages() {
    CoopStream a{"host", 1}, b{"guest", 2};
    for (const size_t size : {size_t{0}, size_t{4}, CoopStream::ChunkBytes,
                              2 * CoopStream::ChunkBytes + 1}) {
        std::vector<u8> data(size, 0x35);
        a.Send(data, 0);
        auto frames = a.Flush(0);
        CHECK(!frames.empty());
        std::vector<std::vector<u8>> all;
        for (const auto& frame : frames) {
            for (auto& message : b.Receive(frame, 0)) all.push_back(std::move(message));
        }
        CHECK(all.size() == 1 && all[0] == data && !b.Broken());
        for (const auto& ack : b.Flush(0)) a.Receive(ack, 0);
        CHECK(a.Unacked() == 0);
    }
    CoopStream limited{"guest", 3, {.message_bytes = 2, .chunk_bytes = 8}};
    const GameFrame oversized{"host", 1, 3, 0, {{PacketClass::Reliable, 0, {1, 1, 2, 3}}}};
    CHECK(limited.Receive(EncodeGameFrame(oversized), 0).empty() && limited.Broken());
    return true;
}

static bool CoopStreamRejectsBeforeQueueingAndCountsChunkMarkers() {
    CoopStream a{"host", 1}, b{"guest", 2};
    const std::vector<u8> first(CoopStream::ChunkBytes + 1, 4);
    const std::vector<u8> next{7};
    const size_t exact = first.size() + 2;
    CHECK(!a.SendWithinUnackedLimit(first, 0, exact - 1));
    CHECK(a.Unacked() == 0 && a.UnackedBytes() == 0);
    CHECK(a.SendWithinUnackedLimit(first, 0, exact));
    CHECK(!a.SendWithinUnackedLimit(next, 0, exact + 1));
    CHECK(a.Unacked() == 2 && a.UnackedBytes() == exact);
    std::vector<std::vector<u8>> got;
    for (const auto& frame : a.Flush(0)) {
        for (auto& message : b.Receive(frame, 0)) got.push_back(std::move(message));
    }
    CHECK(got.size() == 1 && got[0] == first);
    for (const auto& ack : b.Flush(0)) a.Receive(ack, 0);
    CHECK(a.UnackedBytes() == 0);
    CHECK(!a.SendWithinUnackedLimit({}, 1, 0));
    CHECK(a.SendWithinUnackedLimit({}, 1, 1));
    CHECK(a.SendWithinUnackedLimit(next, 1, 3));
    got.clear();
    for (const auto& frame : a.Flush(1)) {
        for (auto& message : b.Receive(frame, 1)) got.push_back(std::move(message));
    }
    CHECK(got.size() == 2 && got[0].empty() && got[1] == next);
    return true;
}

int main() {
    if (!UnreliableTransfersItsOwnedPayload() || !ReliableRetainsItsPayloadForRetransmission() ||
        !FreshAndRetriedPacketsKeepWireOrderAcrossFrames() ||
        !WireRejectsImpossibleCountsAndSplitsAtTheWireLimit() ||
        !OwnedReceivePreservesPayloadStorageAndReliableOrder() ||
        !CoopStreamTransfersSingleAndReassemblesSplitMessages() ||
        !CoopStreamRejectsBeforeQueueingAndCountsChunkMarkers())
        return 1;
    std::cout << "Shared stream: unreliable Flush payload allocations 1 -> 0; reliable resend preserved\n";
}
