# Ultimate B71: writer/reader revision cap parity

Date: 2026-11-11. Stacked on [B70 Draft #135](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/135). P0 [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) is **not closed**.

## Defect in the B70 production journal

The reader rejected any revision sequence larger than 32768, because its bounded bitmap contains only 32768 slots, but the writer's `Valid(Revision)` accepted any nonzero 64-bit sequence. After a legitimate full history reached 32768, a normal append at 32769 would be published successfully and then rejected by every future read. This is a self-created permanent recovery block.

## Fix

The writer and reader now share one `MaxRevisions` constant. `Valid` rejects sequence 32769 before any filesystem write. Scan enforces the same maximum. Existing 1…32768 histories remain valid, but no new revision can be written after the limit until a separately designed and verified compaction/rollover transaction exists. There is no silent history truncation or deletion.

A new native regression test validates boundary 32768, rejected gap/32769 writes, absence of accidentally published directories, and fail-closed handling of a synthetic external above-cap revision. This changes the **real portable production header**, not just documentation.

## Validation and remaining gates

The inherited B70 CI builds the exact journal header and executes tests under Linux GCC/Clang and Windows MSVC, plus syntax-checks the actual game-team code. No player files or live servers are accessed. This does **not** wire ledger writes into game save or acknowledge reward grants; the real phantom-earned key item issue remains P0 until durable save acknowledgement and 2–5-client crash/rejoin tests are implemented.

## Global integration findings

On 2026-11-11, the official Yharnam Together repo still has open PRs for in-game party settings (#577), friendly-fire policy (#575), experimental guest trip recovery (#574), Linux port (#571), and server sign-in diagnostic (#559). Visy's Windows port documents VPN/NAT and party improvements, and droogie's bbhost has a separate online stack. They are integration candidates only after interface/protocol/license checks, not blanket merge approvals.
