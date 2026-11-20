// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <algorithm>
#include <cstdint>

namespace ShadNetUdp {
// Cumulative event-loop observations, not inferred counts of missed ticks.
// Measure callback start-to-start intervals on the same monotonic clock.
struct TickTiming {
    explicit TickTiming(std::int64_t period) : nominal_ms(period) {}
    void Start(std::int64_t now) { last_ms = now; }
    void Observe(std::int64_t now) {
        const auto gap = now - last_ms;
        last_ms = now;
        ++ticks;
        max_gap_ms = std::max(max_gap_ms, gap);
        gaps_over_2x += gap > nominal_ms * 2;
    }

    std::int64_t ticks = 0, max_gap_ms = 0, gaps_over_2x = 0;

private:
    const std::int64_t nominal_ms;
    std::int64_t last_ms = 0;
};
} // namespace ShadNetUdp
