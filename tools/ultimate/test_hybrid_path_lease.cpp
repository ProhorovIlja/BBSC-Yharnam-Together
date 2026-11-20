// SPDX-License-Identifier: GPL-2.0-or-later
#include "hybrid_path_lease.h"
#include <cstdlib>
#include <iostream>
#include <limits>

#define CHECK(value) do { ++checks; if (!(value)) { std::cerr << "failed line " << __LINE__ << '\n'; std::abort(); } } while (false)

int main() {
    using namespace ultimate;
    unsigned checks = 0;
    PathBinding a{1, 2, 3, 4, 5, {6}}, b = a;
    ProbeNonce nonce{7}, other{8};
    HybridPathLease p;
    CHECK(!p.bind({}, 0));
    CHECK(p.bind(a, 1));
    CHECK(!p.challenge(a, 1, nonce, 2)); // Relay-only until opt-in.
    p.allow_direct(true);
    CHECK(!p.challenge(a, 1, {}, 3));
    CHECK(p.challenge(a, 1, nonce, 4));
    CHECK(!p.acknowledge(a, 1, other, 5));
    b.peer_connection++;
    CHECK(!p.acknowledge(b, 1, nonce, 6));
    CHECK(p.acknowledge(a, 1, nonce, 7));
    CHECK(p.route(Traffic::PoseSnapshot, true, true, 8) == Route::Direct);
    for (auto traffic : {Traffic::Membership, Traffic::WorldCommit, Traffic::BossResult,
                         Traffic::Reward, Traffic::TravelCommit, Traffic::InvasionAdmission}) {
        CHECK(p.route(traffic, true, true, 8) == Route::Authority);
        CHECK(p.route(traffic, false, true, 8) == Route::Unavailable);
        CHECK(!p.accept_visual(a, traffic, 1, Route::Direct, true, 8));
    }
    CHECK(p.route(Traffic::Unknown, true, true, 8) == Route::Unavailable);
    CHECK(p.accept_visual(a, Traffic::PoseSnapshot, 10, Route::Direct, true, 9));
    CHECK(!p.accept_visual(a, Traffic::PoseSnapshot, 10, Route::Relay, true, 10));
    CHECK(p.accept_visual(a, Traffic::VisualEmote, 0, Route::Relay, true, 11));
    CHECK(!p.accept_visual(a, Traffic::VisualEmote, 0, Route::Relay, true, 12));
    CHECK(!p.accept_visual(b, Traffic::PoseSnapshot, 11, Route::Relay, true, 13));
    CHECK(!p.acknowledge(a, 1, nonce, 2006)); // Cannot extend by replay.
    CHECK(p.route(Traffic::PoseSnapshot, true, true, 2006) == Route::Direct);
    CHECK(p.route(Traffic::PoseSnapshot, true, true, 2007) == Route::Relay);
    CHECK(!p.accept_visual(a, Traffic::PoseSnapshot, 11, Route::Direct, true, 2008));
    CHECK(p.accept_visual(a, Traffic::PoseSnapshot, 11, Route::Relay, true, 2009));
    CHECK(!p.challenge(a, 1, nonce, 2010));
    CHECK(p.challenge(a, 2, other, 2011));
    CHECK(!p.acknowledge(a, 2, other, 3011)); // Deadline is exclusive.
    CHECK(p.route(Traffic::PoseSnapshot, true, false, 3012) == Route::Unavailable);
    CHECK(p.challenge(a, 3, nonce, 3013));
    p.allow_direct(false); // Revokes pending probe as well as current proof.
    p.allow_direct(true);
    CHECK(!p.acknowledge(a, 3, nonce, 3014));
    CHECK(p.challenge(a, 4, other, 3015));
    CHECK(p.acknowledge(a, 4, other, 3016));
    b = a; b.endpoint[0]++;
    CHECK(p.bind(b, 3017)); // NAT rebind requires a new proof.
    CHECK(p.route(Traffic::PoseSnapshot, true, true, 3018) == Route::Relay);
    CHECK(!p.challenge(a, 5, nonce, 3019));
    CHECK(!p.accept_visual(b, Traffic::PoseSnapshot, 11, Route::Relay, true, 3020));
    CHECK(p.accept_visual(b, Traffic::PoseSnapshot, 12, Route::Relay, true, 3021));
    CHECK(p.challenge(b, 5, nonce, 3022));
    p.disconnect();
    CHECK(p.bind(a, 3023));
    CHECK(!p.acknowledge(b, 5, nonce, 3024));
    CHECK(!p.challenge(a, 5, nonce, 3025));
    CHECK(!p.challenge(a, 6, nonce, 3025));
    p.allow_direct(true);
    CHECK(p.challenge(a, 6, nonce, 3026));
    CHECK(p.acknowledge(a, 6, nonce, 3027));
    CHECK(p.route(Traffic::PoseSnapshot, true, true, 3026) == Route::Relay); // Regression.
    CHECK(!p.challenge(a, 7, nonce, 3028)); // Fault stays closed.
    CHECK(!p.bind(a, 3029));

    HybridPathLease high;
    const auto max = std::numeric_limits<std::uint64_t>::max();
    CHECK(high.bind(a, max - 10));
    high.allow_direct(true);
    CHECK(high.challenge(a, 1, nonce, max - 9));
    CHECK(high.acknowledge(a, 1, nonce, max - 8));
    CHECK(high.route(Traffic::PoseSnapshot, true, true, max) == Route::Direct);
    CHECK(high.accept_visual(a, Traffic::PoseSnapshot, 0xffffffffU, Route::Relay, true, max));
    CHECK(!high.accept_visual(a, Traffic::PoseSnapshot, 0, Route::Relay, true, max));
    b = a; b.epoch++;
    CHECK(high.bind(b, max));
    CHECK(high.accept_visual(b, Traffic::PoseSnapshot, 0, Route::Relay, true, max));
    CHECK(!high.accept_visual(a, Traffic::PoseSnapshot, 1, Route::Relay, true, max));

    // Invalid binds and transport disconnects cannot erase a still-current
    // authenticated stream's history or carry permission into a different peer.
    HybridPathLease reconnect;
    CHECK(reconnect.bind(a, 1));
    reconnect.allow_direct(true);
    CHECK(reconnect.accept_visual(a, Traffic::PoseSnapshot, 50, Route::Relay, true, 2));
    CHECK(!reconnect.bind({}, 3));
    CHECK(reconnect.bind(a, 4));
    CHECK(!reconnect.accept_visual(a, Traffic::PoseSnapshot, 50, Route::Relay, true, 5));
    CHECK(!reconnect.challenge(a, 1, nonce, 6));
    reconnect.allow_direct(true);
    CHECK(reconnect.challenge(a, 1, nonce, 7));
    reconnect.disconnect();
    CHECK(reconnect.bind(a, 8));
    CHECK(!reconnect.accept_visual(a, Traffic::PoseSnapshot, 49, Route::Relay, true, 9));
    CHECK(!reconnect.challenge(a, 2, nonce, 10));
    CHECK(reconnect.accept_visual(a, Traffic::PoseSnapshot, 51, Route::Relay, true, 11));
    reconnect.allow_direct(true);
    b = a; ++b.peer_connection;
    CHECK(reconnect.bind(b, 12));
    CHECK(!reconnect.challenge(b, 2, nonce, 13));
    CHECK(reconnect.accept_visual(b, Traffic::PoseSnapshot, 0, Route::Relay, true, 14));
    reconnect.allow_direct(true);
    CHECK(reconnect.challenge(b, 2, nonce, 15));
    CHECK(reconnect.acknowledge(b, 2, nonce, 16));
    CHECK(reconnect.route(Traffic::PoseSnapshot, true, true, 17) == Route::Direct);
    HybridPathLease failover;
    CHECK(failover.bind(a, 1));
    failover.allow_direct(true);
    CHECK(failover.challenge(a, 1, nonce, 2));
    CHECK(failover.bind(a, 3)); // A duplicate notification does not cancel the pending ACK.
    CHECK(failover.acknowledge(a, 1, nonce, 4));
    CHECK(failover.bind(a, 5));
    CHECK(failover.route(Traffic::PoseSnapshot, true, true, 6) == Route::Direct);
    CHECK(failover.accept_visual(a, Traffic::PoseSnapshot, 10, Route::Direct, true, 7));
    CHECK(failover.challenge(a, 2, other, 8));
    b = a; ++b.endpoint[0];
    CHECK(!failover.direct_failed(b, 9));
    CHECK(failover.route(Traffic::PoseSnapshot, true, true, 10) == Route::Direct);
    CHECK(failover.direct_failed(a, 11));
    CHECK(failover.route(Traffic::PoseSnapshot, true, true, 11) == Route::Relay);
    CHECK(failover.route(Traffic::PoseSnapshot, true, false, 11) == Route::Unavailable);
    CHECK(failover.route(Traffic::Reward, true, true, 11) == Route::Authority);
    CHECK(!failover.acknowledge(a, 2, other, 12));
    CHECK(!failover.accept_visual(a, Traffic::PoseSnapshot, 11, Route::Direct, true, 13));
    CHECK(!failover.accept_visual(a, Traffic::PoseSnapshot, 10, Route::Relay, true, 14));
    CHECK(failover.accept_visual(a, Traffic::PoseSnapshot, 11, Route::Relay, true, 15));
    CHECK(failover.challenge(a, 3, nonce, 16));
    CHECK(failover.acknowledge(a, 3, nonce, 17));
    CHECK(!failover.accept_visual(a, Traffic::PoseSnapshot, 11, Route::Direct, true, 18));
    CHECK(failover.accept_visual(a, Traffic::PoseSnapshot, 12, Route::Direct, true, 19));

    std::cout << checks << " hybrid path checks passed\n";
}
