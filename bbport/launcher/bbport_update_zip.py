# SPDX-License-Identifier: GPL-2.0-or-later
"""Validate portable update archives before staging them for the Windows launcher."""
import re
import shutil
import stat
from pathlib import Path

MAX_DOWNLOAD_BYTES = 2 << 30
MAX_ENTRIES = 30_000
MAX_EXPANDED_BYTES = 4 << 30
_RESERVED = re.compile(r'(?i)(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])\Z')
_UNSAFE = re.compile(r'[\x00-\x1f<>:"|?*\\]')


def download_update(response, out, progress):
    """Copy a bounded complete HTTP response, with or without a length header."""
    declared = response.headers.get('Content-Length')
    expected = int(declared) if declared is not None else None
    if expected is not None and not 0 < expected <= MAX_DOWNLOAD_BYTES:
        raise ValueError('Update download has an invalid size')
    done, shown = 0, -1
    while chunk := response.read(1 << 20):
        done += len(chunk)
        if done > MAX_DOWNLOAD_BYTES or (expected is not None and done > expected):
            raise ValueError('Update download exceeded its size limit')
        out.write(chunk)
        percent = done * 100 // expected if expected is not None else 0
        if percent != shown:
            shown = percent
            progress(percent)
    if not done or (expected is not None and done != expected):
        raise ValueError('Update download ended before the expected size')


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
        if len(parts) > 32 or len(name) > 1024 or any(not part or part.endswith(('.', ' ')) or _UNSAFE.search(part) or
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
    try:
        package.extractall(destination, entries)
    except Exception:
        # Only remove the directory this call created. Keep the original
        # exception for the launcher's error dialog if cleanup is also blocked.
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return destination.joinpath(*launchers[0])
