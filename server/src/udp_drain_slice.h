// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

namespace ShadNetUdp {
struct DrainResult {
    bool more = false;
    bool read_failed = false;
    bool progressed = false;

    // A transient read error may leave already-queued datagrams without
    // another readyRead. Retry once, unless this slice made fresh progress.
    [[nodiscard]] bool retry_read(bool already_retried) const {
        return more && read_failed && (!already_retried || progressed);
    }
    [[nodiscard]] bool budget_yield() const { return more && !read_failed; }
};

// Budget
// checks are amortized, and never interrupt handling of a single datagram.
template <class Pending, class Consume, class OverTime>
DrainResult DrainSlice(Pending pending, Consume consume, OverTime over_time) {
    DrainResult result;
    for (unsigned n = 0; n < 128; ++n) {
        if (!pending())
            return result;
        if (!consume()) {
            result.read_failed = true;
            result.more = pending();
            return result;
        }
        result.progressed = true;
        if ((n + 1) % 16 == 0 && over_time())
            break;
    }
    result.more = pending();
    return result;
}
} // namespace ShadNetUdp
