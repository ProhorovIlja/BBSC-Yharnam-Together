// SPDX-License-Identifier: GPL-2.0-or-later
// A send after peer shutdown must return EPIPE, not terminate the game with SIGPIPE.
#include "../../src/core/libraries/network/rpc_safe_send.h"
#include <cerrno>
#include <sys/socket.h>
#include <unistd.h>

int main() {
    int sockets[2] = {-1, -1};
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) != 0)
        return 1;
    close(sockets[1]);
    const char request = 'x';
    errno = 0;
    const ssize_t sent =
        send(sockets[0], &request, sizeof(request), Libraries::Net::RpcLocal::SafeSendFlags());
    const int error = errno;
    close(sockets[0]);
    return sent == -1 && error == EPIPE ? 0 : 2;
}
