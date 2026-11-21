// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <span>
#include <stop_token>
#ifdef _WIN32
#include <winsock2.h>
#else
#include <cerrno>
#include <sys/socket.h>
#include <sys/time.h>
#endif

namespace Libraries::Net::RpcLocal {
#ifdef _WIN32
using Socket = SOCKET;
#else
using Socket = int;
#endif

constexpr int LocalSendTimeoutMs = 100;
constexpr int LocalReplyBudgetMs = 250;

inline bool ConfigureLocalSend(Socket socket) {
#if !defined(_WIN32) && !defined(MSG_NOSIGNAL) && defined(SO_NOSIGPIPE)
    const int enabled = 1;
    if (setsockopt(socket, SOL_SOCKET, SO_NOSIGPIPE, &enabled, sizeof(enabled)) != 0)
        return false;
#endif
#ifdef _WIN32
    const DWORD timeout = LocalSendTimeoutMs;
#else
    const timeval timeout{0, LocalSendTimeoutMs * 1000};
#endif
    return setsockopt(socket, SOL_SOCKET, SO_SNDTIMEO,
                      reinterpret_cast<const char*>(&timeout), sizeof(timeout)) == 0;
}

inline bool WasInterrupted() {
#ifdef _WIN32
    return WSAGetLastError() == WSAEINTR;
#else
    return errno == EINTR;
#endif
}

inline std::int64_t NowMs() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now().time_since_epoch()).count();
}

inline bool SendAll(Socket socket, std::span<const std::uint8_t> bytes,
                    std::stop_token stop = {}) {
#if !defined(_WIN32) && defined(MSG_NOSIGNAL)
    constexpr int flags = MSG_NOSIGNAL;
#else
    constexpr int flags = 0;
#endif
    const auto deadline = NowMs() + LocalReplyBudgetMs;
    size_t sent = 0;
    while (sent < bytes.size()) {
        if (stop.stop_requested() || NowMs() >= deadline)
            return false;
        const int rc = send(socket, reinterpret_cast<const char*>(bytes.data() + sent),
                            static_cast<int>(bytes.size() - sent), flags);
        if (rc < 0 && WasInterrupted())
            continue;
        if (rc <= 0) {
            return false;
        }
        sent += static_cast<size_t>(rc);
    }
    return true;
}

} // namespace Libraries::Net::RpcLocal
