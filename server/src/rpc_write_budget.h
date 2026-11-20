// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>

namespace ShadNetRpc {
// Both Qt's connected write queue and the preconnect queue are byte budgets.
constexpr bool FitsWriteBudget(std::int64_t queued, std::int64_t incoming,
                               std::int64_t limit) {
    return queued >= 0 && incoming >= 0 && queued <= limit &&
           incoming <= limit - queued;
}

template <typename Socket>
bool TryQueueBackendWrite(Socket& socket, const char* data, std::int64_t size,
                          std::int64_t limit) {
    return FitsWriteBudget(socket.bytesToWrite(), size, limit) &&
           socket.write(data, size) == size;
}
}
