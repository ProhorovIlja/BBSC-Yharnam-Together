// SPDX-License-Identifier: GPL-2.0-or-later
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include "core/libraries/network/http_timeouts.h"
using namespace Libraries::Http;
using namespace std::chrono_literals;
struct Client {
    std::chrono::seconds connect{}, receive{}, send{};
    unsigned calls = 0;
    void set_connection_timeout(std::chrono::seconds s) { connect=s; ++calls; }
    void set_read_timeout(std::chrono::seconds s) { receive=s; ++calls; }
    void set_write_timeout(std::chrono::seconds s) { send=s; ++calls; }
};
static void Check(bool ok, int line) {
    if (!ok) { std::fprintf(stderr,"HTTP timeout policy failed at %d\n",line); std::exit(1); }
}
#define CHECK(ok) Check((ok),__LINE__)
int main() {
    struct Case { std::uint32_t us; std::chrono::seconds plain, tls; };
    constexpr std::array<Case,12> cases{{
        {0,30s,30s},{1,1s,10s},{999999,1s,10s},{1000000,1s,10s},
        {1000001,2s,10s},{9000000,9s,10s},{9999999,10s,10s},{10000000,10s,10s},
        {10000001,11s,11s},{30000000,30s,30s},{50000000,50s,50s},
        {0xffffffffu,4295s,4295s}}};
    Client client; unsigned applied=0;
    for (const auto& c : cases) for (bool tls : {false,true}) {
        const auto b=Timeouts::Configure(client,c.us,1000001,0xffffffffu,tls);
        CHECK(b.connect==(tls ? c.tls : c.plain));
        CHECK(b.receive==2s && b.send==4295s);
        CHECK(client.connect==b.connect && client.receive==b.receive && client.send==b.send);
        CHECK(client.calls==3*++applied);
    }
    // A pooled client must be reconfigured, including a redirect from HTTPS to plain HTTP.
    Timeouts::Configure(client,1000000,0,0,true); CHECK(client.connect==10s);
    Timeouts::Configure(client,1000000,0,0,false); CHECK(client.connect==1s);
    CHECK(client.receive==120s && client.send==120s);
    static_assert(Timeouts::ForRequest(1,1,1,true).connect==10s);
    static_assert(Timeouts::ForRequest(1,1,1,true).receive==1s);
    static_assert(Timeouts::ForRequest(1,1,1,true).send==1s);
    std::puts("HTTP policy: 24 budget cases and pooled scheme reconfiguration passed");
}
