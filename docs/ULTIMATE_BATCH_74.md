# Ultimate B74: don't lose phantom-earned goods while item manager is unavailable

Date: 2026-11-11. Stacked on [B73 #139](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/139), [P0 phantom key bug #137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137). Do not confuse this with deferred native item-lots [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35).

## Verified real-game failure path

In `emulator/src/core/bloodborne_travel.cpp::GiveBackPhantomKeyItems`, on a non-phantom player with a newly returned own inventory list the code immediately executed `phantom_list = 0` and called `AddTradeItems(..., ItemPopup::Silent)` for earned goods. However the implementation of `AddTradeItems` in the **actual** `emulator/src/core/bloodborne_trade.cpp` returns immediately if `trade_sites` is not installed; later the nested native GiveItems path skips the grant if `HasVtable(MapItemMan)` is false during loading (logs an error but function returns `void`). The phantom observation was erased either way, so an item that disappeared from a phantom list could have no further in-memory recovery attempt. This is source-established; not proven to explain a particular historical save loss.

## Actual live code changes

- `TradeItemsReadyToGive()` on the real trading runtime checks both `trade_sites.load()` and the native `MapItemMan` vtable used by GiveItems. Does not mutate the game.
- `GiveBackPhantomKeyItems` refuses a null inventory list (`KeyItemList()==0`) while loading. At transition to own list, computes current missing phantom-earned goods, and calls `PhantomReturnMayRetireSnapshot` **before** clearing the old phantom pointer. If goods remain and native give is unavailable, leaves `phantom_list, first_look, last_look` untouched and retries on later game-thread ticks. If no goods remain, avoids unnecessary manager probing. If ready, proceeds with the pre-existing give routine.
- Log wording changes from `gave back` to `requested return`, because a native void-return item grant and vtable readiness do not prove the player's save has persisted.
- New standalone `PhantomReturnMayRetireSnapshot` C++20 tests cover zero items vs outstanding items when the give path is ready/unready. Production-function extracted C++ tests verify that missing trading hooks, null manager and failed native vtable fail closed; readiness succeeds only with both sites and manager. CI compiles/runs actual scope header under Linux GCC/Clang and Windows MSVC. Cumulative Windows client build is required to validate actual linking.

## Remaining P0 / no misleading completion claim

This **only** prevents one premature in-process discard. If the game exits before a valid return, B68–B73 persistent file journal remains **offline and unwired**: no durable hunter fingerprint, journal write before game grants, save ACK, sync/fsync, safe transaction or full five-hunter game rigs. Even after `TradeItemsReadyToGive` is true, the real native GiveItems returns `void`; the game can still decline a grant for other reasons. Never issue blind repeated grants without a receipt/dedup mechanism. Requires game 1.09 real unit/party tests and regional save validation. No live game save, Fornex, proprietary game files, deployed server, website, or public executable changed.

## Cross-project source review

Official [Yharnam Together v1.4.0](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/releases) remains the latest published release, while its merged [#548](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/548) integrates a per-slot debt file for restart recovery but currently lacks Ultimate's durable identity and strict transaction gates. Open YT [#438](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/438) has a useful server-side reward mailbox ACK durability proposal, not a guest-local save ACK. Independent [droogie/bbhost](https://github.com/droogie/bbhost) open PRs #236 graphics, #221 mod menu, #231 controller glyphs, #141 render performance remain candidates requiring measured/compatible integration. Independent [visy/bloodborne_pc_windows_port](https://github.com/visy/bloodborne_pc_windows_port) 0.8 series and its enemy drop/guest key-item experiments require game rig and licensing validation. Do not claim exhaustive global incorporation.
