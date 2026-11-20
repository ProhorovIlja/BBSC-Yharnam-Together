// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <QByteArray>
#include <QElapsedTimer>
#include <QMetaObject>
#include <QUdpSocket>
#include "udp_drain_slice.h"

namespace ShadNetUdp {
// Run on the socket's event loop. The context must own both this drain and
// the socket; its destruction cancels any queued continuation.
class SocketDrain {
public:
    template <class Handle, class AccountBusy>
    void Run(QObject& context, QUdpSocket& socket, qint64 max_datagram_bytes,
             Handle handle, AccountBusy account) {
        RunSlice(context, socket, max_datagram_bytes, handle, account, false);
    }

private:
    template <class Handle, class AccountBusy>
    void RunSlice(QObject& context, QUdpSocket& socket, qint64 max_datagram_bytes,
                  Handle handle, AccountBusy account, bool already_retried) {
        if (queued_)
            return;
        QElapsedTimer busy;
        busy.start();
        QByteArray raw;
        const auto result = DrainSlice(
            [&] { return socket.hasPendingDatagrams(); },
            [&] {
                const qint64 bytes = socket.pendingDatagramSize();
                if (bytes < 0)
                    return false;
                if (max_datagram_bytes > 0 && bytes > max_datagram_bytes) {
                    // A short UDP read discards the remainder. Still charge a
                    // slot in the slice budget, but don't allocate or parse it.
                    char ignored;
                    return socket.readDatagram(&ignored, 1) >= 0;
                }
                raw.resize(static_cast<qsizetype>(bytes));
                QHostAddress sender;
                quint16 port = 0;
                const qint64 received = socket.readDatagram(raw.data(), bytes, &sender, &port);
                if (received < 0)
                    return false;
                raw.resize(static_cast<qsizetype>(received));
                handle(raw, sender, port);
                return true;
            },
            [&] { return busy.nsecsElapsed() >= 2'000'000; });
        const bool retry = result.retry_read(already_retried);
        account(busy, result.budget_yield());
        if (result.budget_yield() || retry) {
            // Qt need not signal again for the remainder of the same burst.
            queued_ = true;
            if (!QMetaObject::invokeMethod(&context, [this, &context, &socket, max_datagram_bytes, handle, account, retry] {
                    queued_ = false;
                    RunSlice(context, socket, max_datagram_bytes, handle, account, retry);
                }, Qt::QueuedConnection))
                queued_ = false;
        }
    }
    bool queued_ = false;
};
} // namespace ShadNetUdp
