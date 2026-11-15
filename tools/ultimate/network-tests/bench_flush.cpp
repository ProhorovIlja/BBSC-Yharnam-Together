// SPDX-License-Identifier: GPL-2.0-or-later
// Synthetic Flush CPU timing only, not game FPS/RTT or a CI performance gate.
#include "coop/game_link.h"
#include <algorithm>
#include <chrono>
#include <iostream>
#include <vector>
using namespace BloodborneCoop;
int main() {
    volatile size_t consumed = 0;
    for (size_t old : {size_t{0}, size_t{64}}) {
        for (size_t queued : {size_t{0}, size_t{64}, size_t{1000}, size_t{10000}}) {
            std::vector<long long> samples;
            for (unsigned repeat = 0; repeat < 100; ++repeat) {
                GameLinkPeer link{"fixture", 1};
                const std::vector<u8> packet(16, 1);
                for (size_t i = 0; i < old; ++i) link.Send(PacketClass::Reliable, packet, 0);
                link.Flush(0);
                for (size_t i = 0; i < queued; ++i) link.Send(PacketClass::Reliable, packet, 1);
                const auto start = std::chrono::steady_clock::now();
                const auto frames = link.Flush(151);
                const auto stop = std::chrono::steady_clock::now();
                consumed = frames.size();
                samples.push_back(std::chrono::duration_cast<std::chrono::nanoseconds>(stop - start).count());
            }
            std::sort(samples.begin(), samples.end());
            std::cout << old << ',' << queued << ',' << samples[50] << ',' << samples[95] << '\n';
        }
    }
    return consumed == size_t(-1);
}
