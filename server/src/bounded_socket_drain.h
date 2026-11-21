// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <QByteArray>
#include <QIODevice>

namespace ShadNet {

// A fast peer can queue multiple 8 MiB protocol packets before readyRead.
// Never make another unbounded allocation with QTcpSocket::readAll(), and
// never retain a huge coalesced read while waiting for the packet header.
inline constexpr qint64 ClientReadChunkBytes = 16 * 1024;

template <class Accept, class Connected>
void DrainClientSocket(QIODevice& socket, Accept&& accept, Connected&& connected) {
    while (socket.bytesAvailable() > 0 && connected()) {
        QByteArray chunk = socket.read(ClientReadChunkBytes);
        if (chunk.isEmpty()) {
            break; // Qt will retry on the next readyRead after nonblocking EOF
        }
        accept(chunk);
        // A malformed packet may have disconnected the socket inside accept.
        // Do not process later queued packets from that same peer afterwards.
    }
}
} // namespace ShadNet
