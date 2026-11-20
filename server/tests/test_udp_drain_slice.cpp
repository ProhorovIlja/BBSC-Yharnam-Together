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
    CHECK(DrainSlice(pending, consume, never));
    CHECK(seen == 128 && remaining == 172);
    ++ticks; // Stand-in for a timer/admin callback between two receive slices.
    CHECK(DrainSlice(pending, consume, never));
    CHECK(seen == 256 && ticks == 1);
    CHECK(!DrainSlice(pending, consume, never));
    CHECK(seen == 300 && remaining == 0);
    CHECK(!DrainSlice(pending, consume, never));
    remaining = 100;
    CHECK(DrainSlice(pending, consume, [] { return true; }));
    CHECK(remaining == 84);
    unsigned failures = 0;
    CHECK(!DrainSlice(pending, [&] { ++failures; return false; }, never));
    CHECK(failures == 1 && remaining == 84);
    remaining = 16;
    CHECK(!DrainSlice(pending, consume, [] { return true; }));
    CHECK(remaining == 0);
    std::cout << "UDP drain slice tests passed\n";
}
