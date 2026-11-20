# SPDX-License-Identifier: GPL-2.0-or-later
"""Validate portable update archives before staging them for the Windows launcher."""
import re
import stat
from pathlib import Path

MAX_ENTRIES = 30_000
MAX_EXPANDED_BYTES = 4 << 30
_RESERVED = re.compile(r'(?i)(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])\Z')
_UNSAFE = re.compile(r'[\x00-\x1f<>:"|?*\\]')


def extract_update(package, destination):
    """Stage a complete archive in a new directory and return the only launcher."""
    entries = package.infolist()
    if len(entries) > MAX_ENTRIES or sum(entry.file_size for entry in entries) > MAX_EXPANDED_BYTES:
        raise ValueError('Update archive exceeds the extraction budget')

    paths = {}
    launchers = []
    for entry in entries:
        name = entry.orig_filename
        directory = entry.is_dir()
        parts = (name[:-1] if directory else name).split('/')
        if any(not part or part.endswith(('.', ' ')) or _UNSAFE.search(part) or
               _RESERVED.fullmatch(part.split('.')[0].rstrip(' ')) for part in parts):
            raise ValueError(f'Unsafe update archive member: {name!r}')
        if stat.S_IFMT(entry.external_attr >> 16) not in (0, stat.S_IFDIR if directory else stat.S_IFREG):
            raise ValueError(f'Unsupported update archive member: {name!r}')
        if entry.flag_bits & 1:
            raise ValueError('Encrypted update archives are not supported')

        for depth in range(1, len(parts) + 1):
            spelling = '/'.join(parts[:depth])
            key = spelling.casefold()
            explicit = depth == len(parts)
            is_dir = not explicit or directory
            previous = paths.get(key)
            if previous is not None and (previous[:2] != (spelling, is_dir) or
                                         (previous[2] and explicit)):
                raise ValueError(f'Conflicting update archive member: {name!r}')
            paths[key] = (spelling, is_dir, explicit or bool(previous and previous[2]))
        if not directory and parts[-1].casefold() == 'blauncher.exe':
            launchers.append(parts)

    if len(launchers) != 1:
        raise ValueError('Update archive must contain exactly one BLauncher.exe')
    destination = Path(destination)
    destination.mkdir()  # never extract into a left-over or pre-created directory
    package.extractall(destination, entries)
    return destination.joinpath(*launchers[0])
