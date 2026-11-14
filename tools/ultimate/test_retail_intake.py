# SPDX-License-Identifier: GPL-2.0-or-later
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from retail_intake import IntakeError, inspect


def sfo(title, version):
    keys = b'TITLE_ID\0APP_VER\0'
    values = title + b'\0' + version + b'\0'
    return (struct.pack('<4s4I', b'\0PSF', 0x101, 52, 52 + len(keys), 2)
            + struct.pack('<HHIII', 0, 0x0204, len(title) + 1, len(title) + 1, 0)
            + struct.pack('<HHIII', 9, 0x0204, len(version) + 1, len(version) + 1, len(title) + 1)
            + keys + values)


class IntakeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / 'Unrelated folder name'
        (self.root / 'sce_sys').mkdir(parents=True)
        self.meta = self.root / 'sce_sys/param.sfo'
        self.meta.write_bytes(sfo(b'CUSA03173', b'01.09'))
        self.exe = self.root / 'eboot.bin'
        header = bytearray(64)
        header[:7] = b'\x7fELF\x02\x01\x01'
        struct.pack_into('<HI', header, 18, 62, 1)
        struct.pack_into('<H', header, 52, 64)
        self.raw = bytes(header) + b'\x07' * (1024 * 1024 + 3)
        self.exe.write_bytes(self.raw)

    def test_full_hash_and_no_paths(self):
        report = inspect(self.root)
        self.assertEqual(report['status'], 'fingerprint_only')
        self.assertEqual(report['eboot'], {'size': len(self.raw), 'sha256': hashlib.sha256(self.raw).hexdigest()})
        self.assertNotIn(str(self.root), str(report))

    def test_id_is_not_folder_name(self):
        first = inspect(self.root)
        self.meta.write_bytes(sfo(b'CUSA00299', b'01.09'))
        second = inspect(self.root)
        self.assertEqual(second['title_id'], 'CUSA00299')
        self.assertEqual(first['eboot'], second['eboot'])

    def test_byte_change_changes_fingerprint(self):
        before = inspect(self.root)
        self.exe.write_bytes(self.raw[:-1] + b'\x08')
        self.assertNotEqual(before['eboot'], inspect(self.root)['eboot'])

    def test_base_only(self):
        self.meta.write_bytes(sfo(b'CUSA03173', b'01.00'))
        self.exe.unlink()  # reject before trying to open the executable
        with self.assertRaisesRegex(IntakeError, 'merged_update'):
            inspect(self.root)

    def test_bad_metadata(self):
        self.meta.write_bytes(b'\x00PSF')
        with self.assertRaisesRegex(IntakeError, 'invalid_param'):
            inspect(self.root)

    def test_missing_executable(self):
        self.exe.unlink()
        with self.assertRaisesRegex(IntakeError, 'missing_or_invalid_eboot'):
            inspect(self.root)

    def test_self(self):
        self.exe.write_bytes(b'\x4f\x15\x3d\x1d' + bytes(60))
        with self.assertRaisesRegex(IntakeError, 'self_requires'):
            inspect(self.root)

    def test_non_elf(self):
        self.exe.write_bytes(b'MZ' + bytes(62))
        with self.assertRaisesRegex(IntakeError, 'expected_x86_64'):
            inspect(self.root)

    def test_symlink(self):
        self.exe.unlink()
        target = self.root.parent / 'external'
        target.write_bytes(self.raw)
        try:
            self.exe.symlink_to(target)
        except OSError as exc:
            self.skipTest(str(exc))
        with self.assertRaisesRegex(IntakeError, 'linked_input'):
            inspect(self.root)


if __name__ == '__main__':
    unittest.main()
