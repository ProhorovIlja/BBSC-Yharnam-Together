# Ultimate B77: separate in-process reward lane across multiple phantom sessions

2026-11-11. Stacked on [B76 Draft PR #142](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/142). P0 key items [#137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137), unrelated delayed boss/NPC item-lots [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35).

## Source-confirmed B76 limitation

B76 retained `first_look`/`last_look` and suppressed new phantom observations after the native `GiveItems` void-return call became ambiguous, in case an older badge would otherwise be silently lost. But every new joined guest session could earn **additional** goods not seen by the blocked hook. `PhantomKeyItemLedger` from upstream merged #548 already supports merging owed goods when the game swaps between several phantom inventory list pointers, without any disk writes.

## Production B77 integration

The **real** `emulator/src/core/bloodborne_travel.cpp::GiveBackPhantomKeyItems` now maintains two logically independent in-memory lanes:

1. Existing B75/B76 original `phantom_list` + `PhantomReturnAttemptGate` tracks a single ambiguous native grant. The original snapshot is not overwritten, reissued or acknowledged by a different phantom list.
2. `subsequent_phantom_debt` is a separate genuine production `PhantomKeyItemLedger`. While lane 1 awaits an own-inventory receipt, `LookAtPhantom(list, HeldKeyGoods())` records new phantom goods and merges between successive joins; native `OwnKeyItemsForPhantom` suggestions are deliberately not granted during an older ambiguous return. On a real home-list transition, `LookAtOwn` computes outstanding goods but will not authorize a grant or older receipt until the original own-inventory observation resolves.

After lane 1 is confirmed by a later own-list observation, its `phantom_list` and one-shot gate are reset. Lane 2 persists; it can request **one** native void-return goods batch, and holds that debt until a later own-inventory reading shows nothing missing. A third/fourth phantom-list switch during lane 2 is recorded in the same secondary production ledger. If the result is ambiguous, it is **not automatically retried**; only an observed home-inventory match permits `GaveBack`. Both lanes reset immediately when B69's validated save slot/generation changes. A phantom-shaped inventory pointer that survives character-type transition cannot be misidentified as the hunter's own inventory. Each observed list/owed batch is capped to 256 entries; oversized data fails closed.

## Real tests and CI

- `emulator/tests/bloodborne/test_bloodborne_team.cpp`: actual production GTest reproduces three successive phantom list pointers, distinct earned goods, unload pointer ambiguity, later own-list partial/complete observation, and correct newest-first merged debt ordering.
- `tools/re/tests/test_phantom_multisession_ledger.py`: extracts and **compiles/executes actual C++ production methods** from `bloodborne_team.cpp` under both GCC/Clang (synthetic game goods), not reimplemented rules. It also checks the source ordering of both live game callback lanes and no live savedata journal writes.
- `tools/re/tests/test_phantom_return_readiness.py` updated for two-lane B77 source contracts. The inherited B76 CI is updated for the new guard before modifying any old first/last look.
- Dedicated B77 GitHub Actions: source contracts Windows/Linux, actual production ledger executed GCC/Clang, real C++ scope under Windows MSVC, and `-fsyntax-only` of four real game/test translation units using pinned dependencies and generated co-op protobuf.

## Still NOT finished or safe to publish

This protects distinct **in-process** reward observations across repeated sessions. It is **not a disk save acknowledgement**; `PhantomKeyItemLedger` and B68–B73 immutable disk journal are not connected to live game saves. `AddTradeItems` and native GiveItems return void, so even a ready item manager can fail or apply asynchronously. While a grant is ambiguous, new phantom **own-item top-up** is suppressed rather than blindly invoking an unconfirmed native give. Captured item observations can disappear on process exit or confirmed owner change. No stable cross-restart character fingerprint, write-ahead journal/transaction, durable ACK or 2–5 player real-game test; if an item isn't observed in the own list after a grant request the client correctly refuses blind duplicate replay. P0 #137 and #35 stay OPEN. Source syntax, portable tests and bbport PE builds cannot demonstrate live game save persistence. Real player savedata, proprietary CUSA game files, Fornex production server and public release assets untouched.

External upstream monitored for candidate improvements on 2026-11-11: Amanises YT latest 1.4.0 and merged #548, open #577/#575/#574/#571/#559; droogie/bbhost render/mod/input PRs #236/#221/#231/#141; independent visy Windows network/graphics/save work; owner native no-eboot track #84/#89. Runtime ABI, region, licensing and rig performance verification required before adopting their unrelated changes; no claim of exhausting all of GitHub.
