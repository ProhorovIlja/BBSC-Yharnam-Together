// SPDX-License-Identifier: GPL-2.0-or-later
#include <QBuffer>
#include <QByteArray>
#include <algorithm>
#include <cstdlib>
#include <iostream>
#include "bounded_socket_drain.h"
#define CHECK(condition) do { if (!(condition)) { std::cerr << __LINE__ << ": " << #condition << "\n"; std::abort(); } } while (false)

int main() {
    QByteArray payload(8 * 1024 * 1024 + 777, 'z');
    payload[0] = 'A';
    payload[16384] = 'B';
    payload[payload.size() - 1] = 'C';
    QBuffer device{&payload};
    CHECK(device.open(QIODevice::ReadOnly));
    QByteArray actual;
    int calls = 0;
    qint64 largest = 0;
    ShadNet::DrainClientSocket(device,
        [&](const QByteArray& chunk) {
            ++calls;
            largest = std::max(largest, static_cast<qint64>(chunk.size()));
            actual.append(chunk);
        }, [] { return true; });
    CHECK(actual == payload);
    CHECK(largest == ShadNet::ClientReadChunkBytes);
    CHECK(calls >= 512);
    CHECK(device.bytesAvailable() == 0);
    ShadNet::DrainClientSocket(device,
        [&](const QByteArray&) { CHECK(false && "empty QIODevice"); },
        [] { return true; });
    QBuffer interrupted{&payload};
    CHECK(interrupted.open(QIODevice::ReadOnly));
    QByteArray resumed;
    bool connected = true;
    ShadNet::DrainClientSocket(interrupted,
        [&](const QByteArray& part) {
            resumed.append(part);
            connected = false;
        }, [&] { return connected; });
    CHECK(resumed.size() == ShadNet::ClientReadChunkBytes);
    CHECK(interrupted.pos() == ShadNet::ClientReadChunkBytes);
    CHECK(interrupted.bytesAvailable() == payload.size() - ShadNet::ClientReadChunkBytes);
    connected = true;
    ShadNet::DrainClientSocket(interrupted,
        [&](const QByteArray& part) { resumed.append(part); },
        [&] { return connected; });
    CHECK(resumed == payload);
    std::cout << "Qt bounded client ingress: 8MiB ordered, 16KiB max, disconnect stop passed\n";
}
