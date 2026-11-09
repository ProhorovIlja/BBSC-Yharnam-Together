# Ultimate B14: one cumulative Windows runtime compilation milestone

**Scope:** B01–B13 playable-client source + latest Windows build diagnostics from Draft #31, on the next stacked B14 branch. This is a **game-free native Windows compiler test for the current BBPort-hosted runtime**, not a full standalone no-PS4-ELF Bloodborne PC game. No launcher installer, client/server package, release or Fornex deployment is triggered.

## Evidence and issue carried forward

A GitHub two-way comparison between `experiment/ultimate-batch-13-insight-character-ownership-20261109` and `experiment/ultimate-windows-native-client-build-20261108` reported **diverged: 125 commits on the cumulative side, two newer commits on the separate Windows CI branch**. Those two Windows commits only updated `.github/workflows/ultimate-native-client-windows.yml`. B14 carries its exact bounded-diagnostic workflow revision forward, then replaces its obsolete PR31-only source gate with the actual **B13→B14 seven-file** source boundary, keeping B01–B13 production fixes untouched.

Prior [#31 Windows job 42519991833](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42519991833) had a failed initial 433-target Ninja build but a **successful incremental link retry** in the same runner, producing all three target paths `bb-probe.exe`, `bb-gpu-capabilities.exe`, `bb-play.exe`. That job correctly remained FAILED, and the first-build cause was not proved. The prior successful native Windows [YT 1.3 reference CI 41051781140](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41051781140) limited Ninja to two workers and compiled RelWithDebInfo with `-O2 -g0`, avoiding large debug-info link memory. These are directly comparable known resource choices, **not a claim that the problem was proven to be memory exhaustion**.

## B14 production build.sh controls

- New opt-in `BB_BUILD_JOBS` (1..32, invalid values fail closed) passes `-j N` to the **actual direct Ninja invocation**, not merely an ineffective CMake environment variable or Bash function exported across a nested process.
- New opt-in `BB_WINDOWS_NO_DEBUG_SYMBOLS=1` passes `-DCMAKE_C_FLAGS_RELWITHDEBINFO=-O2 -g0 -DNDEBUG` and matching C++ flag to CMake on Windows; default developer builds retain their old debuggable flags. `-O2` and NDEBUG are the same optimized-mode semantics.
- B10's bounded, always-explicit Ninja failure helper remains in the real `bbport/build.sh`. B14 restricts the **old B10-specific B09→B10 exact whitelist** to its own original PR, avoiding false red checks on cumulative integration, with B14's separate strict source gate maintained.
- No gameplay protocol, drawing code, achievements, rewards, world persistence, private saves or original PS4 game files changed in B14.

## Source and Windows CI gates

The updated `.github/workflows/ultimate-native-client-windows.yml` first runs a **Linux source-fixtures** job, pins actual B14 production build shell and test Git blobs, checks only seven exact changed paths, runs `bash -n`, then executes the real resource-control shell selection, B10 build failure reporter, B12 exact-identity join and B13 per-hunter boss Insight C++ fixtures.

Only after that first job passes, a **real Windows 2022 MSYS2 CLANG64** runner installs pinned-by-repository submodule SHAs and standard toolchain packages, runs the full `bbport/build.sh` production build with two Ninja jobs and low-debug-info mode, and checks: `out/build-mode.txt` production, actual C/C++ CMake cache flags `-O2 -g0 -DNDEBUG`, three nonempty Windows executables, DOS MZ and full PE header **AMD64/PE32+** identity and their SHA256. No copyrighted game payload or binary artifacts are uploaded. If the initial build fails, it prints bounded diagnostics and tries one limited incremental compilation on the same runner **but intentionally keeps the CI RED even if the retry completes**. A clean first-run or properly explained and fixed source error is needed before a green integrated compiler milestone.

## Honest remaining work

This Windows compilation combines *source* accumulated B01–B13 with latest #31 diagnostics. It does **not** validate that any of the private Bloodborne 1.09 assets, shaders or executable gameplay are correct. No game can be played from these three diagnostic EXE paths alone. Runtime validation still requires the exact linked five-player server, signed/verified launcher update pipeline, 2/3/5-player gameplay, renderer hardware/VRAM/fps p95/p99, correct NPC/shop/boss/reward/save logic, TLS, mods, NAT/invasion/session flow and CUSA03173 private game assets under authorization. Nor does it satisfy the independent **truly native, no PS4 eboot/ELF at runtime** PC port mission.

**Do not release a package or restart live Fornex until actual binary and user-save, game/transport and security gates are satisfied.**

## B10 regression adaptation after changing the real Ninja invocation

The first B14 source CI correctly validated the new resource options, then exposed a brittle B10 source test that located the Windows error handler by an exact text literal `ninja -C`. Since the **production** build now invokes `ninja -j 2 -C` via an optional argument array, this old string-match test raised `IndexError` even though the error reporter and all other selection tests still passed. B14 changes `tools/ultimate/test_batch_10_build_failure.py` to locate the Windows error branch by its real `bb-probe bb-gpu-capabilities bb-play` target list and check the still-preserved `report_bbport_build_failure` call and exit 1. The source boundary now enumerates **seven** exact B13→B14 paths including this adapter; the original B10 branch remains untouched.

## Second Windows attempt: separate the expensive compilation phases (2026-11-09)

[Actual Windows run 42581216035](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42581216035) completed with **source-fixtures SUCCESS / build-engine FAILURE**. On the full 433-task build, the first Ninja invocation returned a nonzero exit after progress `[432/433]` without a visible `FAILED:` or compiler error. The diagnostic-only incremental `ninja -j 2 -v` retry successfully completed the remaining five steps in roughly ten seconds, including rebuilding `libbbnet.a` and linking `bb-probe.exe`, and confirmed all three target EXE paths. **CI remained correctly red.** This persisted after actual `-j 2` and low-debug-info `-O2 -g0`, so memory pressure is only one hypothesis, not a confirmed cause.

B14 now adds an **opt-in** `BB_WINDOWS_STAGED_LINK=1` to the actual `bbport/build.sh` Windows CLANG64 path. The Windows CI opts in, building exactly these ordered stages with two Ninja workers:

1. `bbnet`: protobuf, emulator networking, real co-op C++, guest world and savedata integration, `libbbnet.a`
2. `bbgpu`: graphics/Vulkan renderer and network dependency, without final executable links competing with large translation units
3. `bb-probe bb-gpu-capabilities bb-play`: final PE32+ executable link targets

Each step reports `WINDOWS_NINJA_STAGE_BEGIN` and `_PASS`, or `_FAILED: <stage> rc=<original code>` followed by the real B10 bounded failure reporter. A failing stage **preserves its exact raw Ninja shell code** and stops the build rather than masking failure with a later retry. The normal developer Windows path retains its original one-Ninja-command behavior when opt-in is absent.

`tools/ultimate/test_batch_14_windows_native_resources.py` now runs **the actual production staged Bash control flow**, replacing only the external Ninja invocation with a fake that records targets. Its tests verify the exact stage ordering and simulate failure in network, graphics and final PE phases with three different exit codes. The code is thereby verified independently from the much longer real Windows compiler run.

This makes the first-build failure **localizable** and prevents competing terminal links; it does not prove the root cause of prior silent Ninja exits. No standalone game package, real-game launch or 2/3/5-player network session may be claimed until their separate gates pass.
