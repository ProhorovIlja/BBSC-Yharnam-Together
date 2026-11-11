# Ultimate B73: bounded exact-size reads for phantom item recovery journals

Date: 2026-11-11. Stacked on [B72 Draft #138](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/138). Tracks distinct [phantom key item restart issue #137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137), not the delayed item-lot [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35).

## Defect in the actual production offline journal

The B68–B72 `phantom_key_ledger_file.h::ReadReady` first checks `file_size() <= 70 KiB`, then reads the **entire** stream using `std::istreambuf_iterator` into an unbounded `std::string`. An external process or corrupting file writer could append after the size check but before reading; the actual bytes read would exceed the expected cap and allocate uncontrolled memory. `CreateNewRevision` also used an unbounded iterator stream when re-reading its freshly written `.pending` file. Cooperative `.writer.lock` does not protect against non-cooperative filesystem changes.

## Production fix

- Define `MaxRecordBytes = 70 * 1024` once, share between `Decode` and file read.
- New `detail::ReadExactRecord(std::istream&, expected)` enforces the upper bound **before** allocation, reads exactly `expected` bytes, rejects truncated/error streams and rejects any trailing byte (file growth). No `std::istreambuf_iterator` remains in the production header.
- Use the bounded helper in both `ReadReady` and `CreateNewRevision` pending-record verification. Fail closed without overwriting or deleting existing `.ready` revisions.
- Run synthetic deterministic tests on exact-size, grown, shrunk, oversized expected lengths and an on-disk >70KiB malformed `.ready` record. Earlier monotonic, lock, invalid-identity, same-slot and corruption tests remain.

## Verification and limitations

`.github/workflows/ultimate-batch-73-bounded-ledger.yml` executes source contracts on Windows/Linux and compiles/runs this **exact C++20 production header** with Windows MSVC and Linux GCC/Clang. Parent B68/B70 workflows also re-run when the same header/test changes. This protects allocations during a size-check/read race; it is **not** a portable atomic snapshot or guarantee against simultaneous adversarial edits. `FNV-1a` checksum is not authenticated. Still **no live game save acknowledgement** or durable on-disk journal integration; OS fsync/power-loss ordering, hunter fingerprint identity, item grant outcome and real 2–5 player crash/restart rigs remain P0.

## External source triage

Rechecked current upstream [Yharnam Together v1.4.0](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/releases) and merged [PR #548](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/548): upstream deliberately persisted a per-slot phantom debt file after a guest restart, but Ultimate must not copy its truncate/lenient parse without strict transaction protection. The official [PR #438](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/438) separately explores **server reward mailbox** synchronous ordering; its server-side ACK is not a substitute for game-side save acknowledgement. Public BBPort updates include rendering/streaming fixes, but those must be compared with native network/graphics contracts and license before adaptation. The branch changes no production Fornex service, network protocol, private save, game image or proprietary asset.
