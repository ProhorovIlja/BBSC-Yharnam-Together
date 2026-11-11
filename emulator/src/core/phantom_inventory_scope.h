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
