// SPDX-License-Identifier: GPL-2.0-or-later
#include "../src/udp_socket_drain.h"

#include <QCoreApplication>
#include <QTimer>
#include <QVariant>
#include <cstdlib>
#include <iostream>

#define CHECK(x) do { if (!(x)) { std::cerr << "failure line " << __LINE__ << '\n'; std::abort(); } } while (false)

class Fixture : public QObject {
public:
    static constexpr int Burst = 180;
    static constexpr qint64 Limit = 512;
    QUdpSocket receiver{this};
    QUdpSocket sender{this};
    ShadNetUdp::SocketDrain drain;
    int seen = 0;
    int slices = 0;
    int yields = 0;
    int interleaved_at = -1;

    void send(int id) {
        // Include a zero-length datagram in the middle of the burst.
        const auto payload = id == 10 ? QByteArray{} : QByteArray::number(id);
        CHECK(sender.writeDatagram(payload, QHostAddress::LocalHost, receiver.localPort()) == payload.size());
    }

    void run() {
        drain.Run(*this, receiver, Limit, [this](const QByteArray& raw, const QHostAddress& address, quint16 port) {
            CHECK(address == QHostAddress::LocalHost);
            CHECK(port == sender.localPort());
            CHECK(raw == (seen == 10 ? QByteArray{} : QByteArray::number(seen)));
            ++seen;
            if (seen == 1) {
                CHECK(QMetaObject::invokeMethod(this, [this] {
                    interleaved_at = seen;
                }, Qt::QueuedConnection));
            }
            if (seen == Burst) {
                CHECK(interleaved_at > 0 && interleaved_at <= 128);
                // Start a second burst only after the first has completely drained.
                CHECK(QMetaObject::invokeMethod(this, [this] { send(Burst); }, Qt::QueuedConnection));
            }
            if (seen == Burst + 1)
                QCoreApplication::quit();
        }, [this](const QElapsedTimer&, bool yielded) { ++slices; yields += yielded; });
    }
};

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    Fixture f;
    CHECK(f.receiver.bind(QHostAddress(QHostAddress::LocalHost), 0));
    f.receiver.setSocketOption(QAbstractSocket::ReceiveBufferSizeSocketOption, 256 * 1024);
    CHECK(f.sender.bind(QHostAddress(QHostAddress::LocalHost), 0));
    QObject::connect(&f.receiver, &QUdpSocket::readyRead, &f, [&] { f.run(); });
    // Fill the receive queue before any event is serviced: no extra arrivals
    // are needed to trigger the continuation.
    for (int i = 0; i < Fixture::Burst; ++i) {
        // Exercise rejection both within the first slice and after a yield.
        if (i == 20 || i == 160) {
            const QByteArray oversized(Fixture::Limit + 1, 'x');
            CHECK(f.sender.writeDatagram(oversized, QHostAddress::LocalHost,
                                          f.receiver.localPort()) == oversized.size());
        }
        f.send(i);
    }
    QTimer::singleShot(3000, &app, [&] { app.exit(2); });
    CHECK(app.exec() == 0);
    CHECK(f.seen == Fixture::Burst + 1 && f.slices >= 3);
    CHECK(f.yields > 0 && f.yields <= f.slices - 2);
    std::cout << "UDP loopback: ordered continuation, event-loop yield and new-burst rearm passed\n";
}
