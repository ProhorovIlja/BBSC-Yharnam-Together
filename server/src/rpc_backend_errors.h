// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <QMetaObject>
#include <QTcpSocket>
#include <QTimer>
#include <utility>

namespace ShadNetRpc {
inline bool MayBufferBackendRequest(QAbstractSocket::SocketState state) {
    return state == QAbstractSocket::HostLookupState ||
           state == QAbstractSocket::ConnectingState;
}

// Retired sockets get a chance to drain, but a backend that stops reading
// must not keep a detached socket and its write queue indefinitely.
inline void DrainAndCloseBackend(QTcpSocket& socket, int timeout_ms = 2000) {
    // A socket that has not connected cannot drain requests. Qt can defer a
    // disconnect while connecting; do not start an obsolete backend session.
    if (MayBufferBackendRequest(socket.state())) {
        socket.abort();
        return;
    }
    socket.disconnectFromHost();
    if (socket.state() == QAbstractSocket::ClosingState) {
        QTimer::singleShot(timeout_ms, &socket, [socket = &socket] {
            if (socket->state() == QAbstractSocket::ClosingState)
                socket->abort();
        });
    }
}

// Remote EOF goes through disconnected, after the backend's final reads.
// Other errors (including a refused initial connect) may never disconnect.
template <typename Handler>
void OnBackendFailure(QTcpSocket& socket, Handler handler) {
    QObject::connect(&socket, &QTcpSocket::errorOccurred, &socket,
                     [socket = &socket, handler = std::move(handler)](auto error) {
        if (error != QAbstractSocket::RemoteHostClosedError)
            QMetaObject::invokeMethod(socket, handler, Qt::QueuedConnection);
    });
}
}
