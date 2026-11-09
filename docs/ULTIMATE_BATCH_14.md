# Ultimate B14: one cumulative Windows runtime compilation milestone

**Scope:** B01–B13 playable-client source + latest Windows build diagnostics from Draft #31, on the next stacked B14 branch. This is a **game-free native Windows compiler test for the current BBPort-hosted runtime**, not a full standalone no-PS4-ELF Bloodborne PC game. No launcher installer, client/server package, release or Fornex deployment is triggered.

## Evidence and issue carried forward

A GitHub two-way comparison between `experiment/ultimate-batch-13-insight-character-ownership-20261109` and `experiment/ultimate-windows-native-client-build-20261108` reported **diverged: 125 commits on the cumulative side, two newer commits on the separate Windows CI branch**. Those two Windows commits only updated `.github/workflows/ultimate-native-client-windows.yml`. B14 carries its exact bounded-diagnostic workflow revision forward, then replaces its obsolete PR31-only source gate with the actual **B13→B14 six-file** source boundary, keeping B01–B13 production fixes untouched.

Prior [#31 Windows job 42519991833](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42519991833) had a failed initial 433-target Ninja build but a **successful incremental link retry** in the same runner, producing all three target paths `bb-probe.exe`, `bb-gpu-capabilities.exe`, `bb-play.exe`. That job correctly remained FAILED, and the first-build cause was not proved. The prior successful native Windows [YT 1.3 reference CI 41051781140](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41051781140) limited Ninja to two workers and compiled RelWithDebInfo with `-O2 -g0`, avoiding large debug-info link memory. These are directly comparable known resource choices, **not a claim that the problem was proven to be memory exhaustion**.

## B14 production build.sh controls

- New opt-in `BB_BUILD_JOBS` (1..32, invalid values fail closed) passes `-j N` to the **actual direct Ninja invocation**, not merely an ineffective CMake environment variable or Bash function exported across a nested process.
- New opt-in `BB_WINDOWS_NO_DEBUG_SYMBOLS=1` passes `-DCMAKE_C_FLAGS_RELWITHDEBINFO=-O2 -g0 -DNDEBUG` and matching C++ flag to CMake on Windows; default developer builds retain their old debuggable flags. `-O2` and NDEBUG are the same optimized-mode semantics.
- B10's bounded, always-explicit Ninja failure helper remains in the real `bbport/build.sh`. B14 restricts the **old B10-specific B09→B10 exact whitelist** to its own original PR, avoiding false red checks on cumulative integration, with B14's separate strict source gate maintained.
- No gameplay protocol, drawing code, achievements, rewards, world persistence, private saves or original PS4 game files changed in B14.

## Source and Windows CI gates

The updated `.github/workflows/ultimate-native-client-windows.yml` first runs a **Linux source-fixtures** job, pins actual B14 production build shell and test Git blobs, checks only six exact changed paths, runs `bash -n`, then executes the real resource-control shell selection, B10 build failure reporter, B12 exact-identity join and B13 per-hunter boss Insight C++ fixtures.

Only after that first job passes, a **real Windows 2022 MSYS2 CLANG64** runner installs pinned-by-repository submodule SHAs and standard toolchain packages, runs the full `bbport/build.sh` production build with two Ninja jobs and low-debug-info mode, and checks: `out/build-mode.txt` production, actual C/C++ CMake cache flags `-O2 -g0 -DNDEBUG`, three nonempty Windows executables, DOS MZ and full PE header **AMD64/PE32+** identity and their SHA256. No copyrighted game payload or binary artifacts are uploaded. If the initial build fails, it prints bounded diagnostics and tries one limited incremental compilation on the same runner **but intentionally keeps the CI RED even if the retry completes**. A clean first-run or properly explained and fixed source error is needed before a green integrated compiler milestone.

## Honest remaining work

This Windows compilation combines *source* accumulated B01–B13 with latest #31 diagnostics. It does **not** validate that any of the private Bloodborne 1.09 assets, shaders or executable gameplay are correct. No game can be played from these three diagnostic EXE paths alone. Runtime validation still requires the exact linked five-player server, signed/verified launcher update pipeline, 2/3/5-player gameplay, renderer hardware/VRAM/fps p95/p99, correct NPC/shop/boss/reward/save logic, TLS, mods, NAT/invasion/session flow and CUSA03173 private game assets under authorization. Nor does it satisfy the independent **truly native, no PS4 eboot/ELF at runtime** PC port mission.

**Do not release a package or restart live Fornex until actual binary and user-save, game/transport and security gates are satisfied.**
