// SPDX-License-Identifier: GPL-2.0-or-later
#include "core/libraries/network/rpc_poll.h"
#include <fcntl.h>
#include <sys/select.h>
#include <unistd.h>
#include <iostream>

using Libraries::Net::RpcLocal::ReadableFd;

int main() {
    int descriptors[2]{};
    if (pipe(descriptors) != 0)
        return 1;
    const int high = fcntl(descriptors[0], F_DUPFD, FD_SETSIZE + 16);
    if (high < FD_SETSIZE)
        return 2;  // environment must expose high descriptors for this regression
    close(descriptors[0]);

    if (ReadableFd(-1, 0) || ReadableFd(high, -1) || ReadableFd(high, 0))
        return 3;
    const char value = 'h';
    if (write(descriptors[1], &value, 1) != 1 || !ReadableFd(high, 50))
        return 4;
    char received{};
    if (read(high, &received, 1) != 1 || received != value)
        return 5;
    close(descriptors[1]);
    // A closed peer must be observable even with no buffered data.
    if (!ReadableFd(high, 50))
        return 6;
    close(high);
    std::cout << "RPC POSIX poll accepts fd > FD_SETSIZE, read, timeout and HUP\n";
}
