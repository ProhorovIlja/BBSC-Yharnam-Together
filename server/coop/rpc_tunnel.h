// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later

// Phase 11, one port: the game's calls that went over shadNet's TCP port (the NP sign-in, friends,
// scores) ride the server link instead, in its Rpc datagrams. Each side keeps one tunnel per game:
// the game's end takes the bytes of a local TCP connection the game's shadNet client makes, the
// server's end hands them to shadNet's own TCP port on 127.0.0.1, so nothing changes for either.
//
// The tunnel is a reliable stream (coop/coop_stream.h) of messages, each a byte saying what it is
// and its bytes: Open (a connection starts; one before is over), Data (its bytes, in order) and
// Close (it is over). A side whose peer restarted lost the connection: Receive says Closed then.
#pragma once

#include <algorithm>
#include <span>
#include <string>
#include <utility>
#include <vector>

#include "coop/coop_stream.h"

namespace BloodborneCoop {

class RpcTunnel {
public:
    enum class Message : u8 { Open = 1, Data = 2, Close = 3 };
    struct Event {
        enum class Kind { Opened, Data, Closed };
        Kind kind = Kind::Data;
        std::vector<u8> bytes; // Data only
        bool operator==(const Event&) const = default;
    };

    RpcTunnel(std::string self, u32 instance) : stream{std::move(self), instance} {}
    RpcTunnel(std::string self, u32 instance, CoopStream::Limits limits)
        : stream{std::move(self), instance, limits} {}

    // This end's connection: it started, sent bytes, or is over.
    void Open(s64 now_ms) {
        Put(Message::Open, {}, now_ms);
        open = true;
    }
    // TCP is a byte stream. A coalesced read must not become a single
    // message above the receiver's per-message reassembly limit.
    static constexpr size_t MaxDataBytes = 16 * 1024;
    void Write(std::span<const u8> bytes, s64 now_ms) {
        while (!bytes.empty()) {
            const auto n = (std::min)(bytes.size(), MaxDataBytes);
            Put(Message::Data, bytes.first(n), now_ms);
            bytes = bytes.subspan(n);
        }
    }

    // Reserve one close message (opcode and fragment header) when desired by
    // the caller by passing a smaller data budget. Count before copying data.
    [[nodiscard]] bool CanQueueWrite(size_t bytes, size_t budget) const {
        const auto used = UnackedBytes();
        if (used > budget || bytes > budget - used) return false;
        const auto remaining = budget - used - bytes;
        const auto full = bytes / MaxDataBytes;
        const auto tail = bytes % MaxDataBytes;
        constexpr auto full_overhead = 2 + MaxDataBytes / CoopStream::ChunkBytes;
        const auto tail_overhead = tail ? 2 + tail / CoopStream::ChunkBytes : 0;
        return tail_overhead <= remaining && full <= (remaining - tail_overhead) / full_overhead;
    }
    void Close(s64 now_ms) {
        if (open) {
            Put(Message::Close, {}, now_ms);
            open = false;
        }
    }

    // A Rpc datagram's body from the other end: what happened to the connection there.
    std::vector<Event> Receive(std::span<const u8> body, s64 now_ms) {
        std::vector<Event> events;
        std::vector<std::vector<u8>> messages = stream.Receive(body, now_ms);
        if (stream.TakeRestarted() && open) {
            open = false;
            events.push_back({Event::Kind::Closed, {}});
        }
        for (std::vector<u8>& message : messages) {
            if (message.empty()) {
                continue;
            }
            switch (static_cast<Message>(message[0])) {
            case Message::Open:
                open = true;
                events.push_back({Event::Kind::Opened, {}});
                break;
            case Message::Data:
                // A closed or restarted tunnel no longer owns a TCP
                // connection. Don't deliver data to the old endpoint.
                if (!open || message.size() == 1)
                    break;
                message.erase(message.begin());
                events.push_back({Event::Kind::Data, std::move(message)});
                break;
            case Message::Close:
                open = false;
                events.push_back({Event::Kind::Closed, {}});
                break;
            }
        }
        return events;
    }

    // The Rpc datagram bodies to send now (messages, resends and acks).
    std::vector<std::vector<u8>> Flush(s64 now_ms) {
        return stream.Flush(now_ms);
    }

    // Whether a connection is open through the tunnel, as this end knows it.
    bool IsOpen() const {
        return open;
    }
    size_t Unacked() const {
        return stream.Unacked();
    }
    size_t UnackedBytes() const {
        return stream.UnackedBytes();
    }
    // The other end went past this end's limits (CoopStream::Broken).
    bool Broken() const {
        return stream.Broken();
    }

private:
    void Put(Message kind, std::span<const u8> bytes, s64 now_ms) {
        std::vector<u8> message;
        message.reserve(bytes.size() + 1);
        message.push_back(static_cast<u8>(kind));
        message.insert(message.end(), bytes.begin(), bytes.end());
        stream.Send(message, now_ms);
    }

    CoopStream stream;
    bool open = false;
};

} // namespace BloodborneCoop
