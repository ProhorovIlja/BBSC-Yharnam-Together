# Ultimate B16: diagnose the actual last mile of Windows native client compilation

**Date:** 2026-11-09. B16 is stacked on combined client-and-server [B15 #47](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/47), which includes the full two-parent B14 + server #7/#8 merge and protects current SHAD game-link reconnect behavior. This does **not** make the native game genuinely independent from original PS4 eboot/ELF; it is a game-free compiler diagnostic milestone for the playable BBPort-hosted runtime.

## Why a further diagnostic fix is justified

Three complete native Windows runs of the inherited client compiler have behaved consistently:

- [B14 full-build #42581216035](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42581216035): original large Ninja build stops around `[432/433]` with no `FAILED:` or error line; same Windows runner's incremental retry finishes five remaining steps and links all three EXE paths. Despite two Ninja workers and `-O2 -g0`, main job correctly remains red.
- [B14 staged #42593995727](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42593995727): **every actual Ninja phase** `net`, `gpu`, `final` logs `PASS`, yet the complete `build.sh` returns nonzero **before** `Built ...` and `out/build-mode.txt` are confirmed. The final GPU log ends near `[43/44]` and lacks a normal compiler diagnostic; a diagnostic-only incremental retry then completes remaining C++/archive/link tasks. This makes the source-to-output handoff, executable disappearance/locking, an unexpected Bash exit or a hidden Ninja/OS issue credible possibilities, **not proven causes**.

## Production finalization changes

Inside Windows `bbport/build.sh` only, the new B16 code:
1. Installs a nonzero EXIT trap that reports `WINDOWS_NATIVE_EXIT_PHASE: <phase> rc=<status>` without changing the original code.
2. Emits `WINDOWS_NATIVE_FINALIZATION_BEGIN` once the normal or staged Ninja calls have completed. Checks each original `out/gpu/bb-probe.exe`, `bb-gpu-capabilities.exe`, `bb-play.exe` is nonempty. Missing targets exit **46** with the exact name.
3. Emits an explicit copy marker, attempts the original `cp` exactly once, preserves its real error code and reports `WINDOWS_NATIVE_COPY_FAILED` if it fails. No unbounded retries and no accepting a partial package.
4. Compares all three **copied files byte-for-byte** to the original output with `cmp`, exiting **47** for a mismatch.
5. Only after successful validation writes `out/build-mode.txt` and announces `Built...`, allowing the subsequent real Windows CI to inspect optimized CMake flags and AMD64 PE32+ headers. No test alters any game assets, online protocol or player saves.

The B16 Windows Actions workflow also reports the presence of three native EXEs and the production build-mode file **before** the existing bounded incremental diagnostic retry. This distinguishes a missing output from another type of shell abort without producing giant logs.

## Regression and Windows compiler gate

`tools/ultimate/test_batch_16_windows_finalization.py` extracts the **exact finalization commands from production Bash** and runs them locally against tiny synthetic files in isolated temporary folders. It checks successful source/destination identity, all three missing-file paths, raw exit code 37 from a mocked failing copy, and corrupted copied data rejection with exit 47. No real game binary is created by these tests. Ubuntu CI runs this plus inherited B10/B12/B13/B14 source and C++ fixtures before the expensive Windows compiler.

The existing `.github/workflows/ultimate-native-client-windows.yml` is scoped precisely to the new **six changed B15→B16 files**, instead of running its B13→B14 allowlist on descendant PRs. After that strict source gate passes, Windows 2022 MSYS2 CLANG64 will repeat a **single** full build on the entire B01–B16 source including server #7/#8. The complete PE32+ and CMakeCache checks remain mandatory. If a first build fails, its overall CI stays RED even if an incremental diagnostic completes.

## Still OPEN

- A genuinely green **initial** complete Windows build, rather than a retry or a source-only fixture.
- The B15 separate Docker server 12-suite and simulated 5-hunter QA (not proof of real five-person gameplay).
- Integrated launcher, game assets privately, network version/identity, signed updates, DBNO, boss/NPC/shop world, 2/3/5 real game characters, GPU device-lost/VRAM/p95/p99, crash-consistent reward and save isolation.
- The separate fully **native Windows Bloodborne.exe with no original PS4 ELF/eboot at runtime**.

Fornex, public downloads, account passwords, private Google Drive game files and player saves remain untouched.

## B14 inherited regression adapted

After the B16 source finalization refactor, the previous B14 staged-Ninja fixture still located its loop by the old direct `cp out/gpu/...` anchor. Source CI reported a `ValueError` from that obsolete test selector, not a game/compiler failure. B16 updates the fixture to stop at the new production `bbsc_win_phase=validate-native-outputs` marker. This extra regression file is included in the **six-path B15→B16 diff allowlist**, pinned to its exact Git blob and re-run together with B16's real copy fixtures.
