// SPDX-License-Identifier: GPL-2.0-or-later
// Production client bridge and real loopback TCP; only the server-link wire is substituted.
#include <arpa/inet.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <atomic>
#include <cassert>
#include <chrono>
#include <cstring>
#include <deque>
#include <cstdio>
#include <source_location>
#include <cstdlib>
#include <thread>

#include "coop/rpc_tunnel.h"
#include "core/libraries/network/rpc_bridge.h"
#include "core/libraries/network/rpc_local_send.h"
#include "core/libraries/network/server_link.h"

using BloodborneCoop::RpcTunnel;
using Kind = RpcTunnel::Event::Kind;
using namespace std::chrono_literals;

namespace {
struct Peer {
    RpcTunnel tunnel{"shadnet", 9, RpcTunnel::TransportLimits()};
    std::deque<std::vector<u8>> inbound;
    std::vector<u8> held_reply;
    std::atomic<bool> hold_ack{true};
    std::atomic<bool> replace_server{false};
    std::atomic<bool> inject_old{false};
    std::atomic<int> invalid_lengths{0};
    std::atomic<bool> stage_reply{false};
    std::atomic<bool> reply_staged{false};
    std::atomic<int> closes{0};
    std::atomic<int> opens{0};
    std::atomic<size_t> received{0};
    std::atomic<bool> ordered{true};
    size_t offset = 0; // Only the bridge thread touches the remote tunnel.
};

Peer& Remote() {
    // Same lifetime as the bridge's detached worker in this process.
    static auto* peer = new Peer;
    return *peer;
}

u8 Pattern(size_t i) {
    return static_cast<u8>((i ^ (i >> 8) ^ (i >> 16)) & 255);
}

int Connect(u16 port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    assert(fd >= 0);
    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = htons(port);
    assert(connect(fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == 0);
    return fd;
}

template <typename Predicate>
void Await(Predicate ready, std::source_location where = std::source_location::current()) {
    auto deadline = std::chrono::steady_clock::now() + 4s;
    while (!ready()) {
        if (std::chrono::steady_clock::now() >= deadline) {
            std::fprintf(stderr, "RPC loopback deadline at %s:%u\n",
                         where.file_name(), static_cast<unsigned>(where.line()));
            std::abort();
        }
        std::this_thread::sleep_for(5ms);
    }
}

void SendPayload(int fd, const std::vector<u8>& bytes) {
    for (size_t at = 0; at < bytes.size(); at += 16384) {
        assert(Libraries::Net::RpcLocal::SendAll(
            fd, std::span(bytes).subspan(at, (std::min)(size_t{16384}, bytes.size() - at))));
    }
}
} // namespace

namespace Libraries::Net {
bool ServerRpcSend(const void* body, u32 len) {
    auto& p = Remote();
    const auto now = RpcLocal::NowMs();
    for (const auto& event : p.tunnel.Receive({static_cast<const u8*>(body), len}, now)) {
        if (event.kind == Kind::Opened) {
            p.offset = 0;
            p.received = 0;
            ++p.opens;
        } else if (event.kind == Kind::Closed) {
            ++p.closes;
        } else if (event.kind == Kind::Data) {
            for (u8 value : event.bytes) {
                if (value != Pattern(p.offset++)) {
                    p.ordered = false;
                }
            }
            p.received = p.offset;
        }
    }
    return true;
}

int ServerRpcReceive(void* body, u32 len) {
    auto& p = Remote();
    // A truncated/empty adapter result must not poison the live stream.
    // Copy a plausible header, then claim bytes past the caller's buffer.
    const int invalid = p.invalid_lengths.exchange(0);
    if (invalid == 2) {
        // Use the active instance: a retired header would be rejected even
        // without the length guard and would not exercise this boundary.
        const std::array<u8, 1> valid{0xAB};
        p.tunnel.Write(valid, RpcLocal::NowMs());
        auto frames = p.tunnel.Flush(RpcLocal::NowMs());
        assert(!frames.empty() && frames.back().size() <= len);
        const auto& current = frames.back();
        std::memcpy(body, current.data(), current.size());
        for (auto& frame : frames)
            p.inbound.push_back(std::move(frame));
        p.invalid_lengths = 1;
        return static_cast<int>(len) + 1;
    }
    if (invalid == 1)
        return 0;
    const auto now = RpcLocal::NowMs();
    if (p.replace_server.exchange(false)) {
        p.inbound.clear();
        p.tunnel = RpcTunnel{"shadnet", 10, RpcTunnel::TransportLimits()};
    }
    // Keep one addressed reply from the current stream for delayed delivery.
    if (p.stage_reply.exchange(false)) {
        const std::array<u8, 1> stale{0xEE};
        p.tunnel.Write(stale, now);
        auto frames = p.tunnel.Flush(now);
        assert(frames.size() == 1);
        p.held_reply = std::move(frames.front());
        p.reply_staged = true;
    }
    if (p.inject_old.exchange(false)) {
        assert(!p.held_reply.empty());
        p.inbound.push_back(p.held_reply);
        const std::array<u8, 1> fresh{0xAB};
        p.tunnel.Write(fresh, now);
    }
    if (!p.hold_ack) {
        for (auto& frame : p.tunnel.Flush(now)) {
            p.inbound.push_back(std::move(frame));
        }
    }
    if (p.inbound.empty()) {
        return -1;
    }
    auto frame = std::move(p.inbound.front());
    p.inbound.pop_front();
    assert(frame.size() <= len);
    std::memcpy(body, frame.data(), frame.size());
    return static_cast<int>(frame.size());
}
} // namespace Libraries::Net

int main() {
    const u16 port = Libraries::Net::StartRpcBridge();
    assert(port != 0);
    auto& p = Remote();
    std::vector<u8> payload(1280 * 1024);
    for (size_t i = 0; i < payload.size(); ++i) {
        payload[i] = Pattern(i);
    }
    int first = Connect(port);
    SendPayload(first, payload);
    Await([&] { return p.received > 192 * 1024; });
    std::this_thread::sleep_for(120ms);
    // No ACKs: the wire stalls at the reorder window, even though the local
    // request queue has a larger independent cap.
    assert(p.received <= RpcTunnel::TransportLimits().held_bytes);
    p.hold_ack = false;
    Await([&] { return p.received == payload.size(); });
    assert(p.ordered);

    // A live replacement supersedes the old stream. Inject an old addressed
    // response before the fresh one: only the fresh byte may reach the new TCP client.
    p.stage_reply = true;
    Await([&] { return p.reply_staged.load(); });
    int second = Connect(port);
    Await([&] { return p.opens == 2; });
    p.inject_old = true;
    pollfd response{second, POLLIN, 0};
    assert(poll(&response, 1, 4000) == 1);
    u8 byte = 0;
    assert(recv(second, &byte, 1, 0) == 1 && byte == 0xAB);
    close(first);

    p.hold_ack = true;
    SendPayload(second, payload);
    Await([&] { return p.received > 192 * 1024; });
    pollfd ended{second, POLLIN, 0};
    assert(poll(&ended, 1, 8000) == 1);
    assert(recv(second, &byte, 1, 0) <= 0);
    close(second);

    // With the previous budget abandoned, a new connection can send even
    // before an ACK to the old stream would have arrived.
    const int third = Connect(port);
    Await([&] { return p.opens == 3; });
    p.hold_ack = false;
    SendPayload(third, std::vector<u8>(payload.begin(), payload.begin() + 32));
    Await([&] { return p.received == 32; });
    assert(p.ordered);
    p.reply_staged = false;
    p.stage_reply = true;
    Await([&] { return p.reply_staged.load(); });
    close(third);
    Await([&] { return p.closes > 0; });
    const int fourth = Connect(port);
    Await([&] { return p.opens == 4; });
    p.invalid_lengths = 2;
    response = {fourth, POLLIN, 0};
    assert(poll(&response, 1, 4000) == 1);
    assert(recv(fourth, &byte, 1, 0) == 1 && byte == 0xAB);
    // Model the server discarding a tunnel at sign-in loss, while the
    // bridge still owns a local TCP stream. A fresh server instance must
    // close that stream; an old addressed reply cannot reach the next one.
    p.reply_staged = false;
    p.stage_reply = true;
    Await([&] { return p.reply_staged.load(); });
    p.replace_server = true;
    response = {fourth, POLLIN, 0};
    assert(poll(&response, 1, 4000) == 1);
    assert(recv(fourth, &byte, 1, 0) == 0);
    close(fourth);
    const int fifth = Connect(port);
    Await([&] { return p.opens == 5; });
    p.inject_old = true;
    response = {fifth, POLLIN, 0};
    assert(poll(&response, 1, 4000) == 1);
    assert(recv(fifth, &byte, 1, 0) == 1 && byte == 0xAB);
    close(fifth);
    // Avoid destructors racing the intentionally process-lifetime worker.
    _exit(0);
}
