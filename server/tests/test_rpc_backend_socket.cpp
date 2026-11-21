// SPDX-License-Identifier: GPL-2.0-or-later
#include "../src/rpc_write_budget.h"
#include "../src/rpc_backend_errors.h"
#include "../src/rpc_backend_read.h"

#include <QCoreApplication>
#include <QEventLoop>
#include <QTimer>
#include <QHostAddress>
#include <QTcpServer>
#include <QTcpSocket>
#include <iostream>

#define CHECK(x) do { if (!(x)) { std::cerr << "failure line " << __LINE__ << ": " << #x << '\n'; return 1; } } while (false)

// Force Qt's pending state without relying on external networking or on
// loopback remaining asynchronous on a particular OS.
class PendingSocket : public QTcpSocket {
public:
    using QAbstractSocket::setSocketState;
};

int BufferedReplyAcrossAckAndEof() {
    using namespace ShadNetRpc;
    using BloodborneCoop::RpcTunnel;
    QTcpServer backend;
    CHECK(backend.listen(QHostAddress::LocalHost, 0));
    QTcpSocket forward;
    forward.setReadBufferSize(4096);
    forward.connectToHost(QHostAddress::LocalHost, backend.serverPort());
    CHECK(forward.waitForConnected(2000));
    CHECK(backend.hasPendingConnections() || backend.waitForNewConnection(2000));
    auto* local = backend.nextPendingConnection();
    CHECK(local);
    const QByteArray reply("reply after the ACK");
    CHECK(local->write(reply) == reply.size());
    CHECK(local->waitForBytesWritten(2000));
    CHECK(forward.bytesAvailable() || forward.waitForReadyRead(2000));

    RpcTunnel out{"shadnet", 7}, in{"game", 9};
    out.Open(0);
    const std::array<u8, 22> prior{};
    out.Write(prior, 0);
    BloodborneCoop::RpcReadPause pause;
    constexpr size_t budget = 32;
    CHECK(PumpBackendReply(forward, out, pause, false, 1, budget, 64) == BackendRead::Pending);
    const auto remaining = forward.bytesAvailable();
    CHECK(remaining > 5 && remaining < reply.size());
    CHECK(PumpBackendReply(forward, out, pause, false, 5001, budget, 64) == BackendRead::Failed);
    CHECK(forward.bytesAvailable() == remaining);

    local->disconnectFromHost();
    CHECK(forward.state() == QAbstractSocket::UnconnectedState || forward.waitForDisconnected(2000));
    CHECK(forward.bytesAvailable() == remaining);
    CHECK(!BackendCanReceiveRequest(forward.state(), true));
    CHECK(!BackendCanReceiveRequest(forward.state(), false));
    CHECK(BackendCanReceiveRequest(QAbstractSocket::ConnectedState, false));
    CHECK(!BackendCanReceiveRequest(QAbstractSocket::ConnectedState, true));
    CHECK(BackendCanReceiveRequest(QAbstractSocket::ConnectingState, false));
    QByteArray received;
    int messages = 0;
    for (const auto& wire : out.Flush(5002)) {
        for (const auto& event : in.Receive(wire, 5002)) {
            if (event.kind == RpcTunnel::Event::Kind::Data && ++messages > 1)
                received.append(reinterpret_cast<const char*>(event.bytes.data()), event.bytes.size());
        }
    }
    CHECK(received == reply.left(reply.size() - remaining));
    for (const auto& ack : in.Flush(5003))
        out.Receive(ack, 5003);
    CHECK(out.UnackedBytes() == 0);
    CHECK(PumpBackendReply(forward, out, pause, true, 5004, budget, 5) == BackendRead::Pending);
    CHECK(forward.bytesAvailable() == remaining - 5);
    CHECK(PumpBackendReply(forward, out, pause, true, 5005, budget, 64) == BackendRead::DrainedEof);
    out.Close(5005);
    bool closed = false;
    for (const auto& wire : out.Flush(5005)) {
        for (const auto& event : in.Receive(wire, 5005)) {
            CHECK(!closed);
            if (event.kind == RpcTunnel::Event::Kind::Data)
                received.append(reinterpret_cast<const char*>(event.bytes.data()), event.bytes.size());
            else if (event.kind == RpcTunnel::Event::Kind::Closed)
                closed = true;
        }
    }
    CHECK(closed && received == reply);
    return 0;
}

int LargeBackendReplyHasBoundedReliableDebt() {
    using namespace ShadNetRpc;
    using BloodborneCoop::RpcTunnel;
    QTcpServer listener;
    CHECK(listener.listen(QHostAddress::LocalHost, 0));
    QTcpSocket client;
    client.setReadBufferSize(32 * 1024);
    client.connectToHost(QHostAddress::LocalHost, listener.serverPort());
    CHECK(client.waitForConnected(2000));
    CHECK(listener.hasPendingConnections() || listener.waitForNewConnection(2000));
    auto* backend = listener.nextPendingConnection();
    CHECK(backend);
    QByteArray expected(512 * 1024 + 17, '\0');
    for (qsizetype i = 0; i < expected.size(); ++i)
        expected[i] = static_cast<char>('A' + (i % 26));
    CHECK(backend->write(expected) == expected.size());

    RpcTunnel outbound{"shadnet", 71}, inbound{"game", 79};
    outbound.Open(0);
    for (const auto& frame : outbound.Flush(0))
        inbound.Receive(frame, 0);
    for (const auto& ack : inbound.Flush(0))
        outbound.Receive(ack, 0);
    BloodborneCoop::RpcReadPause pause;
    QByteArray actual;
    constexpr size_t budget = 64 * 1024;
    size_t peak_debt = 0;
    bool blocked_once = false;
    for (int tick = 1; tick <= 500 && actual.size() < expected.size(); ++tick) {
        QCoreApplication::processEvents();
        backend->flush();
        if (client.bytesAvailable() == 0)
            client.waitForReadyRead(50);
        const auto available = client.bytesAvailable();
        const auto state = PumpBackendReply(client, outbound, pause, false,
                                            tick * 10, budget, 16 * 1024);
        CHECK(state == BackendRead::Pending);
        blocked_once |= available > 0 && client.bytesAvailable() == available;
        peak_debt = (std::max)(peak_debt, outbound.UnackedBytes());
        CHECK(peak_debt <= budget);
        for (const auto& frame : outbound.Flush(tick * 10, 128)) {
            for (const auto& event : inbound.Receive(frame, tick * 10)) {
                CHECK(event.kind != RpcTunnel::Event::Kind::PeerRestarted);
                if (event.kind == RpcTunnel::Event::Kind::Data)
                    actual.append(reinterpret_cast<const char*>(event.bytes.data()),
                                  static_cast<qsizetype>(event.bytes.size()));
            }
        }
        if (tick % 12 == 0) {
            for (const auto& ack : inbound.Flush(tick * 10 + 1))
                outbound.Receive(ack, tick * 10 + 1);
        }
    }
    CHECK(actual == expected);
    CHECK(peak_debt > 16 * 1024 && blocked_once);
    for (const auto& ack : inbound.Flush(5100))
        outbound.Receive(ack, 5100);
    CHECK(outbound.UnackedBytes() == 0);
    backend->disconnectFromHost();
    return 0;
}

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    CHECK(LargeBackendReplyHasBoundedReliableDebt() == 0);
    CHECK(BufferedReplyAcrossAckAndEof() == 0);
    PendingSocket pending;
    pending.setSocketState(QAbstractSocket::ConnectingState);
    int expired = 0;
    QEventLoop pendingLoop;
    ShadNetRpc::OnBackendConnectTimeout(pending, 0, [&] {
        ++expired;
        pendingLoop.quit();
    });
    {
        PendingSocket retired;
        retired.setSocketState(QAbstractSocket::ConnectingState);
        ShadNetRpc::OnBackendConnectTimeout(retired, 0, [&] { expired += 100; });
    }
    CHECK(expired == 0);
    QTimer::singleShot(2000, &pendingLoop, &QEventLoop::quit);
    pendingLoop.exec();
    CHECK(expired == 1);
    pending.setSocketState(QAbstractSocket::UnconnectedState);
    QTcpServer backend;
    CHECK(backend.listen(QHostAddress::LocalHost, 0));
    QTcpSocket forward;
    forward.connectToHost(QHostAddress::LocalHost, backend.serverPort());
    CHECK(forward.waitForConnected(2000));
    CHECK(backend.hasPendingConnections() || backend.waitForNewConnection(2000));
    QTcpSocket* local = backend.nextPendingConnection();
    CHECK(local);
    int deadlines = 0;
    ShadNetRpc::OnBackendConnectTimeout(forward, 0, [&] { ++deadlines; });
    QEventLoop established;
    QTimer::singleShot(10, &established, &QEventLoop::quit);
    established.exec();
    CHECK(deadlines == 0); // a successful connect is not torn down by the timer
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

    // A normal close still delivers its queued request before disconnecting.
    QTcpSocket draining;
    draining.connectToHost(QHostAddress::LocalHost, backend.serverPort());
    CHECK(draining.waitForConnected(2000));
    CHECK(backend.hasPendingConnections() || backend.waitForNewConnection(2000));
    QTcpSocket* reader = backend.nextPendingConnection();
    CHECK(reader);
    CHECK(draining.write("done", 4) == 4);
    ShadNetRpc::DrainAndCloseBackend(draining);
    if (draining.state() != QAbstractSocket::UnconnectedState)
        CHECK(draining.waitForDisconnected(2000));
    QByteArray finalBytes;
    while (finalBytes.size() < 4) {
        CHECK(reader->bytesAvailable() || reader->waitForReadyRead(2000));
        finalBytes += reader->readAll();
    }
    CHECK(finalBytes == "done");

    // The receiver stops reading. Keep the kernel send buffer small so some
    // of this production-sized request remains in Qt when the socket retires.
    QTcpSocket stalled;
    stalled.connectToHost(QHostAddress::LocalHost, backend.serverPort());
    CHECK(stalled.waitForConnected(2000));
    CHECK(backend.hasPendingConnections() || backend.waitForNewConnection(2000));
    QTcpSocket* blocked = backend.nextPendingConnection();
    CHECK(blocked);
    blocked->setReadBufferSize(1);
    stalled.setSocketOption(QAbstractSocket::SendBufferSizeSocketOption, 4096);
    const QByteArray backlog(1 << 20, 'x');
    CHECK(stalled.write(backlog) == backlog.size());
    QEventLoop drainLoop;
    QObject::connect(&stalled, &QTcpSocket::disconnected, &drainLoop, &QEventLoop::quit);
    ShadNetRpc::DrainAndCloseBackend(stalled, 40);
    CHECK(stalled.state() == QAbstractSocket::ClosingState && stalled.bytesToWrite() > 0);
    QTimer::singleShot(2000, &drainLoop, &QEventLoop::quit);
    drainLoop.exec();
    CHECK(stalled.state() == QAbstractSocket::UnconnectedState && stalled.bytesToWrite() == 0);
    std::cout << "RPC backend TCP: graceful drain and bounded stalled close passed\n";

    // A replacement must abort a live graceful drain immediately and
    // clear the owner's pointer before the socket emits disconnected.
    auto* old = new QTcpSocket(&backend);
    old->connectToHost(QHostAddress::LocalHost, backend.serverPort());
    CHECK(old->waitForConnected(2000));
    CHECK(backend.hasPendingConnections() || backend.waitForNewConnection(2000));
    auto* oldReader = backend.nextPendingConnection();
    CHECK(oldReader);
    oldReader->setReadBufferSize(1);
    old->setSocketOption(QAbstractSocket::SendBufferSizeSocketOption, 4096);
    CHECK(old->write(backlog) == backlog.size());
    ShadNetRpc::DrainAndCloseBackend(*old);
    CHECK(old->state() == QAbstractSocket::ClosingState && old->bytesToWrite() > 0);
    QPointer<QTcpSocket> retired(old);
    bool clearedDuringDisconnect = false;
    QObject::connect(old, &QTcpSocket::disconnected, &app,
                     [&] { clearedDuringDisconnect = retired.isNull(); });
    ShadNetRpc::AbortRetiredBackend(retired);
    CHECK(retired.isNull() && clearedDuringDisconnect && old->bytesToWrite() == 0);
    ShadNetRpc::AbortRetiredBackend(retired);

    QTcpSocket cancelled;
    cancelled.connectToHost(QHostAddress::LocalHost, backend.serverPort());
    if (ShadNetRpc::MayBufferBackendRequest(cancelled.state())) {
        ShadNetRpc::DrainAndCloseBackend(cancelled);
        CHECK(cancelled.state() == QAbstractSocket::UnconnectedState);
    } else {
        // Some platforms complete loopback connect synchronously.
        CHECK(cancelled.state() == QAbstractSocket::ConnectedState);
        cancelled.abort();
    }

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
    bool failed = false;
    ShadNetRpc::OnBackendFailure(refused, [&] { failed = true; }, [&] {
        failures += failed ? 1 : 100;
        loop.quit();
    });
    refused.connectToHost(QHostAddress::LocalHost, unusedPort);
    CHECK(failures == 0); // cleanup must not run inside connect/error transitions
    QTimer::singleShot(2000, &loop, &QEventLoop::quit);
    loop.exec();
    CHECK(refused.error() == QAbstractSocket::ConnectionRefusedError);
    CHECK(!MayBufferBackendRequest(refused.state()));
    CHECK(failed && failures == 1 && disconnects == 0);
    PendingSocket transition;
    int marked = 0, cleaned = 0;
    ShadNetRpc::OnBackendFailure(transition, [&] { ++marked; }, [&] { ++cleaned; });
    transition.errorOccurred(QAbstractSocket::RemoteHostClosedError);
    CHECK(marked == 0);
    transition.errorOccurred(QAbstractSocket::NetworkError);
    CHECK(marked == 1 && cleaned == 0);
    QCoreApplication::processEvents();
    CHECK(cleaned == 1);
    std::cout << "RPC backend TCP: initial refusal triggers deferred cleanup without disconnect\n";
}
