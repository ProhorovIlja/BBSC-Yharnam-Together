# Ultimate B72: one owner-validation contract for phantom inventory and delayed awards

Date: 2026-11-11. Stacked on [B71 #136](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/136). Distinguish [Issue #35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) (deferred boss/NPC item lots) from new [Issue #137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137) (phantom-earned keys across restart).

## Real issue found in live reward code

`emulator/src/core/bloodborne_travel.cpp::GiveBackPhantomKeyItems` already used B69 `PhantomInventoryScope::Usable`, which accepts only retail savedata slots 0–9 and a nonzero character generation. In contrast, the real production deferred boss/NPC reward code `bloodborne_flags_store.cpp` accepted *any nonnegative* slot even if out of retail bounds (10+) or generation zero. Queue producers, delayed consumers and NPC death-drop dedup therefore disagreed on whether the current game state represented a known hunter.

## Source changes

- `phantom_inventory_scope.h` now declares `ValidSaveCharacterScope(slot,generation)`. The existing live phantom inventory guard calls that **same** helper.
- `DeferredRewardOwner::Valid` calls it too. The real `HoldGuestBossItem`, `QueueGuestNpcGift`, `GiveDueNpcGifts`, `GiveDeferredBossItems` and `RefreshNpcDeathDropLedger` paths use this validation. Invalid slots/generations cannot own new deferred reward queues or be consumers of previously queued items; no new save-path or server action.
- The existing *source-extracted production owner* regression fixture was updated to include the shared header and exercise slot -1, slot 10 and generation zero (as well as valid 0 and 9). The B69 portable identity test now checks every retail slot 0–9, unknown/invalid slots and missing generation.

## Tests / safety

Dedicated `.github/workflows/ultimate-batch-72-reward-identity.yml` executes source contracts on Windows/Linux, extracted source owner/evictor logic under Linux GCC, and actual shared C++20 header under MSVC Windows and GCC/Clang Linux. A cumulative native Windows client build will verify the full production translation units separately. **Neither** a portable policy test nor a successful build proves game drops actually persisted. No live game inventory, player saves, Fornex or server deployments are modified.

The P0 phantom-key issue #137 remains open: current game callback lacks verified durable per-character sidecar, safe write-before-grant, explicit save acknowledgment, crash/power-loss transaction semantics and real 2–5-client verification. Owner validation is a necessary gate, **not** the fix for restart losses.

## New source intake snapshot

Rechecked the original [Yharnam Together](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together) open PRs #577 (in-game party settings), #575 (friendly fire), #574 (experimental guest trips), #571 (Linux build) and #559 (server sign-in diagnostics), plus our [Windows port #89](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/89), [#84](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/84) and the separate [visy Windows port](https://github.com/visy/bloodborne_pc_windows_port). These are not automatically protocol-compatible. Keep testing licenses, networking, render performance and independent no-eboot-native requirements before adopting code. No claim to have searched literally every online repo.
