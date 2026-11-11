# Ultimate B76: retain unresolved phantom key-item receipt across new co-op list

Date: 2026-11-11. Based on [B75 Draft #141](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/141), P0 [guest phantom key items lost after restart #137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137). Separate delayed native reward problem [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35).

## Real source defect

B75 retains `phantom_list`, `first_look` and `last_look` after issuing a single native `AddTradeItems` request until the hunter's own inventory is observed to contain the owed goods. But the **same live game hook**, `emulator/src/core/bloodborne_travel.cpp::GiveBackPhantomKeyItems`, enters its `PhantomType` branch if a guest immediately rejoins. That branch writes `last_look = HeldKeyGoods()` *before* comparing pointers, and, for a new list, overwrites `phantom_list` and `first_look`. A pending unacknowledged reward from the old phantom list could therefore be silently replaced with an unrelated fresh list, losing the only in-process evidence even with B75's grant-once latch.

## B76 actual game changes

- Extend production `PhantomReturnAttemptGate::MayUpdatePhantomSnapshot()`: return false during an unacknowledged native item grant.
- In the **real** `GiveBackPhantomKeyItems` game-thread `PhantomType` branch, check the grant gate **before** any `last_look`, `first_look` or `phantom_list` mutation. When an older grant is ambiguous, retain its entire old phantom observation and return without replacing it, regardless of whether the current phantom list has same/different pointer.
- Warn once per newly observed blocked phantom-list pointer, rather than spamming a warning every 250 ms; reset the warning marker on slot/generation switch or a confirmed home inventory match. No automatic second grant.
- Native C++20 policy tests simulate old phantom goods `{4114,4000}` and a newly joined phantom's different goods `{4110,4103}`; prove that the old goods remain frozen while a grant request is pending and that a newly observed phantom list is accepted again after an explicit owner reset or receipt.
- Existing extracted real C++ grant readiness tests and source-order regressions assert guard happens before `HeldKeyGoods()` and `phantom_list = list`. Inherited B74 CI compiles the actual full game `bloodborne_trade.cpp` and `bloodborne_travel.cpp` translation units against pinned `spdlog`/`fmt` and generated proto, while dedicated B76 CI tests C++20 under Windows MSVC and Linux GCC/Clang.

## Limitations — no premature P0 resolution

**This mitigation does not monitor new phantom-earned items** during a new co-op session while an earlier grant is pending. That is an intentional fail-closed freeze; completing safe multi-session accumulation requires a real per-character durable debt state machine, collision-safe stable hunter identity, a write-before-grant journal, an authenticated/validated local save acknowledgement, and crash/restart/multiplayer rigs. An own-inventory read **does not prove** the game has written its savedata to disk. If the game's void-return grant failed, this patch prevents duplicate retries but cannot repair the grant automatically. We cannot call #137 fixed or publish a stable client.

The user has explicitly requested best-of-ecosystem improvements, no repeated premature builds or Fornex deployment, non-destructive save handling, and a **separate** truly native independent no-eboot PC port. Checked public upstream YT #548 key debt, open #577/#575/#574 and independent droogie/bbhost #236/#221/#231/#141 plus visy network/save fork for compatibility opportunities. No blind copy from incompatible branches, no claim of comprehensive GitHub exhaustion or completed native port. Real savedata, private Bloodborne dump, production Fornex services and published binaries untouched.
