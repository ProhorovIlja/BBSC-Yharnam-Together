// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#ifndef _WIN32
#include <sys/socket.h>
#endif

namespace Libraries::Net::RpcLocal {
// Per-send suppression is safer than process-wide SIGPIPE ignoring. On macOS
// SO_NOSIGPIPE must additionally be configured on the accepted socket.
constexpr int SafeSendFlags() noexcept {
#ifdef MSG_NOSIGNAL
    return MSG_NOSIGNAL;
#else
    return 0;
#endif
}
} // namespace Libraries::Net::RpcLocal
