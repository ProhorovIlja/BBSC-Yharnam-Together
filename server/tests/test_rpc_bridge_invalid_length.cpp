// SPDX-License-Identifier: GPL-2.0-or-later
// Compiles and drives production RPC bridge with a deliberately invalid
// receive length, not just a simulation of the length helper.
#include "core/libraries/network/rpc_bridge.h"
#include "core/libraries/network/server_link.h"
#include <atomic>
#include <chrono>
#include <thread>
#include <iostream>
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
using Socket = SOCKET;
void Close(Socket s) { closesocket(s); }
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
using Socket = int;
void Close(Socket s) { close(s); }
#endif
using namespace std::chrono_literals;
std::atomic<int> calls{0};
std::atomic<int> sends{0};
namespace Libraries::Net {
bool ServerRpcSend(const void*, u32 count) {
    if (count) ++sends;
    return true;
}
int ServerRpcReceive(void* buffer, u32 len) {
    if (calls.fetch_add(1) == 0) {
        // The transport claims it returned more than the caller's buffer.
        // It has not written the claimed bytes. The bridge must discard.
        (void)buffer;
        return static_cast<int>(len) + 120;
    }
    return -1;
}
}
int main() {
#ifdef _WIN32
    WSADATA wsa{};
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return 1;
#endif
    const auto port = Libraries::Net::StartRpcBridge();
    if (port == 0) return 2;
    const auto deadline = std::chrono::steady_clock::now() + 1500ms;
    while (calls.load() < 1 && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(5ms);
    if (calls.load() < 1) return 3;
    const Socket client = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
#ifdef _WIN32
    if (client == INVALID_SOCKET) return 4;
#else
    if (client < 0) return 4;
#endif
    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = htons(port);
    if (connect(client, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0)
        return 5;
    const auto ready = std::chrono::steady_clock::now() + 1500ms;
    while (sends.load() < 1 && std::chrono::steady_clock::now() < ready)
        std::this_thread::sleep_for(5ms);
    if (sends.load() == 0) return 6;
    Libraries::Net::StopRpcBridge();
    Close(client);
#ifdef _WIN32
    WSACleanup();
#endif
    std::cout << "RPC bridge survived oversized adapter length then accepted TCP\n";
}
