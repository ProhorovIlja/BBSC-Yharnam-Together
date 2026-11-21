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
} // namespace ShadNetRpc
