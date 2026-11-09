# Ultimate B19: fix the actual Windows build exit 127 after all EXEs link

**2026-11-09.** Integration after B18; retains the cumulative B01–B18 client/server source, no additional gameplay or protocol edits. Separate true eboot/ELF-free native PC port remains an equal project.

## Root cause demonstrated in actual Windows logs

[Windows production CI B16 #42598837011](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42598837011) passed **all three real Ninja stages**: `net`, `gpu` and `final`, with nonempty `bb-probe.exe`, `bb-gpu-capabilities.exe`, and `bb-play.exe`. It then failed in the **final output copy command with exit code 127**, phase `copy-native-outputs`. Its `wc -c` byte count fields were also blank. All these commands came from `bbport/build.sh`: `wc`, `cp`, `cmp` are **not guaranteed to exist** on minimally installed MSYS2 CLANG64 Github Actions runners. This is no longer a speculative out-of-memory or Ninja failure: actual linker outputs were present and the logged failing phase and code are known.

## Production fix: already-required CMake, not extra Unix utilities

- `[[ -s file ]]`, a built-in Bash test, continues to reject any missing/empty linker output.
- `cmake -E copy_if_different src1 src2 src3 out/` replaces `cp` and preserves the original `WINDOWS_NATIVE_COPY_FAILED: rc=N` fatal path.
- `cmake -E compare_files src dest` replaces `cmp -s` for each EXE, preserving the original `WINDOWS_NATIVE_COPIED_OUTPUT_MISMATCH` error and no early write of `out/build-mode.txt`.
- A source-ready message replaces `wc -c`. CMake was *already required* for the earlier Windows CMake/Ninja configure stage and no extra package or dependency is introduced.
- The official CMake `-E` CLI documents multi-input `copy_if_different` and `compare_files`, supported even by older CMake 3.x. No server/client gameplay source, DLL copy/deployment, account, world/save, network packet or renderer code changed.

## Real tests and gates

- Update `tools/ultimate/test_batch_16_windows_finalization.py` to extract the **new production Bash finalization** verbatim, compile-independent, and test real `cmake -E` copying/byte comparison of three synthetic EXE placeholders. Preserve distinct missing target (46), forced CMake copy failure (37), post-copy corruption (47) error statuses. Verify it works when `cp`, `wc`, and `cmp` functions explicitly fail with 127.
- Exact **five-file B18→B19** changed-path and source-blob CI gate, inherited B10 linker, B12 co-op data, B13 Insight and B14 Ninja staging fixture. It uses **real Windows 2022 MSYS2 CLANG64** to compile the entire accumulated client and check all three actual PE32+ AMD64 headers, both CMake `-O2 -g0` cache flags and production mode from a **clean first pass**.
- A failed first build still exits red, even if an incremental retry later links or copies files; B19 cannot be promoted simply because output files were eventually present.

## Release boundaries

This is a game-free **actual compiled runtime** gate, not playable Bloodborne 1.09 with private CUSA03173 assets or the independent native no-ELF port. It does not validate GPU quality, cross-network latency, 5 real hunters, DBNO/invasions, mods, saves, linked server release, signed launcher update/installer or all screenshot Issues. No private files, accounts, Fornex service restarts, binary uploads or public releases. Draft PR only.
