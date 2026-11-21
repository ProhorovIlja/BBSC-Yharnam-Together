// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstddef>

// ServerRpcReceive() promises the count actually copied to the provided
// buffer. Reject a malformed adapter count before constructing a span of
// potentially out-of-bounds memory; -1 means no frame available.
namespace Libraries::Net::RpcLocal {
constexpr std::size_t ValidatedFrameLength(int copied, std::size_t capacity) {
    return copied > 0 && static_cast<std::size_t>(copied) <= capacity
        ? static_cast<std::size_t>(copied) : 0;
}
}
