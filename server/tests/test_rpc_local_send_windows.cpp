// SPDX-License-Identifier: GPL-2.0-or-later
#include "core/libraries/network/rpc_local_send.h"
#include <winsock2.h>
#include <iostream>

int main() {
    WSADATA data{};
    if (WSAStartup(MAKEWORD(2, 2), &data) != 0) return 1;
    SOCKET s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s == INVALID_SOCKET) return 2;
    if (!Libraries::Net::RpcLocal::ConfigureLocalSend(s)) return 3;
    DWORD timeout = 0;
    int size = sizeof(timeout);
    if (getsockopt(s, SOL_SOCKET, SO_SNDTIMEO, reinterpret_cast<char*>(&timeout), &size) != 0)
        return 4;
    closesocket(s);
    WSACleanup();
    if (timeout != static_cast<DWORD>(Libraries::Net::RpcLocal::LocalSendTimeoutMs))
        return 5;
    std::cout << "RPC local write timeout configured" << std::endl;
    return 0;
}
