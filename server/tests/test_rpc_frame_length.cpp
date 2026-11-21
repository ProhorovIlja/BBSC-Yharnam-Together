// SPDX-License-Identifier: GPL-2.0-or-later
#include "core/libraries/network/rpc_frame_length.h"
#include <cassert>
#include <cstdint>
#include <limits>
#include <iostream>

using Libraries::Net::RpcLocal::ValidatedFrameLength;
static_assert(ValidatedFrameLength(-1, 16384) == 0);
static_assert(ValidatedFrameLength(0, 16384) == 0);
static_assert(ValidatedFrameLength(1, 16384) == 1);
static_assert(ValidatedFrameLength(16384, 16384) == 16384);
static_assert(ValidatedFrameLength(16385, 16384) == 0);
static_assert(ValidatedFrameLength(std::numeric_limits<int>::max(), 16384) == 0);
static_assert(ValidatedFrameLength(1, 0) == 0);
int main() {
    if (ValidatedFrameLength(999999, 16) != 0 ||
        ValidatedFrameLength(8, 16) != 8)
        return 1;
    std::cout << "RPC read span size contract holds\n";
}
