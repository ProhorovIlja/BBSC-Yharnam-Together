// SPDX-License-Identifier: GPL-2.0-or-later
#include "../src/udp_drain_slice.h"
#include <cstdlib>
#include <iostream>

#define CHECK(x) do { if (!(x)) { std::cerr << "failure line " << __LINE__ << '\n'; std::abort(); } } while (false)

int main() {
    using ShadNetUdp::DrainSlice;
    unsigned remaining = 300, seen = 0, ticks = 0;
    auto pending = [&] { return remaining > 0; };
    auto consume = [&] { --remaining; ++seen; return true; };
    auto never = [] { return false; };
    CHECK(DrainSlice(pending, consume, never).budget_yield());
    CHECK(seen == 128 && remaining == 172);
    ++ticks; // Stand-in for a timer/admin callback between two receive slices.
    CHECK(DrainSlice(pending, consume, never).budget_yield());
    CHECK(seen == 256 && ticks == 1);
    CHECK(!DrainSlice(pending, consume, never).budget_yield());
    CHECK(seen == 300 && remaining == 0);
    CHECK(!DrainSlice(pending, consume, never).budget_yield());
    remaining = 100;
    CHECK(DrainSlice(pending, consume, [] { return true; }).budget_yield());
    CHECK(remaining == 84);
    unsigned failures = 0;
    const auto stalled = DrainSlice(pending, [&] { ++failures; return false; }, never);
    CHECK(failures == 1 && remaining == 84);
    CHECK(stalled.read_failed && !stalled.progressed && !stalled.budget_yield());
    CHECK(stalled.retry_read(false) && !stalled.retry_read(true));
    const auto progressed = DrainSlice(pending, [&] {
        if (remaining == 84) return consume();
        return false;
    }, never);
    CHECK(progressed.read_failed && progressed.progressed && progressed.retry_read(true));
    const auto emptied = DrainSlice(pending, [&] {
        remaining = 0;
        return false;
    }, never);
    CHECK(emptied.read_failed && !emptied.retry_read(false));
    remaining = 16;
    CHECK(!DrainSlice(pending, consume, [] { return true; }).budget_yield());
    CHECK(remaining == 0);
    std::cout << "UDP drain slice tests passed\n";
}
