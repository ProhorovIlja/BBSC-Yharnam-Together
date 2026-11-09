// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
#include <cassert>
#include <iostream>
#include <string>
#include <vector>
#include "coop/chat_policy.h"

using namespace BloodborneCoop::Comms;

int main() {
    std::vector<Peer> peers{
        Peer{.id="a", .team="hunt-a", .blocked={}},
        Peer{.id="b", .team="hunt-a", .blocked={}},
        Peer{.id="c", .team="hunt-b", .blocked={}},
        Peer{.id="d", .team="hunt-b", .blocked={}},
        Peer{.id="e", .team="", .blocked={}},
    };
    const auto send = [&](Gate& gate, Scope scope, std::string msg, std::string to = "",
                          std::int64_t at = 100, bool global = true) {
        return gate.Route("a", Request{scope, std::move(msg), std::move(to)},
                          std::span<const Peer>(peers), at, global);
    };
    {
        Gate gate;
        auto team = send(gate, Scope::Team, "Hello, Yharnam");
        assert(team.allowed() && team.recipients == std::vector<std::string>{"b"});
        auto world = send(gate, Scope::Global, "Global");
        assert(world.allowed() && world.recipients.size() == 4);
        auto dm = send(gate, Scope::Direct, "Whisper", "c");
        assert(dm.allowed() && dm.recipients == std::vector<std::string>{"c"});
        assert(send(gate, Scope::Direct, "secret", "unknown").status == Status::Unavailable);
        assert(send(gate, Scope::Direct, "secret", "a").status == Status::Unavailable);
    }
    {
        Gate gate;
        assert(send(gate, Scope::Global, "No cross-profile global", "", 100, false).status ==
               Status::Unavailable);
        peers[1].team = "hunt-b"; // live membership changed: old audience must be revoked
        assert(send(gate, Scope::Team, "team churn").recipients.empty());
        peers[1].team = "hunt-a";
        peers[1].blocked.insert("a");
        assert(send(gate, Scope::Team, "blocked").recipients.empty());
        assert(send(gate, Scope::Direct, "blocked", "b").status == Status::Unavailable);
        peers[1].blocked.clear();
        peers[1].receive_direct = false;
        assert(send(gate, Scope::Direct, "opt out", "b").status == Status::Unavailable);
        peers[1].receive_direct = true;
        peers[1].online = false;
        assert(send(gate, Scope::Direct, "gone", "b").status == Status::Unavailable);
        peers[1].online = true;
    }
    {
        Gate gate;
        peers[0].team = "";
        assert(send(gate, Scope::Team, "not in team").status == Status::NoTeam);
        peers[0].team = "hunt-a";
        peers[0].can_send = false;
        assert(send(gate, Scope::Global, "muted").status == Status::Disabled);
        peers[0].can_send = true;
        peers[0].online = false;
        assert(send(gate, Scope::Global, "offline").status == Status::UnknownSender);
        peers[0].online = true;
        assert(gate.Route("spoofed", Request{Scope::Global, "message", ""},
                          std::span<const Peer>(peers), 100, true).status ==
               Status::UnknownSender);
    }
    {
        Gate gate;
        assert(ValidText("Привет, охотники! 🎮"));
        assert(ValidText("<b>just text</b>"));
        assert(!ValidText(""));
        assert(!ValidText("     "));
        assert(!ValidText(std::string(513, 'x')));
        assert(!ValidText(std::string(241, 'x')));
        assert(!ValidText("line\nspoof"));
        assert(!ValidText(std::string("\xc0\xaf", 2))); // overlong slash
        assert(!ValidText(std::string("\xed\xa0\x80", 3))); // surrogate
        assert(!ValidText(std::string("\xf4\x90\x80\x80", 4))); // too large
        assert(!ValidText(std::string("\xe2\x80\xae", 3))); // bidi override
        assert(!ValidText(std::string("\xe2\x81\xa6", 3))); // bidi isolate
        assert(send(gate, Scope::Global, "line\nbreak").status == Status::InvalidText);
        assert(send(gate, Scope::Global, "Привет").allowed());
    }
    {
        Gate gate;
        for (int i = 0; i < 6; ++i) {
            assert(send(gate, i % 2 ? Scope::Global : Scope::Team, "burst", "", 100 + i).allowed());
        }
        assert(send(gate, Scope::Team, "7th", "", 107).status == Status::RateLimited);
        assert(send(gate, Scope::Team, "rollback", "", 99).status == Status::Unavailable);
        assert(send(gate, Scope::Team, "next window", "", 10100).allowed());
        // clearing is an administrative operation, not a client-controlled reconnect request
        gate.Clear("a");
        assert(send(gate, Scope::Team, "post-admin-reset", "", 10101).allowed());
    }
    {
        Gate gate;
        // Inputs from a different server MUST NOT be placed in the current server's roster.
        peers.push_back(Peer{.id="z", .team="another-server", .blocked={}}); // synthetic current-shard member
        assert(send(gate, Scope::Team, "isolated").recipients ==
               std::vector<std::string>{"b"});
        // A duplicated roster entry cannot duplicate a delivery.
        peers.push_back(peers[1]);
        assert(send(gate, Scope::Global, "one per account").recipients.size() == 5);
    }
    std::cout << "chat_policy: membership, blocks, opt-out, UTF-8, flood and scope PASS\n";
}
