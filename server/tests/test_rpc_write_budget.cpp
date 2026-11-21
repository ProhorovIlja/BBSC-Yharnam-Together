// SPDX-License-Identifier: GPL-2.0-or-later
#include "src/rpc_write_budget.h"
#include <cstdint>
#include <iostream>
#include <limits>

using ShadNetRpc::FitsWriteBudget;
static_assert(FitsWriteBudget(0, 0, 16));
static_assert(FitsWriteBudget(15, 1, 16));
static_assert(!FitsWriteBudget(15, 2, 16));
static_assert(!FitsWriteBudget(-1, 1, 16));
static_assert(!FitsWriteBudget(0, -1, 16));
static_assert(!FitsWriteBudget(std::numeric_limits<std::int64_t>::max(),
                               std::numeric_limits<std::int64_t>::max(),
                               std::numeric_limits<std::int64_t>::max()));

using ShadNetRpc::FitsTunnelReadBudget;
static_assert(FitsTunnelReadBudget(0, 1, 5));
static_assert(!FitsTunnelReadBudget(0, 1, 4));
static_assert(FitsTunnelReadBudget(0, 999, 1003)); // one 1,000-byte fragment
static_assert(!FitsTunnelReadBudget(0, 999, 1002));
static_assert(FitsTunnelReadBudget(0, 1000, 1005)); // two fragments
static_assert(!FitsTunnelReadBudget(0, 1000, 1004));
static_assert(FitsTunnelReadBudget(0, 16 * 1024, 16404));
static_assert(!FitsTunnelReadBudget(0, 16 * 1024, 16403));
static_assert(!FitsTunnelReadBudget(0, 0, 100));
static_assert(!FitsTunnelReadBudget(0, 16 * 1024 + 1, 1 << 20));
static_assert(!FitsTunnelReadBudget(20, 1, 10));
static_assert(!FitsTunnelReadBudget(std::numeric_limits<std::size_t>::max() - 2, 1,
                                   std::numeric_limits<std::size_t>::max()));

struct FakeSocket {
    std::int64_t queued = 0;
    std::int64_t bytesToWrite() const { return queued; }
    std::int64_t write(const char*, std::int64_t size) {
        queued += size;
        return size;
    }
};
int main() {
    FakeSocket socket{};
    if (!ShadNetRpc::TryQueueBackendWrite(socket, "abc", 3, 4) ||
        ShadNetRpc::TryQueueBackendWrite(socket, "xx", 2, 4) ||
        socket.queued != 3 ||
        !ShadNetRpc::TryQueueBackendWrite(socket, "d", 1, 4) ||
        socket.queued != 4)
        return 1;
    // A backend that sends continuously while the remote game never ACKs
    // cannot grow the reliable queue past the configured memory ceiling.
    constexpr std::size_t cap = 9u << 20;
    constexpr std::size_t chunk = ShadNetRpc::MaxTunnelReadSlice;
    constexpr std::size_t fragments = (chunk + 1000) / 1000;
    std::size_t queued = 0;
    std::size_t accepted = 0;
    while (FitsTunnelReadBudget(queued, chunk, cap)) {
        queued += chunk + 1 + fragments;
        ++accepted;
    }
    if (!accepted || queued > cap - 2 ||
        FitsTunnelReadBudget(queued, chunk, cap) ||
        !FitsTunnelReadBudget(0, chunk, cap))
        return 2;
    std::cout << "RPC backend write and bounded reply read budgets passed\n";
}
