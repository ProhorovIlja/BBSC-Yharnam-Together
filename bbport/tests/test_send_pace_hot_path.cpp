// SPDX-License-Identifier: GPL-2.0-or-later
// B89: lightweight Windows/Linux native executable using the EXACT production
// co-op SendPace header. No game, server or proprietary save file required.
#include <cassert>
#include <chrono>
#include <cstdio>

#include "core/bloodborne_send_pace.h"

using Core::Bloodborne::SendPace;
using Core::Bloodborne::EventSyncPerSecond;
using namespace std::chrono_literals;

static SendPace::Clock::time_point At(std::chrono::microseconds elapsed) {
    return SendPace::Clock::time_point{} + 1h + elapsed;
}

int main() {
    SendPace pace;
    for (u64 object = 1; object <= 600; ++object) {
        assert(pace.Allow(object, At(0us), 166ms));
    }
    assert(pace.Sweeps() == 1);
    for (int i = 0; i < 2000; ++i) {
        (void)pace.Allow(1, At(100ms), 166ms);
        (void)pace.AllowRate(0x1000000, At(100ms), EventSyncPerSecond);
    }
    assert(pace.Sweeps() == 1); // no O(N) full map scan for every send
    assert(pace.Size() == 601);
    assert(pace.Allow(1, At(350ms), 166ms));
    assert(pace.Sweeps() == 2);
    assert(pace.Size() == 601);
    assert(pace.Allow(0x123456789, At(10s), 166ms));
    assert(pace.Sweeps() == 3);
    assert(pace.Size() == 1);

    SendPace events;
    for (u64 event = 1; event <= 800; ++event) {
        assert(events.AllowRate(event, At(0us), EventSyncPerSecond));
    }
    assert(events.Sweeps() == 1);
    for (int i = 0; i < 120; ++i) {
        (void)events.AllowRate(1, At(100ms), EventSyncPerSecond);
    }
    assert(events.Sweeps() == 1);
    assert(events.AllowRate(900, At(7s), EventSyncPerSecond));
    assert(events.Size() == 1);

    // Preserve fair player-state intervals and event pacing.
    SendPace session;
    assert(session.Allow(0x123, At(0us), 166ms));
    assert(!session.Allow(0x123, At(41ms), 166ms));
    assert(session.Allow(0x123, At(166ms), 166ms));
    std::puts("B89_PRODUCTION_SEND_PACE_AMORTIZED_SWEEP_PASS");
}
