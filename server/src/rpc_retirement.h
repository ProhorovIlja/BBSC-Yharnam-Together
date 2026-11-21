// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstddef>
#include <utility>

// Retire owned RPC sessions before their old endpoint may sign in again.
// Close callback executes while the object still has its map-owned lifetime,
// and should detach/abort the TCP socket before the map erases the session.
namespace ShadNetRpc {
template <class RpcMap, class Endpoint, class Close>
std::size_t RetireByEndpoint(RpcMap& ends, const Endpoint& peer, Close&& close) {
    std::size_t retired = 0;
    for (auto it = ends.begin(); it != ends.end();) {
        if (it->second && it->second->to == peer) {
            close(*it->second);
            it = ends.erase(it);
            ++retired;
        } else {
            ++it;
        }
    }
    return retired;
}
// The online ID may sign in from a different endpoint before the old link's
// loss notification reaches this server. Do not carry its tunnel or backend
// write queue across this authenticated endpoint change.
template <class Slot, class Endpoint, class Close>
bool RetireIfEndpointChanged(Slot& slot, const Endpoint& peer, Close&& close) {
    if (!slot || slot->to == peer)
        return false;
    close(*slot);
    slot.reset();
    return true;
}
} // namespace ShadNetRpc
