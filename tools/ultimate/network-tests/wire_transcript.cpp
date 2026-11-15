// SPDX-License-Identifier: GPL-2.0-or-later
// Deterministic loss/duplicate/reorder transcript captured against the pre-change header.
#include "coop/game_link.h"
#include <iostream>
#include <vector>
using namespace BloodborneCoop;
struct Transit { GameFrame frame; s64 due; bool to_guest; };
int main() {
    u64 hash = 14695981039346656037ull;
    auto mix = [&](const auto& bytes) { for (u8 b : bytes) { hash ^= b; hash *= 1099511628211ull; } };
    u32 random = 0x73577;
    auto next = [&]() { random = random * 1664525u + 1013904223u; return random; };
    for (unsigned trial = 0; trial < 3; ++trial) {
        GameLinkPeer::Settings settings;
        settings.resend_ms = trial == 0 ? 0 : 15;
        settings.keepalive_ms = 25;
        settings.quiet_ms = 500;
        GameLinkPeer host{"host", 1, settings}, guest{"guest", 2, settings};
        std::vector<Transit> pending;
        for (s64 tick = 0; tick < 1000; ++tick) {
            const s64 now = tick * 5;
            if (tick < 400) {
                for (auto* peer : {&host, &guest}) {
                    for (unsigned n = 0, count = next() % 5; n < count; ++n) {
                        std::vector<u8> packet;
                        GameLinkDetail::Put(packet, next() % 8);
                        GameLinkDetail::Put(packet, u32{1});
                        packet.push_back(static_cast<u8>(next()));
                        peer->Send(next() % 3 ? PacketClass::Reliable : PacketClass::Unreliable, packet, now);
                    }
                }
            }
            for (bool to_guest : {true, false}) {
                auto frames = (to_guest ? host : guest).Flush(now);
                for (const auto& frame : frames) {
                    mix(EncodeGameFrame(frame)); // Includes every outgoing frame, even if lost.
                    if (tick < 400 && next() % 5 == 0) continue;
                    pending.push_back({frame, now + s64(next() % 20), to_guest});
                    if (tick < 400 && next() % 7 == 0) pending.push_back(pending.back());
                }
            }
            // Reverse arrival order within the current queue; delayed frames remain queued.
            for (size_t i = pending.size(); i > 0; --i) {
                auto& item = pending[i - 1];
                if (item.due > now) continue;
                auto delivered = (item.to_guest ? guest : host).Receive(item.frame, now);
                for (const auto& packet : delivered) mix(packet);
                pending.erase(pending.begin() + static_cast<std::ptrdiff_t>(i - 1));
            }
        }
        // A final keepalive may still be in flight at this fixed cutoff.
        if (host.Unacked() || guest.Unacked()) return 2;
    }
    std::cout << "Wire transcript FNV1a64: " << hash << '\n';
    return hash == 9003454785029844084ull ? 0 : 3;
}
