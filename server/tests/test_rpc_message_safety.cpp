// SPDX-License-Identifier: GPL-2.0-or-later
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>
#include "coop/rpc_tunnel.h"

using BloodborneCoop::CoopStream;
using BloodborneCoop::RpcTunnel;
using Kind = RpcTunnel::Event::Kind;

#define REQUIRE(expr) do { if (!(expr)) { std::cerr << "FAIL " << __LINE__ << ": " #expr "\n"; return 1; } } while (false)

int main() {
    CoopStream::Limits limits{};
    limits.message_bytes = 64 * 1024;
    limits.chunk_bytes = CoopStream::ChunkBytes + 1;
    limits.held_bytes = 256 * 1024;
    limits.unreliable_channels = 16;

    RpcTunnel server{"shadnet", 13};
    RpcTunnel game{"game", 7, limits};
    const std::vector<u8> before{'b', 'a', 'd'};
    server.Write(before, 0);
    REQUIRE(server.UnackedBytes() == 0); // No data before Open.
    server.Open(0);
    auto opening = server.Flush(0);
    REQUIRE(!opening.empty());
    bool opened = false;
    for (const auto& frame : opening) {
        for (const auto& event : game.Receive(frame, 0)) {
            REQUIRE(event.kind == Kind::Opened);
            opened = true;
        }
    }
    REQUIRE(opened);
    for (const auto& ack : game.Flush(0)) server.Receive(ack, 0);

    std::vector<u8> expected(512 * 1024 + 17);
    for (size_t i = 0; i < expected.size(); ++i)
        expected[i] = static_cast<u8>((i * 31 + i / 97) % 251);
    server.Write(expected, 1);
    server.Close(1);
    REQUIRE(!server.IsOpen());
    // The reply already queued before Close must arrive ahead of Close.
    std::vector<u8> got;
    bool closed = false;
    size_t packets = 0;
    for (const auto& frame : server.Flush(2)) {
        for (const auto& event : game.Receive(frame, 2)) {
            if (event.kind == Kind::Data) {
                REQUIRE(!closed);
                REQUIRE(!event.bytes.empty());
                REQUIRE(event.bytes.size() <= RpcTunnel::MaxDataBytes);
                got.insert(got.end(), event.bytes.begin(), event.bytes.end());
            } else {
                REQUIRE(event.kind == Kind::Closed);
                closed = true;
            }
        }
        ++packets;
    }
    REQUIRE(packets > 1);
    REQUIRE(closed && got == expected);
    REQUIRE(!game.Broken());
    for (const auto& ack : game.Flush(2)) server.Receive(ack, 2);
    REQUIRE(server.UnackedBytes() == 0);
    server.Write(before, 3);
    REQUIRE(server.UnackedBytes() == 0); // No data after Close.

    // Deliberately encode malformed controls through the *actual* CoopStream
    // to prove that a trailing payload never opens/closes an RPC session.
    CoopStream raw{"game", 31};
    RpcTunnel receiver{"shadnet", 37, limits};
    const auto deliver = [&](std::vector<u8> bytes, s64 tick) {
        raw.Send(bytes, tick);
        std::vector<RpcTunnel::Event> events;
        for (const auto& wire : raw.Flush(tick))
            for (auto& e : receiver.Receive(wire, tick))
                events.push_back(std::move(e));
        for (const auto& ack : receiver.Flush(tick)) raw.Receive(ack, tick);
        return events;
    };
    REQUIRE(deliver({1, 99}, 10).empty() && !receiver.IsOpen());
    REQUIRE(deliver({2, 99}, 11).empty() && !receiver.IsOpen());
    REQUIRE(deliver({1}, 12).size() == 1 && receiver.IsOpen());
    REQUIRE(deliver({3, 99}, 13).empty() && receiver.IsOpen());
    REQUIRE(deliver({2}, 14).empty() && receiver.IsOpen());
    auto valid = deliver({2, 'x'}, 15);
    REQUIRE(valid.size() == 1 && valid[0].kind == Kind::Data &&
            valid[0].bytes == std::vector<u8>{'x'});
    REQUIRE(deliver({3}, 16).size() == 1 && !receiver.IsOpen());
    REQUIRE(deliver({2, 'y'}, 17).empty());
    // Exact shared transport under loss and a stalled ACK path. The backend
    // emits 512 KiB and then Close; every 13th initial frame is dropped, ACKs
    // remain blocked for 500 ms, and the receiver's out-of-order buffer is
    // capped at 256 KiB. Resends must eventually deliver every byte exactly
    // once in order and retire all sender reliable bytes.
    RpcTunnel loss_sender{"shadnet", 43};
    RpcTunnel loss_receiver{"game", 47, limits};
    loss_sender.Open(0);
    loss_sender.Write(expected, 0);
    loss_sender.Close(0);
    std::vector<u8> restored;
    bool loss_open = false;
    bool loss_closed = false;
    size_t simulated_loss = 0;
    size_t resent_frames = 0;
    for (s64 tick = 0; tick < 20'000; tick += 100) {
        size_t frame_index = 0;
        const auto frames = loss_sender.Flush(tick);
        if (tick > 0) resent_frames += frames.size();
        for (const auto& frame : frames) {
            const bool drop = tick == 0 && frame_index % 13 == 0;
            ++frame_index;
            if (drop) {
                ++simulated_loss;
                continue;
            }
            for (const auto& event : loss_receiver.Receive(frame, tick)) {
                if (event.kind == Kind::Opened) {
                    REQUIRE(!loss_open && !loss_closed);
                    loss_open = true;
                } else if (event.kind == Kind::Data) {
                    REQUIRE(loss_open && !loss_closed);
                    restored.insert(restored.end(), event.bytes.begin(), event.bytes.end());
                    REQUIRE(restored.size() <= expected.size());
                } else {
                    REQUIRE(event.kind == Kind::Closed && loss_open && !loss_closed);
                    loss_closed = true;
                }
            }
        }
        // Hold client ACKs for 500ms, then restore the return path.
        for (const auto& ack : loss_receiver.Flush(tick)) {
            if (tick >= 500) loss_sender.Receive(ack, tick);
        }
        REQUIRE(!loss_receiver.Broken());
        if (loss_closed && loss_sender.UnackedBytes() == 0) break;
    }
    REQUIRE(simulated_loss > 0 && resent_frames > 0);
    REQUIRE(loss_open && loss_closed && restored == expected);
    REQUIRE(loss_sender.UnackedBytes() == 0);
    std::cout << "RPC 512KiB ordered reply, lost frames, paused ACK recovery, malformed controls passed\n";
    return 0;
}
