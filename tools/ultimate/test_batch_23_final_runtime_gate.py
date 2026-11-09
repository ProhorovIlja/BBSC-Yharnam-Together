# SPDX-License-Identifier: GPL-2.0-or-later
"""B23: validate the final package-time DLL gate, without a game or compiler."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main, mock

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "bbport/packaging/windows/package.sh"
VERIFIER = ROOT / "bbport/packaging/windows/verify_runtime_dlls.py"
spec = importlib.util.spec_from_file_location("ultimate_b23_closure", VERIFIER)
closure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(closure)


class FinalGate(TestCase):
    def stage(self, directory):
        root = Path(directory)
        bin_dir = root / "stage/bin"
        clang = root / "clang64/bin"
        bin_dir.mkdir(parents=True)
        clang.mkdir(parents=True)
        exe = bin_dir / "bb-probe.exe"
        exe.write_bytes(b"MZmock")
        return bin_dir, clang, [exe]

    def test_staging_order_final_verification_is_unique_and_precedes_both_archive_modes(self):
        s = PACKAGE.read_text(encoding="utf-8")
        gate = "out/pyenv/Scripts/python.exe -I packaging/windows/verify_runtime_dlls.py"
        self.assertEqual(s.count(gate), 1)
        stage = s.index(gate)
        # These optional libraries previously arrived AFTER the B21 gate.
        for staged_asset in (
            "cp out/bbport_dlss.dll out/nvngx_dlss.dll",
            "cp out/xess/bin/libxess.dll",
            'cp out/reshade/ReShade64.dll "$reshade_src/',
            'cp out/pkgtool/PkgTool.exe out/pkgtool/LibOrbisPkg.dll',
        ):
            self.assertLess(s.index(staged_asset), stage, staged_asset)
        self.assertLess(stage, s.index("if [[ ${BB_PACKAGE_STAGE_ONLY:-} == 1 ]]"))
        self.assertLess(stage, s.index("make_zip.py out/stage"))
        self.assertIn('--root "$dest/Bloodborne.exe"', s)
        self.assertIn('--bin-dir "$dest/bin"', s)

    def test_real_closure_inspects_late_xess_and_dlss_dlls_and_all_transitive_imports(self):
        with TemporaryDirectory() as td:
            bin_dir, clang, roots = self.stage(td)
            (bin_dir / "libxess.dll").write_bytes(b"MZlate-xess")
            (bin_dir / "bbport_dlss.dll").write_bytes(b"MZlate-dlss")
            (clang / "needed_by_xess.dll").write_bytes(b"MZvendor")
            (clang / "needed_by_dlss.dll").write_bytes(b"MZvendor")
            calls = []
            imports = {
                "libxess.dll": ("needed_by_xess.dll", "KERNEL32.dll"),
                "bbport_dlss.dll": ("needed_by_dlss.dll",),
                "needed_by_xess.dll": ("USER32.dll",),
                "needed_by_dlss.dll": (),
            }
            def fake_imports(path, objdump="llvm-objdump"):
                calls.append(path.name.casefold())
                return imports.get(path.name.casefold(), ())
            with mock.patch.object(closure, "import_names", side_effect=fake_imports):
                copied, edges = closure.close_runtime(bin_dir, clang, roots)
            self.assertEqual((copied, edges), (2, 2))
            self.assertIn("libxess.dll", calls)
            self.assertIn("bbport_dlss.dll", calls)
            self.assertIn("needed_by_xess.dll", calls)
            self.assertIn("needed_by_dlss.dll", calls)

    def test_missing_import_from_late_staged_vendor_dll_blocks_package(self):
        with TemporaryDirectory() as td:
            bin_dir, clang, roots = self.stage(td)
            (bin_dir / "libxess.dll").write_bytes(b"MZlate-xess")
            def imports(path, objdump="llvm-objdump"):
                return ("xess_unavailable_vendor.dll",) if path.name == "libxess.dll" else ()
            with mock.patch.object(closure, "import_names", side_effect=imports):
                with self.assertRaisesRegex(closure.ClosureError,
                                            "libxess.dll imports xess_unavailable_vendor.dll"):
                    closure.close_runtime(bin_dir, clang, roots)
            self.assertFalse((bin_dir / "xess_unavailable_vendor.dll").exists())


if __name__ == "__main__":
    main()
