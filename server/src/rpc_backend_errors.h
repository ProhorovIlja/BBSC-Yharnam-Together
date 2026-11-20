// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <QMetaObject>
#include <QPointer>
#include <QTcpSocket>
#include <QTimer>
#include <utility>

namespace ShadNetRpc {
inline bool MayBufferBackendRequest(QAbstractSocket::SocketState state) {
    return state == QAbstractSocket::HostLookupState ||
           state == QAbstractSocket::ConnectingState;
}

// Once disconnected, a socket may still own unread reply data. Late
// request data must not abort that socket before the reply drains.
inline bool BackendCanReceiveRequest(QAbstractSocket::SocketState state, bool eof) {
    return !eof && (state == QAbstractSocket::ConnectedState || MayBufferBackendRequest(state));
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

// Clear ownership before abort emits any synchronous socket signals.
inline void AbortRetiredBackend(QPointer<QTcpSocket>& socket) {
    auto retired = std::exchange(socket, QPointer<QTcpSocket>{});
    if (retired) {
        retired->abort();
        retired->deleteLater();
    }
}

// A pending backend connect is scoped to this socket; established and
// replaced sockets are not affected by an expired deadline.
template <typename Handler>
void OnBackendConnectTimeout(QTcpSocket& socket, int timeout_ms, Handler handler) {
    QTimer::singleShot(timeout_ms, &socket, [socket = &socket, handler = std::move(handler)] {
        if (MayBufferBackendRequest(socket->state()))
            handler();
    });
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
