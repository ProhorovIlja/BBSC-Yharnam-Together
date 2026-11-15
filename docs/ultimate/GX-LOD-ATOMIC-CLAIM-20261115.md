# Atomic GX LOD slot claims

Adapted from [ayozetr/bloodborne_linux #53](https://github.com/ayozetr/bloodborne_linux/pull/53),
head `156e0d6aee62a7cd1840b385455f7801b3964f1c` (unmerged when rechecked).
The source is GPL-2.0-or-later. Its 93 original loop bytes match the pinned
owner-provided 1.09 image through its actual load segments.

The original loop checks a slot's count against capacity, reads the count again,
then increments it without synchronization. Concurrent workers can receive the
same element or an index past capacity. The imported replacement uses a bounded
`lock cmpxchg`, retries a contested claim and advances past a full slot. It
preserves the registers consumed by the continuation. The actual continuation
overwrites flags with a comparison before its first conditional branch.

The in-place guard is selected by the real BBport preparation patch pipeline,
at any frame rate, only when the full original loop bytes match. This branch's
existing online-event/Quit/Rebirth cave allocation is preserved. Each guard is
checked independently: a mismatched LOD loop does not disable a valid event
guard, and vice versa. The existing segment-layout gate and `BB_CRASH_GUARDS=0`
still apply. The original game image is never edited by these checks.

## Actual machine-code harness

The harness exports original and patched bytes from the production guard module,
maps writable memory and then changes it to executable/read-only, and runs each
loop with platform-ABI wrappers. Success/full continuations capture registers and
return; the harness does not perform the game's subsequent virtual call or load
any game image. The original and replacement have 600 sequential comparisons over
five capacity layouts and first slots 0–4. Two invalid starts are additionally
rejected by the replacement. Pointer/index/count/register relationships and the
preserved r8 sentinel are checked.

Local Linux x86-64, 100,000 rounds, eight simultaneously released workers, four
slots of capacity two (800,000 calls per implementation):

| Observation | Original | Atomic guard |
| --- | ---: | ---: |
| Duplicate claims | 313 | 0 |
| Claims beyond capacity | 24 | 0 |
| Over-capacity slot observations | 23 | 0 |
| Rounds with an overrun observation | 24 | 0 |
| Invalid register relationships | 0 | 0 |
| Missed claims | 0 | 0 |

Counts in the original are nondeterministic. A preceding exploratory run counted
156 duplicates and 36 combined overrun observations; the retained run separates
overrun claims, slots and rounds to avoid conflating them. The protected harness
must have zero errors; reproduction of an original race is a local negative
control, not a flaky CI requirement.

CI runs the actual x86-64 code on Linux/Windows x64, 20,000 rounds each. On an
arm64 runner the machine-code harness explicitly skips (CTest return 77); Python
byte/branch/selection/cave checks still execute. A skip is not macOS native game
validation. The suite collects 15 guard, 73 patch-pipeline and two existing cave
tests; four patch-pipeline tests require retail files and skip without them.

Reproduce with `cmake -S tools/ultimate/lod-tests -B build-lod`, build, then run
`build-lod/lod_claim baseline 100000` and `build-lod/lod_claim patched 100000`
(use the configuration subdirectory and `.exe` on Windows).

## Acceptance boundaries

This is a source integration in the BBport preparation track plus isolated native
loop validation. It is not a new playable no-EBOOT retail profile, a full client
build, a GPU/gameplay test or a real-session crash-rate measurement. The independent
strict prepared-native startup diagnostic does not execute this LOD loop yet.
Other GX crashes, including the separate heap/lock path noted upstream, remain
unresolved. Real-game load/owner lifecycle, device/vendor behavior and long-run
playtests are required before release. No game FPS, latency or server-load claim.
