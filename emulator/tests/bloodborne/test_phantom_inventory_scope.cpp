#include "core/phantom_inventory_scope.h"

#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>

using BloodborneCoop::PhantomInventoryScope;

int main() {
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
