# SPDX-License-Identifier: GPL-2.0-or-later
"""B21: package-time Windows PE DLL closure, synthetic import graphs only.

Tests the actual production Python helper directly. No game file, network,
server, executable build, global MSYS2 installation or actual release ZIP.
"""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from unittest import TestCase, main, mock

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "bbport/packaging/windows/verify_runtime_dlls.py"
PACKAGER = ROOT / "bbport/packaging/windows/package.sh"
spec = importlib.util.spec_from_file_location("bbsc_runtime_closure", HELPER)
closure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(closure)


class ActualPackagingClosure(TestCase):
    def new_stage(self, td):
        root = Path(td)
        bin_dir = root / "out/stage/bbport-windows/bin"
        external = root / "clang64/bin"
        bin_dir.mkdir(parents=True)
        external.mkdir(parents=True)
        roots = [
            bin_dir / "bb-probe.exe",
            bin_dir / "bb-gpu-capabilities.exe",
            bin_dir.parent / "Bloodborne.exe",
        ]
        for path in roots:
            path.write_bytes(b"MZ-\x00synthetic unit fixture")
        return bin_dir, external, roots

    def test_real_pe_import_parser_is_not_limited_to_direct_ldr_output(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "sample.exe"
            exe.write_bytes(b"MZhello")
            raw = (
                "The Import Tables:\n"
                "    DLL Name: SDL3.dll\n"
                "    DLL Name: KERNEL32.dll\n"
                "    DLL Name: libwinpthread-1.dll\n"
                "    DLL Name: SDL3.dll\n"
            )
            with mock.patch.object(closure.subprocess, "run",
                                   return_value=SimpleNamespace(returncode=0, stdout=raw)):
                self.assertEqual(
                    closure.import_names(exe),
                    ("KERNEL32.dll", "libwinpthread-1.dll", "SDL3.dll"),
                )
            exe.write_bytes(b"not a windows executable")
            with mock.patch.object(closure.subprocess, "run",
                                   return_value=SimpleNamespace(returncode=0, stdout="")):
                with self.assertRaisesRegex(closure.ClosureError, "Not a Windows PE"):
                    closure.import_names(exe)

    def test_real_import_parser_rejects_invalid_dll_basename_and_objdump_failure(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "bb-probe.exe"
            exe.write_bytes(b"MZvalid")
            for dangerous in ("../evil.dll", "C:\\wrong.dll", "D:evil.dll"):
                with self.subTest(dangerous=dangerous):
                    output = "DLL Name: " + dangerous + "\n"
                    with mock.patch.object(closure.subprocess, "run",
                                           return_value=SimpleNamespace(returncode=0, stdout=output)):
                        with self.assertRaises(closure.ClosureError):
                            closure.import_names(exe)
            with mock.patch.object(closure.subprocess, "run",
                                   return_value=SimpleNamespace(returncode=11, stdout="")):
                with self.assertRaisesRegex(closure.ClosureError, "exit=11"):
                    closure.import_names(exe)

    def test_transitive_vendor_dependency_is_pulled_and_system_loader_not_bundled(self):
        with tempfile.TemporaryDirectory() as td:
            bin_dir, external, roots = self.new_stage(td)
            (external / "SDL3.dll").write_bytes(b"MZ SDL3 source")
            (external / "libwinpthread-1.dll").write_bytes(b"MZ pthread source")
            imports = {
                "bb-probe.exe": ("SDL3.dll", "VULKAN-1.dll", "KERNEL32.dll"),
                "bb-gpu-capabilities.exe": ("SDL3.dll",),
                "bloodborne.exe": ("USER32.dll",),
                "sdl3.dll": ("libwinpthread-1.dll", "ucrtbase.dll"),
                "libwinpthread-1.dll": ("KERNELBASE.dll",),
            }
            with mock.patch.object(closure, "import_names",
                                   side_effect=lambda p, objdump="": imports.get(p.name.casefold(), ())):
                count, edges = closure.close_runtime(bin_dir, external, roots)
            self.assertEqual(count, 2)
            self.assertEqual(edges, 3)
            self.assertEqual((bin_dir / "SDL3.dll").read_bytes(), b"MZ SDL3 source")
            self.assertEqual((bin_dir / "libwinpthread-1.dll").read_bytes(), b"MZ pthread source")
            self.assertFalse((bin_dir / "VULKAN-1.dll").exists())
            # Running twice cannot overwrite existing package files.
            with mock.patch.object(closure, "import_names",
                                   side_effect=lambda p, objdump="": imports.get(p.name.casefold(), ())):
                copied_again, _ = closure.close_runtime(bin_dir, external, roots)
            self.assertEqual(copied_again, 0)

    def test_package_build_fails_closed_on_unresolved_vendor_import(self):
        with tempfile.TemporaryDirectory() as td:
            bin_dir, external, roots = self.new_stage(td)
            with mock.patch.object(closure, "import_names",
                                   side_effect=lambda p, objdump="": (
                                       ("CriticalVendor123.dll",) if p.name == "bb-probe.exe" else ()
                                   )):
                with self.assertRaisesRegex(closure.ClosureError,
                                            "bb-probe.exe imports CriticalVendor123.dll"):
                    closure.close_runtime(bin_dir, external, roots)
            self.assertFalse((bin_dir / "CriticalVendor123.dll").exists())

    def test_locally_bundled_dll_is_not_overwritten_by_external_version(self):
        with tempfile.TemporaryDirectory() as td:
            bin_dir, external, roots = self.new_stage(td)
            (bin_dir / "SDL3.dll").write_bytes(b"MZ bundled")
            (external / "SDL3.dll").write_bytes(b"MZ newer unrelated system copy")
            with mock.patch.object(closure, "import_names",
                                   side_effect=lambda p, objdump="": (
                                       ("SDL3.dll",) if p.name == "bb-probe.exe" else ()
                                   )):
                copied, edges = closure.close_runtime(bin_dir, external, roots)
            self.assertEqual((copied, edges), (0, 1))
            self.assertEqual((bin_dir / "SDL3.dll").read_bytes(), b"MZ bundled")

    def test_production_package_invokes_closure_before_including_game_scripts(self):
        s = PACKAGER.read_text(encoding="utf-8")
        for text in (
            "llvm-objdump",
            "verify_runtime_dlls.py",
            "--bin-dir \"$dest/bin\"",
            "--root \"$dest/bin/bb-probe.exe\"",
            "--root \"$dest/bin/bb-gpu-capabilities.exe\"",
            "--root \"$dest/Bloodborne.exe\"",
        ):
            self.assertIn(text, s, text)
        self.assertLess(s.index("verify_runtime_dlls.py"), s.index("cp -r scripts patches"))
        self.assertNotIn("BB_GAME_DIR", HELPER.read_text())
        self.assertNotIn("requests.get", HELPER.read_text())


if __name__ == "__main__":
    main()
