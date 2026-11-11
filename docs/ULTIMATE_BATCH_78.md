# Ultimate B78: reset native-grant latch on second-lane receipt; align offline journal save slots

Date: 2026-11-11. Stacked on [B77 Draft PR #143](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/143). Relevant [phantom key-item P0 #137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137). Independent delayed boss/NPC native item-lot P0 [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) not addressed here.

## Two production-source mismatches

1. **Second-lane completion deadlocks later joins.** B77's real `emulator/src/core/bloodborne_travel.cpp::GiveBackPhantomKeyItems` reset `subsequent_tracking` and cleared `subsequent_phantom_debt` with `GaveBack()` once the own inventory read back the second-lane reward, but forgot to reset `return_attempt`. The `PhantomReturnAttemptGate` still reported `Requested()==true`; subsequent sessions could enter the blocked secondary path and future grants would not pass `MayRequest`. The path was untested beyond one second-lane receipt.
2. **Disk journal accepted unsupported slots.** The **offline** `emulator/src/core/phantom_key_ledger_file.h` allowed `slot < 64` while the actual runtime inventory and delayed item owner contract requires only `userdata0000..userdata0009` with a nonzero generation. Journal `Valid` and `Decode` therefore accepted nonsensical 10..63 owners. This does not yet affect live saves (journal still offline), but would be dangerous to wire as-is.

## Actual code changes

- `PhantomReturnAttemptGate::AcknowledgeObservedHome(missing_items)` returns false without changing the one-shot latch when any goods remain missing. Only with **zero** missing items does it reset the requested flag and return true. This is a **readback-only** in-process receipt.
- The real second-lane own-inventory branch calls that method *before* `subsequent_phantom_debt.GaveBack()`, clears the in-memory secondary tracking and its diagnostic marker only after a successful home-list observation, and re-opens normal new-phantom observation and grant when appropriate.
- Persistent file journal `Valid` and `Decode` reject slots 10 and above, matching live owner rules. All ten supported 0–9 owners tested, as well as rejected 10, 11, 63, 64, 1024 in encoded, scanned and write paths. The journal still uses a required 32-character lowercase-hex `character_fingerprint`, but **it does not yet know how to derive a trustworthy stable fingerprint from an actual game's savedata.** The runtime's transient character generation cannot substitute for it.
- Native C++ tests require several grant/receipt cycles: a missing item never clears the latch, a complete own-inventory observation clears it, and the next fresh phantom may issue its own one-time grant. Synthetic filesystem tests validate all retail/unsupported slot boundaries.
- Dedicated B78 Windows/Linux CI compiles/runs the actual production C++ journal and policy under MSVC, GCC and Clang, plus source-order regressions. Inherited B77 and B74 CI compile the actual changed game translation units against pinned C++23 dependencies.

## Limits and next durable recovery gate

This is **not a disk savedata acknowledgement**. The current static `character_slot` and `deferred_reward_character_generation` change across new hunters and are not proof of a stable cross-process character identity. No code in this PR writes game savedata or plugs B68–B73 `CreateNewRevision` into the live item-grant hooks; do **not** make such a connection until a source-verified hunter fingerprint and game save outcome/transaction ACK exist. The offline FNV checksum only detects some corruption; it is **not authentication**. Crash/power-loss ordering (fsync and directory metadata), disputed double-grant vs missing item, rejoin during ambiguous second-lane grant, and real 2–5 player game rigs remain unresolved; P0 #137 stays OPEN.

In parallel, continued current public candidate scan: upstream Amanises-Yharnam-Together #548 merged phantom ledger, open #577/#575/#574/#571/#559; independent droogie/bbhost graphics/input/mod candidates #236/#221/#231/#141; separate visy Windows source and owner's native no-eboot AOT PR #84 and save-migration #89. None are bulk-merged without license/ABI validation. No Fornex production, original savedata, private retail Bloodborne files, executable publication, or native no-eboot game completion claimed.
