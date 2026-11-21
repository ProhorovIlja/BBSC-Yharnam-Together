// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>
#include <cstddef>

namespace ShadNetRpc {
// Both Qt's connected write queue and the preconnect queue are byte budgets.
constexpr bool FitsWriteBudget(std::int64_t queued, std::int64_t incoming,
                               std::int64_t limit) {
    return queued >= 0 && incoming >= 0 && queued <= limit &&
           incoming <= limit - queued;
}

// Reply path: never read an unbounded QTcpSocket backlog into one QByteArray
// before testing how much the reliable tunnel already retains. One Rpc Data
// contains an opcode, then 1,000-byte CoopStream fragments each add a marker.
// Reserve two bytes for a subsequent Close control message.
constexpr std::size_t MaxTunnelReadSlice = 16 * 1024;
constexpr std::size_t TunnelFragmentBytes = 1000;
constexpr bool FitsTunnelReadBudget(std::size_t unacked, std::size_t incoming,
                                     std::size_t limit) {
    if (!incoming || incoming > MaxTunnelReadSlice || unacked > limit)
        return false;
    const std::size_t fragment_count =
        (incoming + 1 + TunnelFragmentBytes - 1) / TunnelFragmentBytes;
    const std::size_t room = limit - unacked;
    // Subtraction-based checks avoid overflowing when limit is near SIZE_MAX.
    return room >= 2 && incoming <= room - 2 &&
           1 + fragment_count <= room - 2 - incoming;
}

template <typename Socket>
bool TryQueueBackendWrite(Socket& socket, const char* data, std::int64_t size,
                          std::int64_t limit) {
    return FitsWriteBudget(socket.bytesToWrite(), size, limit) &&
           socket.write(data, size) == size;
}
}
