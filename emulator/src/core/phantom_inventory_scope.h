// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// B69: slot-scoped, game-thread-only key-item observer identity. A phantom's
// inventory pointer and first/last observations are ONLY valid for the exact
// character generation and save slot that created them. This guard does not
// access a real save, session or network. The returned "changed" signal
// directs the real game hook to clear its cached observations immediately.
#include <cstddef>
#include <cstdint>

namespace BloodborneCoop {

// Shared validated runtime owner identity: all retail userdata0000..0009
// and a nonzero generation are required for BOTH phantom inventories and
// delayed boss/NPC rewards. A slot alone can belong to a later hunter.
[[nodiscard]] inline constexpr bool ValidSaveCharacterScope(
    int slot, std::uint64_t generation) noexcept {
    return slot >= 0 && slot < 10 && generation != 0;
}

// At an own-list transition, never forget earned phantom items while the
// game's item grant path is unready. Zero owed items can retire without a
// grant. A ready native call is NOT proof of durable save acknowledgement.
[[nodiscard]] inline constexpr bool PhantomReturnMayRetireSnapshot(
    std::size_t missing_items, bool native_give_ready) noexcept {
    return missing_items == 0 || native_give_ready;
}

// B75: a native GiveItems call has a void return and can be asynchronous.
// Record ONE attempt until a later read of the hunter's own inventory
// observes no missing key goods. Never auto-repeat an ambiguous grant: the
// first call may have succeeded, and a second could duplicate a reward.
// This is process-local protection, not an on-disk save acknowledgement.
class PhantomReturnAttemptGate {
public:
    void Reset() noexcept { requested_ = false; }
    void MarkRequested() noexcept { requested_ = true; }
    [[nodiscard]] bool Requested() const noexcept { return requested_; }
    // B76: a second phantom list may arrive BEFORE the previous void native
    // grant has been observed in the real hunter's own inventory. It must
    // never replace the first/last observations for that pending grant.
    [[nodiscard]] bool MayUpdatePhantomSnapshot() const noexcept {
        return !requested_;
    }
    [[nodiscard]] bool MayRequest(std::size_t missing_items, bool native_ready) const noexcept {
        return missing_items != 0 && native_ready && !requested_;
    }
    [[nodiscard]] bool ObservedInOwnInventory(std::size_t missing_items) const noexcept {
        return missing_items == 0;
    }
    // B78: a subsequent batch must unlock future co-op grants only after
    // its own inventory receipt. Never reset merely because GiveItems was
    // invoked or MapItemMan was available. This is not disk save ACK.
    [[nodiscard]] bool AcknowledgeObservedHome(std::size_t missing_items) noexcept {
        if (missing_items != 0) return false;
        requested_ = false;
        return true;
    }

private:
    bool requested_ = false;
};

class PhantomInventoryScope {
public:
    [[nodiscard]] bool Observe(int slot, std::uint64_t generation) noexcept {
        if (slot_ == slot && generation_ == generation) {
            return false;
        }
        slot_ = slot;
        generation_ = generation;
        return true;
    }

    [[nodiscard]] bool Usable() const noexcept {
        // The real Bloodborne save-slot hook uses userdata0000..userdata0009.
        // Unknown / unsupported slots and missing generation MUST NOT
        // inherit any previous hunter's cached phantom inventory state.
        return ValidSaveCharacterScope(slot_, generation_);
    }

    [[nodiscard]] int Slot() const noexcept { return slot_; }
    [[nodiscard]] std::uint64_t Generation() const noexcept { return generation_; }

private:
    int slot_ = -2; // unobserved, distinct from game value -1 (not loaded)
    std::uint64_t generation_ = 0;
};

} // namespace BloodborneCoop
