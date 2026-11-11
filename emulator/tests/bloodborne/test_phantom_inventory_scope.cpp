#include "core/phantom_inventory_scope.h"

#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>
#include <utility>

using BloodborneCoop::PhantomInventoryScope;
using BloodborneCoop::PhantomReturnMayRetireSnapshot;
using BloodborneCoop::PhantomReturnAttemptGate;
using BloodborneCoop::ValidSaveCharacterScope;

int main() {
    // B80: a rapid rejoin BEFORE any native GiveItems attempt can overwrite
    // the first earned items, not just a post-grant ambiguous receipt.
    using BloodborneCoop::PreserveFirstPhantomOnRejoin;
    assert(!PreserveFirstPhantomOnRejoin(false, false, false, true, false));
    assert(!PreserveFirstPhantomOnRejoin(false, false, true, false, true));
    assert(!PreserveFirstPhantomOnRejoin(false, false, true, true, false));
    assert(PreserveFirstPhantomOnRejoin(false, false, true, true, true));
    assert(PreserveFirstPhantomOnRejoin(false, true, true, true, false));
    assert(PreserveFirstPhantomOnRejoin(true, false, false, false, false));
    assert(PreserveFirstPhantomOnRejoin(true, true, true, true, true));

    // B75: readiness is necessary to request once; native void-return is
    // never a save ACK, so another tick must not repeat an ambiguous grant.
    PhantomReturnAttemptGate receipt;
    assert(!receipt.Requested());
    assert(receipt.MayUpdatePhantomSnapshot()); // first session is observable
    assert(!receipt.MayRequest(1, false));
    assert(receipt.MayRequest(1, true));
    assert(!receipt.MayRequest(0, true));
    assert(receipt.ObservedInOwnInventory(0));
    assert(!receipt.ObservedInOwnInventory(1));
    receipt.MarkRequested();
    assert(receipt.Requested());
    // B76: even a different guest-world phantom list cannot overwrite the
    // old pending grant before an observed own-inventory receipt.
    assert(!receipt.MayUpdatePhantomSnapshot());
    std::vector<std::uint32_t> owed_snapshot{4114, 4000}; // first phantom
    const auto observe_phantom = [&](std::vector<std::uint32_t> new_observation) {
        if (receipt.MayUpdatePhantomSnapshot()) {
            owed_snapshot = std::move(new_observation);
        }
    };
    observe_phantom({4110, 4103}); // new list during pending native grant
    assert((owed_snapshot == std::vector<std::uint32_t>{4114, 4000}));
    assert(!receipt.MayRequest(1, true));
    assert(!receipt.MayRequest(1, false));
    assert(!receipt.ObservedInOwnInventory(1));
    assert(receipt.ObservedInOwnInventory(0));
    // B78: the second phantom return must NOT permanently latch out later
    // sessions after its home inventory is observed to contain all goods.
    assert(!receipt.AcknowledgeObservedHome(1));
    assert(receipt.Requested());
    assert(receipt.AcknowledgeObservedHome(0));
    assert(!receipt.Requested());
    assert(receipt.MayRequest(2, true));
    receipt.MarkRequested();
    assert(!receipt.AcknowledgeObservedHome(1));
    assert(!receipt.MayRequest(2, true));
    assert(receipt.AcknowledgeObservedHome(0));
    assert(receipt.MayUpdatePhantomSnapshot());
    receipt.Reset(); // only after an observed home-inventory match / owner switch
    assert(!receipt.Requested());
    assert(receipt.MayUpdatePhantomSnapshot());
    observe_phantom({4110, 4103}); // owner switched or receipt confirmed
    assert((owed_snapshot == std::vector<std::uint32_t>{4110, 4103}));
    assert(receipt.MayRequest(5, true));

    // B74: while MapItemMan has not yet come back from a scene load,
    // a transition to the own inventory must retain the phantom observations.
    assert(PhantomReturnMayRetireSnapshot(0, false));
    assert(PhantomReturnMayRetireSnapshot(0, true));
    for (std::size_t owed : {1u, 2u, 5u, 256u}) {
        assert(!PhantomReturnMayRetireSnapshot(owed, false));
        assert(PhantomReturnMayRetireSnapshot(owed, true));
    }

    // Delayed rewards and phantom items must accept the exact same 10 slots
    // and reject unknown slot, out-of-range slot, and missing generation.
    for (int slot = 0; slot < 10; ++slot) {
        assert(ValidSaveCharacterScope(slot, 1));
        assert(ValidSaveCharacterScope(slot, UINT64_MAX));
        assert(!ValidSaveCharacterScope(slot, 0));
    }
    for (int slot : {-3, -2, -1, 10, 11, 64}) {
        assert(!ValidSaveCharacterScope(slot, 1));
        assert(!ValidSaveCharacterScope(slot, UINT64_MAX));
    }
    PhantomInventoryScope scope;
    assert(!scope.Usable());
    assert(scope.Observe(-1, 1));
    assert(!scope.Usable());
    assert(!scope.Observe(-1, 1));

    // All retail save slots are independent, no cross-character inheritance.
    for (int slot = 0; slot < 10; ++slot) {
        assert(scope.Observe(slot, 1));
        assert(scope.Usable());
        assert(scope.Slot() == slot);
        assert(scope.Generation() == 1);
        assert(!scope.Observe(slot, 1));
    }
    // Same slot but new character after character lists are forgotten.
    assert(scope.Observe(9, 2));
    assert(scope.Usable());
    assert(!scope.Observe(9, 2));
    assert(scope.Observe(9, UINT64_MAX));
    assert(scope.Usable());

    // Game stopped / unknown slot / unsupported data => reset immediately.
    assert(scope.Observe(-1, UINT64_MAX));
    assert(!scope.Usable());
    assert(scope.Observe(9, UINT64_MAX));
    assert(scope.Usable());
    assert(scope.Observe(10, UINT64_MAX));
    assert(!scope.Usable());
    assert(scope.Observe(0, 0));
    assert(!scope.Usable());
    assert(scope.Observe(0, 3));
    assert(scope.Usable());
    assert(scope.Observe(-2, 0));
    assert(!scope.Usable());

    // A regression in identity comparison could return false when a new
    // hunter occupied the same userdata000N slot, leaking phantom rewards.
    assert(scope.Observe(0, 5));
    assert(scope.Observe(0, 6));
    assert(!scope.Observe(0, 6));
    std::cout << "B69_REAL_GAME_PHANTOM_INVENTORY_SCOPE_PASS\n";
}
