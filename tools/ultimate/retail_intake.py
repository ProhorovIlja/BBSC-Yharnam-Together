# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only, offline intake for a merged PS4 dump; not native-build approval."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct

from retail_sfo import MAX_BYTES, identify

MAX_EXEC = 512 * 1024 * 1024


class IntakeError(ValueError):
    """A public diagnostic with no local paths."""


def contained_file(root, relative):
    path = root
    for part in relative.split('/'):
        path = path / part
        if path.is_symlink():
            raise IntakeError('linked_input_not_supported')
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise IntakeError('missing_or_invalid_' + relative.rsplit('/', 1)[-1])
    return path


def identity(root):
    with contained_file(root, 'sce_sys/param.sfo').open('rb') as stream:
        try:
            return identify(stream.read(MAX_BYTES + 1))
        except ValueError as exc:
            raise IntakeError('invalid_param.sfo') from exc


def fingerprint(path):
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 64 <= before.st_size <= MAX_EXEC:
            raise IntakeError('invalid_eboot_size_or_type')
        header = stream.read(64)
        if header.startswith(b'\x4f\x15\x3d\x1d'):
            raise IntakeError('self_requires_supported_local_extraction')
        # ELF64, little-endian, current ELF version, AMD64. This is only a shape check.
        if (len(header) != 64 or header[:7] != b'\x7fELF\x02\x01\x01'
                or struct.unpack_from('<H', header, 18)[0] != 62
                or struct.unpack_from('<I', header, 20)[0] != 1
                or struct.unpack_from('<H', header, 52)[0] != 64):
            raise IntakeError('expected_x86_64_elf_input')
        digest = hashlib.sha256(header)
        read = len(header)
        while chunk := stream.read(1024 * 1024):
            read += len(chunk)
            if read > before.st_size:
                raise IntakeError('eboot_changed_during_read')
            digest.update(chunk)
        after = os.fstat(stream.fileno())
        named = path.stat(follow_symlinks=False)
        def signature(info):
            return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

        if read != before.st_size or signature(before) != signature(after) or signature(after) != signature(named):
            raise IntakeError('eboot_changed_during_read')
    return {'size': read, 'sha256': digest.hexdigest()}


def inspect(root):
    root = root.resolve()
    title_id, app_ver = identity(root)
    if app_ver != '01.09':
        raise IntakeError('merged_update_01.09_required')
    return {
        'schema': 1,
        'title_id': title_id,
        'app_ver': app_ver,
        'eboot': fingerprint(contained_file(root, 'eboot.bin')),
        'status': 'fingerprint_only',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path, help='root of a locally extracted, merged game folder')
    args = parser.parse_args()
    try:
        report = inspect(args.game)
    except IntakeError as exc:
        print(json.dumps({'schema': 1, 'status': 'rejected', 'reason': str(exc)}))
        return 2
    except (OSError, RuntimeError):
        print(json.dumps({'schema': 1, 'status': 'rejected', 'reason': 'cannot_read_input'}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
