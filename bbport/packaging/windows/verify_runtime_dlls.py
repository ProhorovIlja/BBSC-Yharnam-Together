#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed static Windows PE import closure for bbport's staged executables.

Only import-table DLLs of bb-probe, GPU capabilities and staged root DLLs.
Windows system libraries are deliberately not bundled; non-system imports
must come from the package's bin/ or the pinned build's CLANG64 bin/.
No downloads, arbitrary DLL search PATH, game assets or user save reads.
"""
import argparse
from collections import deque
from pathlib import Path
import re
import shutil
import subprocess
import sys

IMPORT = re.compile(r"^\s*DLL Name:\s*(\S+\.dll)\s*$", re.IGNORECASE | re.MULTILINE)
SYSTEM = frozenset({
    "advapi32.dll", "bcrypt.dll", "bcryptprimitives.dll", "cfgmgr32.dll",
    "comctl32.dll", "comdlg32.dll", "crypt32.dll", "d2d1.dll",
    "d3d9.dll", "d3d11.dll", "d3d12.dll", "d3dcompiler_47.dll",
    "dcomp.dll", "dbghelp.dll", "dinput8.dll", "dnsapi.dll", "dsound.dll",
    "dwmapi.dll", "dxcore.dll", "dxva2.dll", "avrt.dll",
    "dxgi.dll", "gdi32.dll", "gdi32full.dll", "hid.dll",
    "imm32.dll", "iphlpapi.dll", "kernel32.dll", "kernelbase.dll",
    "msvcrt.dll", "ntdll.dll", "ncrypt.dll", "netapi32.dll",
    "mf.dll", "mfplat.dll", "mfreadwrite.dll", "mfuuid.dll", "mmdevapi.dll",
    "mpr.dll", "msacm32.dll", "msimg32.dll", "mswsock.dll", "normaliz.dll",
    "ole32.dll", "oleacc.dll", "oleaut32.dll", "opengl32.dll",
    "powrprof.dll", "propsys.dll", "psapi.dll", "rpcrt4.dll",
    "secur32.dll", "setupapi.dll", "shell32.dll", "shlwapi.dll",
    "uapi.dll", "ucrtbase.dll", "user32.dll", "userenv.dll",
    "usp10.dll", "uxtheme.dll", "shcore.dll", "urlmon.dll", "winusb.dll",
    "xinput1_4.dll", "version.dll", "vulkan-1.dll",
    "winhttp.dll", "wininet.dll", "winmm.dll", "winspool.drv",
    "wintrust.dll", "wldap32.dll", "ws2_32.dll", "wsock32.dll",
})


class ClosureError(RuntimeError):
    pass


def is_system(name: str) -> bool:
    key = name.casefold()
    return key in SYSTEM or key.startswith(("api-ms-win-", "ext-ms-win-"))


def import_names(binary: Path, objdump: str = "llvm-objdump") -> tuple[str, ...]:
    """Call the same LLVM toolchain that built the native Windows binaries."""
    try:
        r = subprocess.run(
            [objdump, "-p", str(binary)],
            capture_output=True, text=True, errors="replace", timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ClosureError(f"LLVM PE dependency inspection unavailable: {binary.name}: {exc}") from exc
    if r.returncode != 0:
        raise ClosureError(f"Cannot inspect PE dependencies: {binary.name}: exit={r.returncode}")
    # llvm-objdump returns exit 0 for some text inputs, so require a valid PE
    # signature before treating "no imports" as sufficient.
    try:
        with binary.open("rb") as f:
            if f.read(2) != b"MZ":
                raise ClosureError(f"Not a Windows PE executable: {binary.name}")
    except OSError as exc:
        raise ClosureError(f"Missing staged executable: {binary.name}: {exc}") from exc
    names = sorted({name for name in IMPORT.findall(r.stdout)}, key=str.casefold)
    for name in names:
        if (Path(name).name != name or any(c in name for c in ("\\", "/", ":"))
                or name.startswith(".")):
            raise ClosureError(f"Unsafe DLL import name in {binary.name}")
    return tuple(names)


def dll_inventory(folder: Path) -> dict[str, Path]:
    if not folder.is_dir():
        raise ClosureError(f"Missing DLL directory: {folder}")
    out: dict[str, Path] = {}
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.casefold() == ".dll":
            key = path.name.casefold()
            if key in out:
                raise ClosureError(f"Ambiguous case-insensitive DLL name: {key}")
            out[key] = path
    return out


def close_runtime(bin_dir: Path, clang_dir: Path, roots: list[Path],
                  objdump: str = "llvm-objdump") -> tuple[int, int]:
    """Copy and verify transitive non-system PE DLL imports from CLANG64 only."""
    local = dll_inventory(bin_dir)
    external = dll_inventory(clang_dir)
    # Include bundled DLLs even if ldd's initial executable closure omitted
    # them (e.g. a runtime backend loaded later by name).
    queue = deque([*roots, *local.values()])
    scanned: set[Path] = set()
    copied = 0
    edges = 0
    while queue:
        binary = queue.popleft()
        if binary in scanned:
            continue
        scanned.add(binary)
        for name in import_names(binary, objdump):
            if is_system(name):
                continue
            edges += 1
            key = name.casefold()
            target = local.get(key)
            if target is None:
                source = external.get(key)
                if source is None:
                    raise ClosureError(f"Unresolved non-system DLL: {binary.name} imports {name}")
                target = bin_dir / source.name
                # Never overwrite bundled libraries or silently fetch from
                # Windows/System32 / untrusted PATH.
                if not target.exists():
                    shutil.copy2(source, target)
                    copied += 1
                local[key] = target
            queue.append(target)
    return copied, edges


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bin-dir", type=Path, required=True)
    p.add_argument("--clang-dir", type=Path, default=Path("/clang64/bin"))
    p.add_argument("--root", type=Path, action="append", required=True)
    p.add_argument("--objdump", default="llvm-objdump")
    args = p.parse_args()
    try:
        copied, imports = close_runtime(args.bin_dir, args.clang_dir,
                                        args.root, args.objdump)
    except ClosureError as exc:
        print(f"BBPORT_RUNTIME_DLL_CLOSURE_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"BBPORT_RUNTIME_DLL_CLOSURE_PASS copied={copied} resolved_imports={imports}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
