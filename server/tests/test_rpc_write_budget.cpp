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
    std::cout << "RPC queued byte budget works at boundaries\n";
}
