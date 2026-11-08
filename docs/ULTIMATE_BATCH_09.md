# Ultimate B09: test savedata metadata source against real Windows C++ runtime

B06–B08 repaired three independent defects in **guest-world co-op metadata**: unsafe truncation on a failed file write, stale queued snapshots overwriting newer data and lack of a bounded retry after a failed latest write. Previous CI compiled their exact source helpers **on Linux only**. That is not proof that file replacement, executable spawning or error paths work under Windows, the game's target OS.

## Change

The existing B06, B07 and B08 Python regression harnesses now use platform-native process headers and suffix their temporary synthetic C++ executables with `.exe` on Windows. They also detect `clang++` without assuming `g++` exists. The actual production C++ of B08 is **unchanged and blob-pinned**.

Dedicated GitHub Actions [B09 workflow](../.github/workflows/ultimate-batch-09-windows-savedata-faults.yml) builds and executes these **same production C++ helper fixtures** both on Ubuntu 24.04 and Windows 2022 MSYS2 CLANG64. Tests synthesize normal file replacement, empty file replacement, failed path and blocked rename, stale snapshots, independent slot identities and eventual recovery with exponential retry. The workflow guards the seven-file B08→B09 delta against accidental server/client/game-asset or personal-save changes and validates exact three test source blob hashes.

## Important limits

A Windows GitHub Actions fixture can confirm Windows semantics for these small helper functions but **cannot** validate Bloodborne's actual encrypted savedata, ownership of a player's personal world, antivirus locking on end-user machines, concurrent writer shutdown, `fsync`/power-loss durability, GPU renderer, launcher UX, server or five-hunter Link4 sessions. No game files or account details are used.

Windows full client linker blocker [PR #31](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/31) is a separate compilation milestone currently being investigated. B09 does not recompile the entire engine or make an installer. Keep issues [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) and [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) open, preserve the user's live Fornex and real saves, and promote no package without private real-game verification.
