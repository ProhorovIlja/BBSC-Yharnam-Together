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
}
