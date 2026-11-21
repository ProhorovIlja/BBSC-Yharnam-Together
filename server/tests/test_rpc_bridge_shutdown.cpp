// SPDX-License-Identifier: GPL-2.0-or-later
#include "core/libraries/network/rpc_bridge.h"
#include "core/libraries/network/server_link.h"
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
using TestSocket = SOCKET;
constexpr TestSocket InvalidSocket = INVALID_SOCKET;
int LastSocketError() { return WSAGetLastError(); }
void CloseTestSocket(TestSocket s) { closesocket(s); }
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
using TestSocket = int;
constexpr TestSocket InvalidSocket = -1;
void CloseTestSocket(TestSocket s) { close(s); }
#endif

using namespace std::chrono_literals;
static std::atomic<int> writes = 0;
namespace Libraries::Net {
bool ServerRpcSend(const void*, u32 length) {
    if (length > 0) ++writes;
    return true;
}
int ServerRpcReceive(void*, u32) { return -1; }
}

int main() {
#ifdef _WIN32
    WSADATA startup{};
    if (WSAStartup(MAKEWORD(2, 2), &startup) != 0) return 1;
#endif
    const auto port = Libraries::Net::StartRpcBridge();
    if (!port || Libraries::Net::StartRpcBridge() != port) return 2;
    const TestSocket peer = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (peer == InvalidSocket) return 3;
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);
    if (connect(peer, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) return 4;
    const auto deadline = std::chrono::steady_clock::now() + 1500ms;
    while (!writes.load() && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(5ms);
    if (!writes.load()) return 5; // Real bridge did not accept the active TCP peer.

    // Keep a live accepted connection during shutdown, so the worker must
    // release both its local TCP peer and listener before returning.
    const auto started = std::chrono::steady_clock::now();
    Libraries::Net::StopRpcBridge();
    const auto elapsed = std::chrono::steady_clock::now() - started;
    if (elapsed > 2s) return 6;
    const auto final_writes = writes.load();
    Libraries::Net::StopRpcBridge();
    if (Libraries::Net::StartRpcBridge() != 0) return 7;
    std::this_thread::sleep_for(35ms);
    if (writes.load() != final_writes) return 8;
    CloseTestSocket(peer);
#ifdef _WIN32
    WSACleanup();
#endif
    std::cout << "RPC bridge worker stopped and joined with active game TCP\n";
}
