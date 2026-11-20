// SPDX-License-Identifier: GPL-2.0-or-later
#include "../src/rpc_write_budget.h"
#include "../src/rpc_backend_errors.h"

#include <QCoreApplication>
#include <QEventLoop>
#include <QTimer>
#include <QHostAddress>
#include <QTcpServer>
#include <QTcpSocket>
#include <iostream>

#define CHECK(x) do { if (!(x)) { std::cerr << "failure line " << __LINE__ << ": " << #x << '\n'; return 1; } } while (false)

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    QTcpServer backend;
    CHECK(backend.listen(QHostAddress::LocalHost, 0));
    QTcpSocket forward;
    forward.connectToHost(QHostAddress::LocalHost, backend.serverPort());
    CHECK(forward.waitForConnected(2000));
    CHECK(backend.hasPendingConnections() || backend.waitForNewConnection(2000));
    QTcpSocket* local = backend.nextPendingConnection();
    CHECK(local);
    constexpr qint64 cap = 4096;
    const QByteArray first(cap - 1, 'a');
    CHECK(ShadNetRpc::TryQueueBackendWrite(forward, first.constData(), first.size(), cap));
    CHECK(forward.bytesToWrite() == cap - 1);
    CHECK(!ShadNetRpc::TryQueueBackendWrite(forward, "xx", 2, cap));
    CHECK(forward.bytesToWrite() == cap - 1);
    CHECK(ShadNetRpc::TryQueueBackendWrite(forward, "b", 1, cap));
    CHECK(forward.bytesToWrite() == cap);
    while (forward.bytesToWrite() > 0)
        CHECK(forward.waitForBytesWritten(2000));
    QByteArray delivered;
    while (delivered.size() < cap) {
        CHECK(local->bytesAvailable() || local->waitForReadyRead(2000));
        delivered += local->readAll();
    }
    CHECK(delivered == first + 'b');
    CHECK(ShadNetRpc::TryQueueBackendWrite(forward, "c", 1, cap));
    forward.abort();
    CHECK(forward.bytesToWrite() == 0);
    std::cout << "RPC backend TCP: cap, rejection, drain and abort passed\n";

    const auto unusedPort = backend.serverPort();
    backend.close();
    QTcpSocket refused;
    using ShadNetRpc::MayBufferBackendRequest;
    CHECK(MayBufferBackendRequest(QAbstractSocket::HostLookupState));
    CHECK(MayBufferBackendRequest(QAbstractSocket::ConnectingState));
    CHECK(!MayBufferBackendRequest(QAbstractSocket::ClosingState));
    CHECK(!MayBufferBackendRequest(refused.state()));
    QEventLoop loop;
    int failures = 0, disconnects = 0;
    QObject::connect(&refused, &QTcpSocket::disconnected, [&] { ++disconnects; });
    ShadNetRpc::OnBackendFailure(refused, [&] {
        ++failures;
        loop.quit();
    });
    refused.connectToHost(QHostAddress::LocalHost, unusedPort);
    CHECK(failures == 0); // cleanup must not run inside connect/error transitions
    QTimer::singleShot(2000, &loop, &QEventLoop::quit);
    loop.exec();
    CHECK(refused.error() == QAbstractSocket::ConnectionRefusedError);
    CHECK(!MayBufferBackendRequest(refused.state()));
    CHECK(failures == 1 && disconnects == 0);
    std::cout << "RPC backend TCP: initial refusal triggers deferred cleanup without disconnect\n";
}
