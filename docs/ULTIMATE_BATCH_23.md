# Ultimate B23: final package-time closure after optional DLL staging

**2026-11-09.** Continues the exact cumulative B01–B22 source on top of Draft PR #54. This is a narrow packaging correctness fix, not a separate installer or a port architecture change.

## Confirmed source gap

B21's `bbport/packaging/windows/verify_runtime_dlls.py` correctly scans all root `bin/*.dll` and transitive imports at invocation time. But `package.sh` invoked it before adding optional `bbport_dlss.dll` / NVIDIA DLSS runtime and Intel `libxess.dll`. Thus an additional vendor DLL introduced later could bypass the static-import gate, even though the completed ZIP would ship it. This is a **source-proven ordering gap**, not proof that the current real package contains an unresolved library.

## Actual change

- Move the existing, single fail-closed verifier invocation to the end of DLL staging, before both stage-only and ZIP exits.
- Keep the verifier's three original PE roots and its actual scan of every `bin/*.dll`; DLL sources remain limited to the explicit CLANG64 runtime tree and bundled files.
- Update the inherited B21 packaging order regression to the new correct invariant.
- New B23 regression calls the production closure function with **late-staged XeSS and DLSS fixture DLLs** and verifies their nested dependencies are copied from the build toolchain; an absent vendor import fails.
- Fast CI checks exact six changed paths, pinned package/test Git blobs, Bash/Python syntax, inherited B21 tests and new B23 tests. No Windows native engine rebuild per package-only edit.

## Still to verify before public release

The final entire staged package must run through a real Windows CLANG64 package build and then clean Windows 10/11 virtual-machine smoke testing. The static import graph does not cover dynamic `LoadLibrary`, PyInstaller's `BLauncher.exe` `_internal` runtime, plugins in `bin/reshade`, `bin/pkgtool`, GPU drivers, or server/gameplay connections. Separate checks are required for these (including original user saves and user settings preservation). No private game files, copyrighted game binaries, actual Fornex deployment or public release were used.

Upstream research candidates retained for separate compatibility work include [Jgamrot/yharnam-pc v2.3.2](https://github.com/Jgamrot/yharnam-pc/releases/tag/v2.3.2) on third-player discovery, [droogie/bbhost PR #217](https://github.com/droogie/bbhost/pull/217) on multiplayer lifecycle, and [droogie/bbhost PR #223](https://github.com/droogie/bbhost/pull/223) on renderer/upscaling. These are **not** incorporated by B23.
