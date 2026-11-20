// SPDX-License-Identifier: GPL-2.0-or-later
#include "../src/link_loop_timing.h"

int main() {
    ShadNetUdp::TickTiming world{50}, link{500};
    world.Start(100);
    link.Start(100);
    world.Observe(150);
    world.Observe(250);
    world.Observe(351);
    world.Observe(399);
    link.Observe(600);
    link.Observe(1650);
    return !(world.ticks == 4 && world.max_gap_ms == 101 && world.gaps_over_2x == 1 &&
             link.ticks == 2 && link.max_gap_ms == 1050 && link.gaps_over_2x == 1);
}
