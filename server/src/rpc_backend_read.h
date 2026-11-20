// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <algorithm>
#include <array>
#include <QTcpSocket>
#include "coop/rpc_tunnel.h"

namespace ShadNetRpc {
enum class BackendRead { Pending, DrainedEof, Failed };

// Leave bytes in Qt's bounded buffer while the UDP peer owes ACKs. An EOF
// may arrive while bytes are still buffered; send those bytes before Close.
inline BackendRead PumpBackendReply(QTcpSocket& socket, BloodborneCoop::RpcTunnel& tunnel,
                                    BloodborneCoop::RpcReadPause& pause, bool eof,
                                    s64 now, size_t budget, size_t max_read) {
    std::array<u8, BloodborneCoop::RpcTunnel::MaxDataBytes> data;
    while (socket.bytesAvailable() > 0 && max_read != 0) {
        auto n = (std::min)({static_cast<size_t>(socket.bytesAvailable()),
                                  max_read, data.size()});
        if (!tunnel.CanWriteRequest(n, budget)) {
            // Payload cost is monotonic, including chunk markers. Use the
            // capacity ACKs freed even when it is less than one full read.
            size_t low = 0, high = n;
            while (low < high) {
                const size_t mid = low + (high - low + 1) / 2;
                if (tunnel.CanWriteRequest(mid, budget))
                    low = mid;
                else
                    high = mid - 1;
            }
            n = low;
            if (n == 0)
                return pause.Expired(now) ? BackendRead::Failed : BackendRead::Pending;
        }
        const auto read = socket.read(reinterpret_cast<char*>(data.data()), n);
        if (read <= 0)
            return BackendRead::Failed;
        pause.Reset();
        tunnel.Write(std::span{data}.first(static_cast<size_t>(read)), now);
        max_read -= static_cast<size_t>(read);
    }
    if (socket.bytesAvailable() == 0) {
        pause.Reset();
        if (eof)
            return BackendRead::DrainedEof;
    }
    return BackendRead::Pending;
}
}
