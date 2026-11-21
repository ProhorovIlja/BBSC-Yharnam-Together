// SPDX-License-Identifier: GPL-2.0-or-later
#include "../src/rpc_backend_errors.h"
#include <QCoreApplication>
#include <QHostAddress>
#include <QPointer>
#include <QTcpServer>
#include <QTcpSocket>
#include <iostream>

#define CHECK(condition) do { if (!(condition)) { \
    std::cerr << "failure at " << __LINE__ << ": " << #condition << '\n'; \
    return 1; } } while (false)

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    QTcpServer backend;
    CHECK(backend.listen(QHostAddress::LocalHost, 0));
    QTcpSocket client;
    client.connectToHost(QHostAddress::LocalHost, backend.serverPort());
    CHECK(client.waitForConnected(2000));
    CHECK(backend.hasPendingConnections() || backend.waitForNewConnection(2000));
    auto* reader = backend.nextPendingConnection();
    CHECK(reader);
    CHECK(client.write("done", 4) == 4);
    ShadNetRpc::DrainAndCloseBackend(client);
    if (client.state() != QAbstractSocket::UnconnectedState)
        CHECK(client.waitForDisconnected(2000));
    CHECK(reader->bytesAvailable() || reader->waitForReadyRead(2000));
    CHECK(reader->readAll() == "done");

    auto* old = new QTcpSocket(&app);
    old->connectToHost(QHostAddress::LocalHost, backend.serverPort());
    CHECK(old->waitForConnected(2000));
    CHECK(backend.hasPendingConnections() || backend.waitForNewConnection(2000));
    auto* blocked = backend.nextPendingConnection();
    CHECK(blocked);
    blocked->setReadBufferSize(1);
    old->setSocketOption(QAbstractSocket::SendBufferSizeSocketOption, 4096);
    const QByteArray backlog(1 << 20, 'x');
    CHECK(old->write(backlog) == backlog.size());
    ShadNetRpc::DrainAndCloseBackend(*old);
    CHECK(old->state() == QAbstractSocket::ClosingState && old->bytesToWrite() > 0);
    QPointer<QTcpSocket> retired(old);
    bool clear_before_signal = false;
    QObject::connect(old, &QTcpSocket::disconnected, &app, [&] {
        clear_before_signal = retired.isNull();
    });
    ShadNetRpc::AbortRetiredBackend(retired);
    CHECK(retired.isNull() && clear_before_signal && old->bytesToWrite() == 0);
    ShadNetRpc::AbortRetiredBackend(retired);
    QCoreApplication::processEvents();
    return 0;
}
