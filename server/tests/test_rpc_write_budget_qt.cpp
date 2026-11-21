// SPDX-License-Identifier: GPL-2.0-or-later
#include "src/rpc_write_budget.h"
#include <QCoreApplication>
#include <QHostAddress>
#include <QTcpServer>
#include <QTcpSocket>
#include <QByteArray>
#include <iostream>
#define CHECK(test) do { if (!(test)) { std::cerr << __LINE__ << ": " << #test << "\n"; return 1; } } while(false)

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    QTcpServer server;
    CHECK(server.listen(QHostAddress::LocalHost, 0));
    QTcpSocket sender;
    sender.connectToHost(QHostAddress::LocalHost, server.serverPort());
    CHECK(sender.waitForConnected(3000));
    CHECK(server.hasPendingConnections() || server.waitForNewConnection(3000));
    QTcpSocket* receiver = server.nextPendingConnection();
    CHECK(receiver != nullptr);
    receiver->setReadBufferSize(1);
    constexpr qint64 cap = 4096;
    const QByteArray first(cap - 1, 'a');
    CHECK(ShadNetRpc::TryQueueBackendWrite(sender, first.constData(), first.size(), cap));
    CHECK(sender.bytesToWrite() == cap - 1);
    CHECK(!ShadNetRpc::TryQueueBackendWrite(sender, "xy", 2, cap));
    CHECK(sender.bytesToWrite() == cap - 1);
    CHECK(ShadNetRpc::TryQueueBackendWrite(sender, "b", 1, cap));
    CHECK(sender.bytesToWrite() == cap);
    while (sender.bytesToWrite() > 0)
        CHECK(sender.waitForBytesWritten(3000));
    QByteArray delivered;
    while (delivered.size() < cap) {
        CHECK(receiver->bytesAvailable() || receiver->waitForReadyRead(3000));
        delivered += receiver->readAll();
    }
    CHECK(delivered == first + 'b');
    CHECK(ShadNetRpc::TryQueueBackendWrite(sender, "c", 1, cap));
    sender.abort();
    CHECK(sender.bytesToWrite() == 0);
    std::cout << "Qt TCP pending-backlog bound, refusal and drain passed\n";
}
