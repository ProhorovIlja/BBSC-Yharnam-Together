// SPDX-License-Identifier: GPL-2.0-or-later
#include <iostream>
#include <limits>
#include <vector>

#include "coop/coop_stream.h"

using namespace BloodborneCoop;

#define CHECK(value) do { if (!(value)) { std::cerr << __func__ << ':' << __LINE__ << ": " << #value << '\n'; return false; } } while (false)

static std::vector<u8> Packet(u32 channel, u8 marker) {
    std::vector<u8> bytes;
    GameLinkDetail::Put(bytes, channel);
    GameLinkDetail::Put(bytes, u32{1});
    bytes.push_back(marker);
    return bytes;
}

static bool WrongRecipientCannotResetOrAcknowledgeTheCurrentStream() {
    for (u32 remote : {2u, 3u}) {
        GameLinkPeer host{"host", 1};
        host.Receive(GameFrame{"guest", 2, 1, 0, {}}, 100);
        host.Send(PacketClass::Reliable, Packet(7, 1), 101);
        host.Flush(101);
        // A delayed frame for a former local game must not change even the
        // apparent remote instance, cumulative ACK or current stream liveness.
        const GameFrame stale{"guest", remote, 999, std::numeric_limits<u32>::max(),
                              {{PacketClass::Reliable, 0, Packet(7, 99)}}};
        CHECK(host.Receive(stale, 200).empty());
        CHECK(host.Restarts() == 0);
        CHECK(host.Unacked() == 1);
        CHECK(host.UnackedBytes() == Packet(7, 1).size());
        CHECK(host.SilentFor(210) == 110);
        const auto frames = host.Flush(210);
        CHECK(frames.size() == 1);
        CHECK(frames.front().peer_instance == 2);
        CHECK(frames.front().ack == 0);
    }
    return true;
}

static bool OldQueuedVisualsCannotPoisonTheNewSequenceSpace() {
    GameLinkPeer host{"host", 1};
    host.Receive(GameFrame{"guest", 2, 1, 0, {}}, 0);
    for (u8 i = 0; i < 64; ++i) host.Send(PacketClass::Unreliable, Packet(6, i), 1);
    host.Flush(1);
    host.Send(PacketClass::Unreliable, Packet(6, 90), 2); // still queued for the old run
    host.Receive(GameFrame{"guest", 3, 1, 0, {}}, 3);
    CHECK(host.Restarts() == 1);
    host.Send(PacketClass::Unreliable, Packet(6, 91), 4);
    const auto frames = host.Flush(4);
    CHECK(frames.size() == 1);
    CHECK(frames.front().entries.size() == 1);
    CHECK(frames.front().entries.front().seq == 0);
    CHECK(frames.front().entries.front().packet == Packet(6, 91));
    GameLinkPeer restarted{"guest", 3};
    CHECK(restarted.Receive(frames.front(), 4) == std::vector<std::vector<u8>>{Packet(6, 91)});
    host.Send(PacketClass::Unreliable, Packet(6, 92), 5);
    const auto next = host.Flush(5);
    CHECK(next.size() == 1);
    CHECK(restarted.Receive(next.front(), 5) == std::vector<std::vector<u8>>{Packet(6, 92)});
    CHECK(restarted.DroppedOld() == 0);
    return true;
}

static bool RejectedFrameCannotDiscardAPartialCoopMessage() {
    CoopStream game{"game", 1}, server{"server", 2};
    std::vector<u8> message(1500);
    for (size_t i = 0; i < message.size(); ++i) message[i] = static_cast<u8>(i);
    game.Send(message, 0);
    const auto chunks = game.Flush(0);
    CHECK(chunks.size() == 2);
    CHECK(server.Receive(chunks[0], 0).empty());
    CHECK(server.HeldBytes() == CoopStream::ChunkBytes);
    const GameFrame stale{"game", 99, 777, 0, {}};
    CHECK(server.Receive(EncodeGameFrame(stale), 1).empty());
    CHECK(!server.TakeRestarted());
    CHECK(server.HeldBytes() == CoopStream::ChunkBytes);
    CHECK(server.Receive(chunks[1], 2) == std::vector<std::vector<u8>>{message});
    CHECK(server.HeldBytes() == 0);
    return true;
}

static bool ARejectedOldTargetStillAdvertisesTheNewLocalRun() {
    GameLinkPeer restarted{"guest", 3};
    CHECK(restarted.Receive(GameFrame{"host", 1, 2, 0, {}}, 0).empty());
    CHECK(!restarted.SilentFor(0));
    const auto reply = restarted.Flush(0);
    CHECK(reply.size() == 1);
    CHECK(reply.front().instance == 3);
    GameLinkPeer host{"host", 1};
    host.Receive(reply.front(), 1);
    host.Send(PacketClass::Reliable, Packet(7, 10), 2);
    const auto current = host.Flush(2);
    CHECK(current.size() == 1);
    CHECK(restarted.Receive(current.front(), 2) == std::vector<std::vector<u8>>{Packet(7, 10)});
    return true;
}

static bool DelayedRetiredRunsCannotResetTheActiveStream() {
    GameLinkPeer host{"host", 1};
    host.Receive(GameFrame{"guest", 90, 1, 0, {}}, 100);
    host.Receive(GameFrame{"guest", 70, 1, 0, {}}, 101);
    host.Receive(GameFrame{"guest", 3, 1, 0, {}}, 102);
    host.Send(PacketClass::Reliable, Packet(7, 1), 103);
    host.Flush(103);
    CHECK(host.Receive(GameFrame{"guest", 3, 1, 0,
                                  {{PacketClass::Reliable, 1, Packet(7, 12)}}}, 104).empty());
    for (u32 retired : {90u, 70u}) {
        for (u32 target : {0u, 1u}) {
            const GameFrame stale{"guest", retired, target, 1,
                                  {{PacketClass::Reliable, 0, Packet(7, 99)}}};
            CHECK(host.Receive(stale, 200).empty());
            CHECK(host.Restarts() == 2);
            CHECK(host.Unacked() == 1);
            CHECK(host.SilentFor(210) == 106);
        }
    }
    const auto delivered = host.Receive(GameFrame{"guest", 3, 1, 1,
                                  {{PacketClass::Reliable, 0, Packet(7, 11)}}}, 211);
    const std::vector<std::vector<u8>> expected{Packet(7, 11), Packet(7, 12)};
    CHECK(delivered == expected);
    CHECK(host.Unacked() == 0);
    return true;
}

static bool StaleChunksCannotBreakTheCurrentCoopStream() {
    CoopStream receiver{"server", 1, {.message_bytes = 2048, .chunk_bytes = 1001}};
    receiver.Receive(EncodeGameFrame(GameFrame{"game", 9, 1, 0, {}}), 0);
    CoopStream sender{"game", 10};
    std::vector<u8> message(1500, 0x42);
    sender.Send(message, 1);
    const auto chunks = sender.Flush(1);
    CHECK(chunks.size() == 2);
    CHECK(receiver.Receive(chunks[0], 1).empty());
    CHECK(receiver.TakeRestarted());
    CHECK(receiver.HeldBytes() == CoopStream::ChunkBytes);

    const std::vector<u8> oversized(1002, 0);
    for (const auto& stale : {GameFrame{"game", 9, 1, 0, {{PacketClass::Reliable, 0, oversized}}},
                             GameFrame{"game", 10, 99, 0, {{PacketClass::Reliable, 0, oversized}}}}) {
        CHECK(receiver.Receive(EncodeGameFrame(stale), 2).empty());
        CHECK(!receiver.Broken() && !receiver.TakeRestarted());
        CHECK(receiver.HeldBytes() == CoopStream::ChunkBytes);
    }
    CHECK(receiver.Receive(chunks[1], 3) == std::vector<std::vector<u8>>{message});
    const GameFrame active{"game", 10, 1, 0, {{PacketClass::Reliable, 2, oversized}}};
    CHECK(receiver.Receive(EncodeGameFrame(active), 4).empty());
    CHECK(receiver.Broken());
    return true;
}

static bool MalformedChunksCannotAdvanceOrPolluteReassembly() {
    CoopStream sender{"game", 10}, receiver{"server", 1};
    const std::vector<u8> message(1500, 0x42);
    sender.Send(message, 0);
    const auto chunks = sender.Flush(0);
    CHECK(chunks.size() == 2);
    CHECK(receiver.Receive(chunks[0], 0).empty());
    CHECK(receiver.HeldBytes() == CoopStream::ChunkBytes);
    const std::vector<GameFrameEntry> invalid{
        {PacketClass::Unreliable, 1, {CoopStream::LastChunk, 99}},
        {PacketClass::Reliable, 1, {}},
        {PacketClass::Reliable, 1, {3, 99}},
        {PacketClass::Reliable, 1, {0}},
    };
    for (const auto& entry : invalid) {
        CHECK(receiver.Receive(EncodeGameFrame(GameFrame{"game", 10, 1, 0, {entry}}), 1).empty());
        CHECK(receiver.HeldBytes() == CoopStream::ChunkBytes);
        CHECK(receiver.SilentFor(2) == 2);
        CHECK(!receiver.Broken() && !receiver.TakeRestarted());
    }
    CHECK(receiver.Receive(chunks[1], 3) == std::vector<std::vector<u8>>{message});
    return true;
}

int main() {
    unsigned failed = 0;
    for (auto test : {WrongRecipientCannotResetOrAcknowledgeTheCurrentStream,
                      OldQueuedVisualsCannotPoisonTheNewSequenceSpace,
                      RejectedFrameCannotDiscardAPartialCoopMessage,
                      ARejectedOldTargetStillAdvertisesTheNewLocalRun,
                      DelayedRetiredRunsCannotResetTheActiveStream,
                      StaleChunksCannotBreakTheCurrentCoopStream,
                      MalformedChunksCannotAdvanceOrPolluteReassembly}) {
        if (!test()) ++failed;
    }
    std::cout << "Game-link restart scenarios: " << (7 - failed) << "/7 passed\n";
    return failed ? 1 : 0;
}
