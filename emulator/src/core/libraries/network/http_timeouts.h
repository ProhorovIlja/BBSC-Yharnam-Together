// SPDX-FileCopyrightText: Copyright 2026 BBSC Yharnam Together contributors
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <algorithm>
#include <chrono>
#include <cstdint>

namespace Libraries::Http::Timeouts {

// Preserve the existing microseconds-to-seconds rounding and zero-means-default convention.
constexpr std::chrono::seconds Seconds(std::uint32_t us, std::uint32_t default_seconds) {
    return std::chrono::seconds(us ? (std::uint64_t{us} + 999999) / 1000000 : default_seconds);
}

struct Budgets {
    std::chrono::seconds connect;
    std::chrono::seconds receive;
    std::chrono::seconds send;
};

constexpr Budgets ForRequest(std::uint32_t connect_us, std::uint32_t receive_us,
                             std::uint32_t send_us, bool tls) {
    const auto requested = Seconds(connect_us, 30);
    // Adapted from Awakenchan/LanternEngine#105 at 05c4b0c14b22efe4c2580825cbd55539bad1c870.
    // httplib uses the connection budget for TLS too. A one-second game setting can expire
    // during a healthy handshake. Scope the compatibility floor to HTTPS; plain HTTP and
    // explicit larger budgets retain their existing behavior. This is a deadline, not a delay.
    return {tls ? std::max(requested, std::chrono::seconds(10)) : requested,
            Seconds(receive_us, 120), Seconds(send_us, 120)};
}

template <class Client>
Budgets Configure(Client& client, std::uint32_t connect_us, std::uint32_t receive_us,
                  std::uint32_t send_us, bool tls) {
    const auto budgets = ForRequest(connect_us, receive_us, send_us, tls);
    client.set_connection_timeout(budgets.connect);
    client.set_read_timeout(budgets.receive);
    client.set_write_timeout(budgets.send);
    return budgets;
}
} // namespace Libraries::Http::Timeouts
