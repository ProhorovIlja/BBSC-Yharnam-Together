// SPDX-License-Identifier: GPL-2.0-or-later
#include "core/libraries/network/rpc_local_send.h"
#include <array>
#include <csignal>
#include <iostream>
#include <unistd.h>
#include <vector>

using namespace Libraries::Net::RpcLocal;

int main() {
    int sockets[2];
    if (std::signal(SIGPIPE, SIG_DFL) == SIG_ERR ||
        socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) != 0)
        return 1;
    const int small = 4096;
    if (setsockopt(sockets[0], SOL_SOCKET, SO_SNDBUF, &small, sizeof(small)) != 0 ||
        !ConfigureLocalSend(sockets[0]))
        return 2;
    const std::array<std::uint8_t, 4> payload{1, 0, 4, 9};
    std::array<std::uint8_t, 4> received{};
    if (!SendAll(sockets[0], payload) ||
        recv(sockets[1], received.data(), received.size(), MSG_WAITALL) != 4 ||
        received != payload)
        return 3;
    // Leave the peer open but do not read. The small send buffer fills.
    const auto started = NowMs();
    if (SendAll(sockets[0], std::vector<std::uint8_t>(1 << 20, 42)) ||
        NowMs() - started > 2000)
        return 4;
    close(sockets[0]);
    close(sockets[1]);
    // Use a fresh pair: the failure must be a closed peer, not a full buffer.
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) != 0 ||
        !ConfigureLocalSend(sockets[0]))
        return 5;
    close(sockets[1]);
    if (SendAll(sockets[0], payload))
        return 6;
    close(sockets[0]);
    std::cout << "RPC local writes: delivered bytes unchanged and escaped stalled reader\n";
}
