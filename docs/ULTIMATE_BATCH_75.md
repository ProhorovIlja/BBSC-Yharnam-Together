# Ultimate B75: one-shot phantom key-item returns until observed in own inventory

Date: 2026-11-11. Stacked on [B74 Draft #140](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/140); scoped to [P0 #137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137), distinct from deferred item-lots [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35).

## Source-established second failure window

B74 delayed a phantom key-item return until `MapItemMan` and trade hooks are ready, but then still did `phantom_list = 0` **before** `AddTradeItems(...)`. The native `GiveItems` exposed through the trade hook returns `void`; successful vtable readiness is not proof the inventory changed, and a later tick could not verify a successful grant because the in-memory phantom snapshot had been discarded. Conversely, retrying an ambiguous `void` call blindly can duplicate a badge/tool if the game applied it asynchronously.

## Changes in real live game source

- `emulator/src/core/phantom_inventory_scope.h`: a small pure `PhantomReturnAttemptGate` records whether a return was requested in this owner scope. A nonzero missing count may be issued **once only** when native grant path is ready. After a request, the same snapshot cannot be reissued, even if it still appears missing on the next frame.
- `emulator/src/core/bloodborne_travel.cpp::GiveBackPhantomKeyItems`: keep `phantom_list` and the original phantom observations across the native give request. Latch `MarkRequested` **before** invoking each native item call. Recompute `PhantomKeyItemsToGiveBack(..., HeldKeyGoods())` on later own-inventory reads; only reset the phantom pointer when `to_return.empty()`, meaning no phantom-earned goods are missing from the observed home list. Reset the attempt state on confirmed slot or character-generation change; do not grant another hunter's pending items.
- Explicit ambiguity policy: if a native void-return grant was attempted but the own inventory still lacks goods, **do not automatically retry**. The snapshot remains in memory as pending instead of vanishing; diagnosis/manual recovery and a durable journal are still needed.
- B74 guard remains: unknown inventory list, unavailable manager or missing trading hooks do not trigger a grant.
- Add C++20 tests of one-shot grant, no blind replay, readback-based completion, reset on owner change, every retail slot 0–9 and invalid generation. Extend the source-exacted real `bloodborne_trade.cpp` grant readiness test with ordering assertions in live callback.

## CI and remaining blockers

`.github/workflows/ultimate-batch-75-phantom-grant-observation.yml` runs exact game callback source contracts on Windows/Linux, production trade readiness extraction on Linux, and the portable policy C++20 tests on Windows MSVC and GCC/Clang Linux. Inherited B74 workflow must also compile the actual modified `bloodborne_travel.cpp` and `bloodborne_trade.cpp` C++23 translation units using pinned dependencies and generated protocol. Scope: syntax/API + portable tests, **not a savedata acknowledgement**, not a Windows game build, no real party gameplay.

IMPORTANT: This is an **in-process** observation of the guest's own list, not durable evidence that the game saved its inventory. It cannot guarantee recovery after a process crash between an issued grant and the game's save. It also cannot safely resolve multiple phantom-list transitions while a previous grant remains ambiguous, and changes to other game's inventory hooks may require further safeguards. Stable hunter identity, write-before-grant disk transactions, fsync/rename, ACK ordering, no-duplicate crash replay, actual CUSA 1.09 2/3/5-client game rigs remain open in #137. No Fornex, real saves, proprietary game assets or public release files modified.

## 2026-11-11 whole-ecosystem candidate review

Rechecked official Yharnam Together PR #548 (merged phantom-key debt), open PRs #577/#575/#574/#571/#559, independent droogie/bbhost render and input/mod fixes (#236/#221/#231/#141), and visy/bloodborne_pc_windows_port 0.8.0 guest/host save separation, direct networking and mod compatibility. Each is a candidate, not automatically safe to merge; the independent visy project calls its own runtime a native Windows port but still requires decrypted retail game files, so it does **not** establish the separately requested fully rebuilt executable independent of eboot. Licensing and ABI remain integration gates.
