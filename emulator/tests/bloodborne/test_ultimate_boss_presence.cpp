// SPDX-License-Identifier: GPL-2.0-or-later
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <span>
#include <string_view>

#include "core/ultimate_boss_presence.h"

using namespace Core::Bloodborne::BossPresence;

using Gauges = std::array<std::uint8_t, GaugeBytes>;

static Gauges Empty() {
    Gauges g{};
    for (std::size_t i = 0; i < GaugeSlots; ++i) {
        const std::int32_t inactive = -1;
        std::memcpy(g.data() + i * GaugeSize, &inactive, sizeof(inactive));
        std::memcpy(g.data() + i * GaugeSize + 4, &inactive, sizeof(inactive));
    }
    return g;
}

static void Set(Gauges& g, std::size_t slot, std::int32_t name_id,
                std::int32_t handle, std::uint8_t shown = 1) {
    assert(slot < GaugeSlots);
    auto* start = g.data() + slot * GaugeSize;
    std::memcpy(start, &name_id, sizeof(name_id));
    std::memcpy(start + 4, &handle, sizeof(handle));
    start[0x10] = shown;
}

int main() {
    static_assert(GaugeSlots == 3 && GaugeSize == 0x14);
    static_assert(NamedBossIds.size() == 87);
    static_assert(BossNameForId(500000) == "Cleric Beast");
    static_assert(BossNameForId(451000) == "Ludwig the Accursed");
    static_assert(BossNameForId(451005) == "Ludwig, the Holy Blade");
    static_assert(BossNameForId(452000) == "Lady Maria of the Astral Clocktower");
    static_assert(BossNameForId(453000) == "Orphan of Kos");
    static_assert(BossNameForId(306001) == "Yharnam, Pthumerian Queen");
    static_assert(BossNameForId(1234567).empty());
    for (std::size_t i = 0; i < NamedBossIds.size(); ++i) {
        assert(!NamedBossIds[i].second.empty());
        for (std::size_t j = 0; j < i; ++j) {
            assert(NamedBossIds[i].first != NamedBossIds[j].first);
        }
    }

    Gauges g = Empty();
    assert(!NameFromActiveGauges(g));
    Set(g, 0, 500000, 123);
    assert(NameFromActiveGauges(g) == std::string_view{"Cleric Beast"});
    Set(g, 1, 500000, 456);  // two bars for one named boss
    assert(NameFromActiveGauges(g) == std::string_view{"Cleric Beast"});

    g = Empty();
    Set(g, 0, 212010, 111);
    Set(g, 1, 212020, 112);
    Set(g, 2, 212030, 113);
    assert(NameFromActiveGauges(g) == std::string_view{"Shadow of Yharnam"});
    g = Empty();
    Set(g, 0, 451000, 111);
    Set(g, 1, 451005, 112);  // two different labels: do not guess
    assert(!NameFromActiveGauges(g));

    g = Empty();
    Set(g, 0, 500000, 111, 0); // handle assigned, bar not yet shown
    assert(!NameFromActiveGauges(g));
    g = Empty();
    Set(g, 0, 999999, 111); // unknown ID
    assert(!NameFromActiveGauges(g));
    g = Empty();
    Set(g, 0, 500000, 111);
    Set(g, 1, 999999, 222); // unknown active boss is not ignored
    assert(!NameFromActiveGauges(g));
    g = Empty();
    Set(g, 0, 500000, -1); // no active bar even if text remnants exist
    assert(!NameFromActiveGauges(g));
    assert(!NameFromActiveGauges(std::span<const std::uint8_t>{}));
    assert(!NameFromActiveGauges(
        std::span<const std::uint8_t>(g.data(), GaugeBytes - 1)));

    EncounterClock clock;
    assert(clock.StartedUnix() == 0);
    clock.Observe(false, 0x24100000u, 100);
    assert(clock.StartedUnix() == 0);
    clock.Observe(true, 0, 100);
    assert(clock.StartedUnix() == 0); // map not known
    clock.Observe(true, 0x24100000u, 100);
    assert(clock.StartedUnix() == 100);
    clock.Observe(true, 0x24100000u, 200);
    assert(clock.StartedUnix() == 100); // phase/name changes keep timer
    clock.Observe(true, 0x34000000u, 300);
    assert(clock.StartedUnix() == 300); // new map
    clock.Observe(false, 0x34000000u, 400);
    assert(clock.StartedUnix() == 0);
    clock.Observe(true, 0x34000000u, 500);
    assert(clock.StartedUnix() == 500); // rematch after clear
    clock.Observe(true, 0x34000000u, -1);
    assert(clock.StartedUnix() == 0);
    clock.Reset();
    assert(clock.StartedUnix() == 0);

    std::puts("ultimate boss names / encounter clock: ok");
}
