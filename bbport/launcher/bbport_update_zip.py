# SPDX-License-Identifier: GPL-2.0-or-later
"""Validate portable update archives before staging them for the Windows launcher."""
import os
import re
import shutil
import stat
import tempfile
from contextlib import contextmanager
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


def _check_install_path(path, directory, *, required=False):
    try:
        info = path.lstat()
    except FileNotFoundError:
        if required:
            raise
        return
    if (getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT or
            not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        raise ValueError(f'Update cannot replace a linked or incompatible path: {path}')


def copy_portable_update(source, target, ignore):
    """Validate an idle installation and atomically replace individual files, not the whole tree."""
    source, target = Path(source), Path(target)
    if not target.is_dir():
        raise ValueError('The current installation directory is missing')
    _check_install_path(source, True, required=True)
    _check_install_path(target, True, required=True)
    source_real, target_real = source.resolve(), target.resolve()
    if (source_real == target_real or source_real in target_real.parents or
            target_real in source_real.parents):
        raise ValueError('Update staging and installation must be separate trees')

    def preflight(src, dst):
        entries = list(src.iterdir())
        skipped = ignore(str(src), [item.name for item in entries])
        for item in entries:
            if item.name in skipped:
                continue
            directory = item.is_dir()
            _check_install_path(item, directory, required=True)
            candidate = dst / item.name
            _check_install_path(candidate, directory)
            if directory:
                preflight(item, candidate)

    def replace_file(src, dst):
        fd, name = tempfile.mkstemp(prefix='.bb-update-', dir=Path(dst).parent)
        os.close(fd)
        try:
            shutil.copyfile(src, name)
            os.replace(name, dst)
        finally:
            try:
                os.unlink(name)
            except FileNotFoundError:
                pass
        return dst

    preflight(source, target)
    shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignore, copy_function=replace_file)


def make_portable_stage(parent=None):
    """An attempt owns its scratch files; other launchers never clear this path."""
    return Path(tempfile.mkdtemp(prefix='bbport-update-', dir=parent))


@contextmanager
def lock_portable_install(target):
    """Serialize cooperating portable installers for this directory."""
    target = Path(target)
    _check_install_path(target, True, required=True)
    path = target / '.bbport-update.lock'
    _check_install_path(path, False)
    with path.open('a+b') as lock:
        lock.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError('Another portable update owns the installation, or the lock is unavailable') from error
        # Leave the lock file in place: removing it would let another process
        # lock a different file while a handle to the original still exists.
        yield
