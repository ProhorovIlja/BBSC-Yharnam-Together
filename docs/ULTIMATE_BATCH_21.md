# Ultimate B21: fail-closed Win64 runtime DLL closure before release packaging

**Milestone:** after B19's real Windows 2022 CLANG64 compiler/PE32+ SUCCESS and B20's release-only Docker CI. This is a **packaging/runtime-readiness fix** atop the same cumulative B01–B20 client+server tree, not a new native engine recompile, downloadable release, or proof of actual game launch.

## Why a successful EXE build is not yet a Windows release

[Actual B19 Windows Actions 42602734451](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42602734451) finished successfully: `bbnet`, `bbgpu`, `final` all PASS; `bb-probe.exe`, `bb-gpu-capabilities.exe`, `bb-play.exe` copied and verified as AMD64 PE32+ with SHA256, mode=production. No game payloads were used. However `bbport/packaging/windows/package.sh` relies on initial `ldd` output and a second single scan of the staged DLLs to copy CLANG64 runtime dependencies. It does **not** previously impose a transitive, exhaustive, fail-closed check of all package-time PE imports. A compiled EXE can therefore be correct yet a clean Windows installation may fail at load time when a nested non-system DLL was missed. The point is a **prevention gap**, not a proved missing DLL in an existing released ZIP.

Microsoft [vcpkg applocal.ps1](https://github.com/microsoft/vcpkg/blob/master/scripts/buildsystems/msbuild/applocal.ps1) already follows a comparable PE `llvm-objdump`/local dependency deployment pattern. The official [MSYS2 CLANG64 LLVM package](https://packages.msys2.org/packages/mingw-w64-clang-x86_64-llvm?repo=clang64) is part of the native LLVM toolchain.

## Production source changes

- New `bbport/packaging/windows/verify_runtime_dlls.py` uses only Python standard library and LLVM `llvm-objdump -p` already installed in the CLANG64 toolchain; it parses `DLL Name: ...` static PE imports.
- Starting from staged `bb-probe.exe`, `bb-gpu-capabilities.exe` and the launch trampoline `Bloodborne.exe`, scan all root `bin/*.dll` recursively to a **fixed point**. Every imported non-system DLL must already be present beside the EXE, or be copied from this build's **explicit `/clang64/bin` directory** and recursively inspected in turn. A missing vendor DLL or error opening/disassembling a binary **fails packaging** and prints only its name and direct importer, not a whole log.
- Windows system DLLs (`kernel32.dll`, `ntdll.dll`, `user32.dll`, `ws2_32.dll`, `vulkan-1.dll`, standard OS import contracts) are intentionally not copied. Names are checked case-insensitively and imports with path traversal/drive syntax are rejected. Already-bundled DLLs are **never overwritten** by a different version from CLANG64.
- `bbport/packaging/windows/package.sh` runs the new check **after** existing `ldd` gathering and before assembling the remaining game scripts; releases cannot silently skip the check. This does not download anything, does not change game assets, does not read player saves, and does not publish a ZIP.
- Python unit fixtures test synthetic nested graphs `bb-probe → SDL3.dll → libwinpthread-1.dll`, intentionally absent codec, already-installed DLL identity, case-independent duplicate imports, blocked malicious DLL names and invalid PE/object inspection. Tests execute the actual Python production helper, with only external `llvm-objdump` mocked.

## Important limits

- This is a **static import** check. DLLs requested only at runtime via `LoadLibrary` or plugin Vulkan/SDL loader behavior are invisible to static PE import tables and still need clean Windows VM smoke testing and GPU hardware probes. Other packaged pieces, notably the PyInstaller `BLauncher.exe` `_internal` runtime, PkgTool, optional ReShade/DLSS/XeSS/Vulkan layers, require their own checks and licensing review.
- This check runs at actual packaging time on real PE outputs. The B21 standalone CI only uses **synthetic PE import fixtures**, not private game files or real DLL scans. It does not install or publish the launcher or run a real Bloodborne CUSA03173 session.
- Follow-up unified release gate must invoke `package.sh` once on the **final combined source** with pinned binaries, verify entire DLL/launcher/runtime file closure, preserve player saves/settings, and run real Windows 10/11 smoke with clean user profiles, 2/3/5-player co-op, NAT and savedata backups. True independent PC-native no-PS4-ELF port remains a separate build target.

No live Fornex, account secrets, proprietary game content or customer saves touched. All changes remain in a Draft branch.
