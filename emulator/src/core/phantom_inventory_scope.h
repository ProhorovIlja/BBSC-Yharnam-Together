// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// B69: slot-scoped, game-thread-only key-item observer identity. A phantom's
// inventory pointer and first/last observations are ONLY valid for the exact
// character generation and save slot that created them. This guard does not
// access a real save, session or network. The returned "changed" signal
// directs the real game hook to clear its cached observations immediately.
#include <cstdint>

namespace BloodborneCoop {

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
        return slot_ >= 0 && slot_ < 10 && generation_ != 0;
    }

    [[nodiscard]] int Slot() const noexcept { return slot_; }
    [[nodiscard]] std::uint64_t Generation() const noexcept { return generation_; }

private:
    int slot_ = -2; // unobserved, distinct from game value -1 (not loaded)
    std::uint64_t generation_ = 0;
};

} // namespace BloodborneCoop
