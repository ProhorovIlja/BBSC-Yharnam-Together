// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include "core/libraries/network/rpc_bridge.h"
#include "core/libraries/network/rpc_local_send.h"

#include <array>
#include <chrono>
#include <mutex>
#include <random>
#include <span>
#include <thread>
#include <vector>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <cerrno>
#include <fcntl.h>
#include <netinet/in.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>
#endif

#include "common/logging/log.h"
#include "coop/rpc_tunnel.h"
#include "core/libraries/network/server_link.h"

namespace Libraries::Net {
namespace {

#ifdef _WIN32
using Socket = SOCKET;
constexpr Socket NoSocket = INVALID_SOCKET;
void CloseSocket(Socket socket) {
    closesocket(socket);
}
#else
using Socket = int;
constexpr Socket NoSocket = -1;
void CloseSocket(Socket socket) {
    close(socket);
}
#endif

u32 NewRpcInstance(u32 previous = 0) {
    std::random_device random;
    const u32 next = static_cast<u32>(random()) | 1u;
    return next == previous ? (next ^ 2u) : next;
}

constexpr int TickMs = 5;
constexpr size_t MaxRequestUnackedBytes = 1 << 20;

s64 NowMs() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now().time_since_epoch())
        .count();
}

// Whether `socket` has something to read (a connection, bytes, its end) within `ms`.
bool Readable(Socket socket, int ms) {
#ifdef _WIN32
    fd_set read_set;
    FD_ZERO(&read_set);
    FD_SET(socket, &read_set);
    timeval timeout{0, ms * 1000};
    return select(0, &read_set, nullptr, nullptr, &timeout) > 0;
#else
    // FD_SET is undefined for POSIX descriptors at or above FD_SETSIZE.
    pollfd watched{socket, POLLIN, 0};
    return poll(&watched, 1, ms) > 0 && (watched.revents & (POLLIN | POLLHUP | POLLERR));
#endif
}

class Bridge {
public:
    u16 Start() {
        std::scoped_lock lock{mutex};
        if (port != 0) {
            return port;
        }
        listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (listener == NoSocket) {
            return 0;
        }
        sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        address.sin_port = 0;
        socklen_t size = sizeof(address);
        if (bind(listener, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0 ||
            listen(listener, 4) != 0 ||
            getsockname(listener, reinterpret_cast<sockaddr*>(&address), &size) != 0) {
            LOG_ERROR(Lib_Net, "Rpc bridge: no listener on 127.0.0.1");
            CloseSocket(listener);
            listener = NoSocket;
            return 0;
        }
        port = ntohs(address.sin_port);
        std::thread{[this] { Run(); }}.detach();
        LOG_INFO(Lib_Net, "Rpc bridge: shadNet's calls go through the server link (127.0.0.1:{})",
                 port);
        return port;
    }

private:
    void Run() {
        std::array<u8, 16384> buffer{};
        while (true) {
            const s64 now_ms = NowMs();
            if (client == NoSocket) {
                if (Readable(listener, TickMs)) {
                    Accept(now_ms);
                }
            } else if (!tunnel.CanWriteRequest(buffer.size(), MaxRequestUnackedBytes)) {
                // Leave unread request bytes in TCP while exchanging ACKs.
                if (read_pause.Expired(now_ms)) {
                    LOG_ERROR(Lib_Net, "Rpc bridge: request queue remained full");
                    DropClient();
                    tunnel.Close(now_ms);
                } else {
                    std::this_thread::sleep_for(std::chrono::milliseconds(TickMs));
                }
            } else if ((read_pause.Reset(), Readable(client, TickMs))) {
                const int got =
                    recv(client, reinterpret_cast<char*>(buffer.data()), buffer.size(), 0);
                if (got > 0) {
                    if (!tunnel.TryWrite({buffer.data(), static_cast<size_t>(got)}, now_ms,
                                         MaxRequestUnackedBytes)) {
                        LOG_ERROR(Lib_Net, "Rpc bridge: local request exceeded the unacknowledged budget");
                        DropClient();
                        tunnel.Close(now_ms);
                    }
                } else if (got == 0 || !RpcLocal::WasInterrupted()) {
                    LOG_INFO(Lib_Net, "Rpc bridge: the game's connection ended");
                    DropClient();
                    tunnel.Close(now_ms);
                }
            }
            // A new connection while one is open replaces it (the game reconnected).
            if (client != NoSocket && Readable(listener, 0)) {
                DropClient();
                tunnel.Close(now_ms);
                Accept(now_ms);
            }
            Exchange(buffer);
        }
    }

    void Accept(s64 now_ms) {
        client = accept(listener, nullptr, nullptr);
        if (client == NoSocket) {
            return;
        }
        if (!RpcLocal::ConfigureLocalSend(client)) {
            LOG_ERROR(Lib_Net, "Rpc bridge: could not configure safe local TCP sends");
            DropClient();
            return;
        }
        if (!tunnel.TryOpen(now_ms, MaxRequestUnackedBytes)) {
            LOG_ERROR(Lib_Net, "Rpc bridge: previous requests have not drained");
            DropClient();
        }
    }

    void DropClient() {
        read_pause.Reset();
        if (client != NoSocket) {
            CloseSocket(client);
            client = NoSocket;
        }
    }

    // What came from shadNet to the game's connection, and what the tunnel sends.
    void Exchange(std::array<u8, 16384>& buffer) {
        for (int count = 0; count < 256; ++count) {
            const int size = ServerRpcReceive(buffer.data(), static_cast<u32>(buffer.size()));
            if (size < 0) {
                break;
            }
            auto events = tunnel.Receive({buffer.data(), static_cast<size_t>(size)}, NowMs());
            if (tunnel.Broken()) {
                LOG_ERROR(Lib_Net, "Rpc bridge: invalid reply stream; reopening on the next local connection");
                DropClient();
                instance = NewRpcInstance(instance);
                tunnel = NewTunnel();
                break;
            }
            for (auto& event : events) {
                using Kind = BloodborneCoop::RpcTunnel::Event::Kind;
                if (event.kind == Kind::Data && client != NoSocket) {
                    if (!RpcLocal::SendAll(client, event.bytes)) {
                        LOG_ERROR(Lib_Net, "Rpc bridge: local TCP reply write failed or timed out");
                        DropClient();
                        tunnel.Close(NowMs());
                    }
                } else if ((event.kind == Kind::Closed || event.kind == Kind::PeerRestarted) &&
                           client != NoSocket) {
                    // shadNet's end is over (or shadNet restarted): the game's client sees its
                    // connection end and connects again.
                    LOG_INFO(Lib_Net, "Rpc bridge: shadNet ended the connection");
                    DropClient();
                }
            }
        }
        for (const auto& body : tunnel.Flush(NowMs())) {
            ServerRpcSend(body.data(), static_cast<u32>(body.size()));
        }
    }

    std::mutex mutex;
    u16 port = 0;
    Socket listener = NoSocket;
    Socket client = NoSocket;
    BloodborneCoop::RpcReadPause read_pause;
    u32 instance = NewRpcInstance();
    BloodborneCoop::RpcTunnel NewTunnel() const {
        return {"game", instance, BloodborneCoop::RpcTunnel::TransportLimits()};
    }
    BloodborneCoop::RpcTunnel tunnel = NewTunnel();
};

Bridge& Instance() {
    static Bridge bridge;
    return bridge;
}

} // namespace

u16 StartRpcBridge() {
    return Instance().Start();
}

} // namespace Libraries::Net
