// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

namespace ultimate {
// Call only on a serialized connection executor, after the wire layer has
// authenticated room, peer, transport endpoint, epoch and packet contents.
// This policy neither authenticates packets nor opens a socket. Endpoint is a
// canonical endpoint digest supplied by that layer, not a peer-claimed address.
struct PathBinding {
    std::uint64_t room = 0, session = 0, local_connection = 0, peer_connection = 0, epoch = 0;
    std::array<std::uint8_t, 32> endpoint{};
    constexpr bool operator==(const PathBinding&) const = default;
    [[nodiscard]] bool valid() const {
        return room && session && local_connection && peer_connection && epoch &&
               endpoint != std::array<std::uint8_t, 32>{};
    }
};
using ProbeNonce = std::array<std::uint8_t, 16>;
enum class Traffic { Membership, WorldCommit, BossResult, Reward, TravelCommit,
                     InvasionAdmission, PoseSnapshot, VisualEmote, Unknown };
enum class Route { Authority, Direct, Relay, Unavailable };

class HybridPathLease {
public:
    static constexpr std::uint64_t ProbeTimeoutMs = 1000, LeaseMs = 2000;

    [[nodiscard]] bool bind(PathBinding value, std::uint64_t now) {
        const bool clock_ok = tick(now);
        if (!clock_ok || !value.valid()) {
            clear_probe();
            binding_.reset();
            allowed_ = false;
            return false;
        }
        // Repeated notification of the same binding is not a path change.
        if (matches(value)) return true;
        clear_probe();
        // Endpoint rebinding must not reset the replay windows. A new
        // authenticated session/epoch/connection does reset them.
        if (!replay_scope_ || value.room != replay_scope_->room || value.session != replay_scope_->session ||
            value.epoch != replay_scope_->epoch || value.local_connection != replay_scope_->local_connection ||
            value.peer_connection != replay_scope_->peer_connection) {
            last_seq_ = {};
            allowed_ = false; // A different authenticated peer needs fresh consent.
        }
        replay_scope_ = value;
        binding_ = value;
        return true;
    }

    void allow_direct(bool value) {
        allowed_ = value;
        if (!value) clear_probe();
    }

    // Caller generates an unpredictable nonce with a CSPRNG. Serial is strictly
    // increasing for this policy object's entire lifetime, including reconnects.
    [[nodiscard]] bool challenge(const PathBinding& peer, std::uint64_t serial,
                                 ProbeNonce nonce, std::uint64_t now) {
        // One in-flight challenge: a scheduler tick must not replace a nonce
        // while its authenticated reply can still arrive.
        if (!tick(now) || !matches(peer) || !allowed_ || pending_ || serial <= highest_serial_ ||
            nonce == ProbeNonce{}) return false;
        highest_serial_ = serial;
        pending_ = Probe{serial, nonce, now};
        return true;
    }

    // The adapter could not queue this exact probe. Retire it without
    // recycling its serial or invalidating an independently verified path.
    [[nodiscard]] bool probe_send_failed(const PathBinding& peer, std::uint64_t serial,
                                         std::uint64_t now) {
        if (!tick(now) || !matches(peer) || !pending_ || pending_->serial != serial)
            return false;
        pending_.reset();
        return true;
    }

    // An authenticated reply to our fresh challenge proves request + return.
    // The receive layer must additionally verify it arrived on peer.endpoint.
    [[nodiscard]] bool acknowledge(const PathBinding& peer, std::uint64_t serial,
                                   ProbeNonce nonce, std::uint64_t now) {
        if (!tick(now) || !matches(peer) || !allowed_ || !pending_ ||
            pending_->serial != serial || pending_->nonce != nonce) return false;
        pending_.reset(); // Duplicate ACKs can never renew the lease.
        verified_ = Verified{serial, now};
        return true;
    }

    // Capture this ticket when scheduling work on the verified direct path,
    // not when handling an asynchronous completion. Tickets are pair-local.
    [[nodiscard]] std::optional<std::uint64_t> direct_ticket(std::uint64_t now) {
        if (!live(now)) return std::nullopt;
        return verified_->serial;
    }

    // Revalidate a queued visual send on the serialized executor immediately
    // before handing it to the transport. Never use this for authority traffic.
    [[nodiscard]] bool direct_send_current(const PathBinding& peer, Traffic stream,
                                          std::uint64_t ticket, std::uint64_t now) {
        return live(now) && matches(peer) && verified_->serial == ticket &&
               (stream == Traffic::PoseSnapshot || stream == Traffic::VisualEmote);
    }

    // Confirmed path failure, not an individual packet loss. A stale callback
    // cannot demote a newer proof, even if the peer and endpoint are unchanged.
    // Clear pending ACKs but keep consent and shared replay state.
    [[nodiscard]] bool direct_failed(const PathBinding& peer, std::uint64_t ticket,
                                     std::uint64_t now) {
        if (!live(now) || !matches(peer) || verified_->serial != ticket) return false;
        clear_probe();
        return true;
    }

    [[nodiscard]] Route route(Traffic event, bool authority_ready, bool relay_ready,
                              std::uint64_t now) {
        const bool direct = live(now);
        switch (event) {
        case Traffic::Membership: case Traffic::WorldCommit: case Traffic::BossResult:
        case Traffic::Reward: case Traffic::TravelCommit: case Traffic::InvasionAdmission:
            return authority_ready ? Route::Authority : Route::Unavailable;
        case Traffic::PoseSnapshot: case Traffic::VisualEmote:
            return direct ? Route::Direct : relay_ready ? Route::Relay : Route::Unavailable;
        default: return Route::Unavailable;
        }
    }

    // Replay state is shared across relay/direct and separate for the two
    // visual streams. Renegotiate epoch before the uint32 sequence wraps.
    [[nodiscard]] bool accept_visual(const PathBinding& peer, Traffic stream,
                                     std::uint32_t sequence, Route received_on,
                                     bool relay_ready, std::uint64_t now) {
        const bool direct = live(now);
        if (!matches(peer) || (received_on != Route::Relay && received_on != Route::Direct) ||
            (received_on == Route::Relay && !relay_ready) ||
            (received_on == Route::Direct && !direct)) return false;
        const auto index = stream == Traffic::PoseSnapshot ? 0U : 1U;
        if (stream != Traffic::PoseSnapshot && stream != Traffic::VisualEmote) return false;
        auto& last = last_seq_[index];
        if (last && sequence <= *last) return false;
        last = sequence;
        return true;
    }

    void disconnect() { binding_.reset(); allowed_ = false; clear_probe(); }

private:
    struct Probe { std::uint64_t serial; ProbeNonce nonce; std::uint64_t started; };
    struct Verified { std::uint64_t serial, at; };
    std::optional<PathBinding> binding_;
    // Keep the stream's identity after losing the active transport binding.
    // Otherwise rebinding that same session would admit captured old packets.
    // The authenticated wire layer must reject rollback to a retired scope.
    std::optional<PathBinding> replay_scope_;
    std::optional<Probe> pending_;
    std::optional<Verified> verified_;
    std::optional<std::uint64_t> last_time_;
    std::array<std::optional<std::uint32_t>, 2> last_seq_{};
    std::uint64_t highest_serial_ = 0;
    bool allowed_ = false;
    bool clock_fault_ = false;

    bool matches(const PathBinding& peer) const { return binding_ && *binding_ == peer; }
    void clear_probe() { pending_.reset(); verified_.reset(); }
    bool tick(std::uint64_t now) {
        if (last_time_ && now < *last_time_) {
            // A monotonic-clock regression is an integration error. Destroy
            // and reconstruct the policy with a new authenticated connection.
            clock_fault_ = true;
            clear_probe();
        }
        if (clock_fault_) return false;
        last_time_ = now;
        if (pending_ && now - pending_->started >= ProbeTimeoutMs) pending_.reset();
        if (verified_ && now - verified_->at >= LeaseMs) verified_.reset();
        return true;
    }
    bool live(std::uint64_t now) { return tick(now) && allowed_ && binding_ && verified_; }
};
} // namespace ultimate
