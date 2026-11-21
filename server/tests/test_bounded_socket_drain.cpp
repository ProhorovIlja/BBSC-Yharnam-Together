// SPDX-License-Identifier: GPL-2.0-or-later
#include <QBuffer>
#include <QByteArray>
#include <algorithm>
#include <cassert>
#include <iostream>
#include "bounded_socket_drain.h"

int main() {
    QByteArray payload(8 * 1024 * 1024 + 777, 'z');
    payload[0] = 'A';
    payload[16384] = 'B';
    payload[payload.size() - 1] = 'C';
    QBuffer device{&payload};
    assert(device.open(QIODevice::ReadOnly));
    QByteArray actual;
    int calls = 0;
    qint64 largest = 0;
    ShadNet::DrainClientSocket(device,
        [&](const QByteArray& chunk) {
            ++calls;
            largest = std::max(largest, static_cast<qint64>(chunk.size()));
            actual.append(chunk);
        }, [] { return true; });
    assert(actual == payload);
    assert(largest == ShadNet::ClientReadChunkBytes);
    assert(calls >= 512);
    assert(device.bytesAvailable() == 0);
    ShadNet::DrainClientSocket(device,
        [&](const QByteArray&) { assert(false && "empty QIODevice"); },
        [] { return true; });
    QBuffer interrupted{&payload};
    assert(interrupted.open(QIODevice::ReadOnly));
    QByteArray resumed;
    bool connected = true;
    ShadNet::DrainClientSocket(interrupted,
        [&](const QByteArray& part) {
            resumed.append(part);
            connected = false;
        }, [&] { return connected; });
    assert(resumed.size() == ShadNet::ClientReadChunkBytes);
    assert(interrupted.pos() == ShadNet::ClientReadChunkBytes);
    assert(interrupted.bytesAvailable() == payload.size() - ShadNet::ClientReadChunkBytes);
    connected = true;
    ShadNet::DrainClientSocket(interrupted,
        [&](const QByteArray& part) { resumed.append(part); },
        [&] { return connected; });
    assert(resumed == payload);
    std::cout << "Qt bounded client ingress: 8MiB ordered, 16KiB max, disconnect stop passed\n";
}
