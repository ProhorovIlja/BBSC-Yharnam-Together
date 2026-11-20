// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

namespace ShadNetUdp {
// Return true only if the caller should yield and then drain again. Budget
// checks are amortized, and never interrupt handling of a single datagram.
template <class Pending, class Consume, class OverTime>
bool DrainSlice(Pending pending, Consume consume, OverTime over_time) {
    for (unsigned n = 0; n < 128; ++n) {
        if (!pending() || !consume())
            return false;
        if ((n + 1) % 16 == 0 && over_time())
            break;
    }
    return pending();
}
} // namespace ShadNetUdp
