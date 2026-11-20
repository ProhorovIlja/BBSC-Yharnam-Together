// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <QMetaObject>
#include <QTcpSocket>
#include <utility>

namespace ShadNetRpc {
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
