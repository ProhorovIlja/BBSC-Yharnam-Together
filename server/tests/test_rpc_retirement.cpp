// SPDX-License-Identifier: GPL-2.0-or-later
#include "../src/rpc_retirement.h"
#include <cassert>
#include <map>
#include <memory>
#include <vector>

struct Endpoint {
    int id;
    bool operator==(const Endpoint&) const = default;
};
struct End {
    Endpoint to;
    bool open = true;
};
int main() {
    std::map<int, std::unique_ptr<End>> ends;
    ends.emplace(1, std::make_unique<End>(End{Endpoint{10}}));
    ends.emplace(2, std::make_unique<End>(End{Endpoint{20}}));
    ends.emplace(3, std::make_unique<End>(End{Endpoint{10}}));
    std::vector<int> closed;
    const auto count = ShadNetRpc::RetireByEndpoint(ends, Endpoint{10}, [&](End& end) {
        assert(end.to.id == 10 && end.open);
        end.open = false;
        closed.push_back(end.to.id);
    });
    assert(count == 2 && closed == std::vector<int>({10, 10}));
    assert(ends.size() == 1 && ends.count(2) == 1 && ends.at(2)->open);
    assert(ShadNetRpc::RetireByEndpoint(ends, Endpoint{10},
                                     [](End&) { assert(false); }) == 0);
    assert(ShadNetRpc::RetireByEndpoint(ends, Endpoint{20}, [&](End& end) {
        assert(end.open);
        end.open = false;
    }) == 1);
    assert(ends.empty());

    // An unchanged endpoint keeps the active tunnel. An authenticated new
    // endpoint first aborts the former one and then gets a fresh slot.
    auto active = std::make_unique<End>(End{Endpoint{30}});
    int aborts = 0;
    auto abort = [&](End& end) {
        assert(active && end.open);
        ++aborts;
        end.open = false;
    };
    assert(!ShadNetRpc::RetireIfEndpointChanged(active, Endpoint{30}, abort));
    assert(active && active->open && aborts == 0);
    assert(ShadNetRpc::RetireIfEndpointChanged(active, Endpoint{31}, abort));
    assert(!active && aborts == 1);
    assert(!ShadNetRpc::RetireIfEndpointChanged(active, Endpoint{31}, abort));
    assert(aborts == 1);
    active = std::make_unique<End>(End{Endpoint{31}});
    assert(active && active->open);
}

