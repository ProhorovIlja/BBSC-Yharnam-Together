// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#ifndef _WIN32
#include <poll.h>

namespace Libraries::Net::RpcLocal {

// POSIX FD_SET would write out of bounds when fd >= FD_SETSIZE.
// POLLHUP/POLLERR indicate the caller must attempt a read and retire the peer.
inline bool ReadableFd(int fd, int timeout_ms) {
    if (fd < 0 || timeout_ms < 0)
        return false;
    pollfd watched{fd, POLLIN, 0};
    return poll(&watched, 1, timeout_ms) > 0 &&
           (watched.revents & (POLLIN | POLLHUP | POLLERR)) != 0;
}

} // namespace Libraries::Net::RpcLocal
#endif
