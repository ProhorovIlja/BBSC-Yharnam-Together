# SPDX-License-Identifier: GPL-2.0-or-later
"""Recover interrupted portable update transactions before starting another one.

This journal protects against ordinary process termination between file replaces;
a filesystem/power-loss durability guarantee also depends on directory metadata
flush and the underlying volume, and is not claimed here.
"""
import json
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path, PurePosixPath

TX_PREFIX = '.bbport-update-undo-'
MAX_MANIFEST_BYTES = 32 << 20
MAX_MANIFEST_ENTRIES = 30000
_UNSAFE = re.compile(r'[\x00-\x1f<>:"|?*\\]')
_RESERVED = re.compile(r'(?i)(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])\Z')


def _regular(path, *, directory=False):
    info = path.lstat()
    if ((getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        raise ValueError(f'Unsafe updater state path: {path}')


def _child(target, relative):
    if not isinstance(relative, str) or len(relative) > 1024:
        raise ValueError('Invalid updater recovery path')
    parts = PurePosixPath(relative).parts
    if not parts or len(parts) > 32 or relative != '/'.join(parts):
        raise ValueError('Noncanonical updater recovery path')
    if any(part in ('', '.', '..') or part.endswith(('.', ' ')) or _UNSAFE.search(part)
           or _RESERVED.fullmatch(part.split('.')[0].rstrip(' '))
           or part.casefold() == '.bbport-update.lock'
           or part.casefold().startswith(TX_PREFIX)
           for part in parts):
        raise ValueError('Unsafe updater recovery member')
    # None of the manifest paths is allowed to traverse a junction or symlink.
    current = target
    for part in parts[:-1]:
        current = current / part
        try:
            _regular(current, directory=True)
        except FileNotFoundError:
            # A newly introduced directory may not have been made yet.
            continue
    dest = target.joinpath(*parts)
    try:
        _regular(dest)
    except FileNotFoundError:
        pass
    return dest


def prepare_journal(undo, target, planned):
    """Write and flush a manifest only after all old/new files were copied."""
    entries = []
    seen = set()
    for _, dest, existed in planned:
        relative = dest.relative_to(target).as_posix()
        _child(target, relative)
        key = relative.casefold()
        if key in seen:
            raise ValueError('Duplicate updater recovery destination')
        seen.add(key)
        entries.append({'path': relative, 'old': bool(existed)})
    if not entries or len(entries) > MAX_MANIFEST_ENTRIES:
        raise ValueError('Invalid updater recovery manifest length')
    data = json.dumps({'version': 1, 'entries': entries}, ensure_ascii=False).encode('utf-8')
    if len(data) > MAX_MANIFEST_BYTES:
        raise ValueError('Updater recovery manifest too large')
    with (undo / 'manifest.json').open('xb') as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())


def mark_journal(undo, state):
    if state not in ('ready', 'committed'):
        raise ValueError('Unknown updater journal state')
    with (undo / state).open('xb') as out:
        out.write(b'1')
        out.flush()
        os.fsync(out.fileno())


def _entries(undo, target):
    file = undo / 'manifest.json'
    _regular(file)
    if file.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError('Updater journal is too large; manual recovery required')
    with file.open('rb') as src:
        data = json.load(src)
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('Invalid updater journal version')
    values = data.get('entries')
    if not isinstance(values, list) or not 0 < len(values) <= MAX_MANIFEST_ENTRIES:
        raise ValueError('Invalid updater journal entries')
    parsed = []
    seen = set()
    for index, value in enumerate(values):
        if not isinstance(value, dict) or set(value) != {'path', 'old'} or type(value['old']) is not bool:
            raise ValueError('Invalid updater journal entry')
        dst = _child(target, value['path'])
        key = value['path'].casefold()
        if key in seen:
            raise ValueError('Duplicate updater journal destinations')
        seen.add(key)
        parsed.append((index, dst, value['old']))
    return parsed


def _restore(backup, dest):
    # Keep the original backup intact until the entire recovery succeeds.
    # Retrying this method after a crash is therefore idempotent.
    fd, name = tempfile.mkstemp(prefix='.bbport-restore-', dir=dest.parent)
    os.close(fd)
    try:
        shutil.copyfile(backup, name)
        os.replace(name, dest)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def recover_pending_portable_updates(target):
    """Rollback incomplete installs; keep untrusted/unrecoverable state untouched.

    Caller must already hold lock_portable_install(target), and the old game
    process must be closed. Returns the count of previously interrupted updates
    successfully handled. Never silently continue after a failed rollback.
    """
    target = Path(target)
    _regular(target, directory=True)
    handled = 0
    for undo in sorted(target.iterdir()):
        if not undo.name.casefold().startswith(TX_PREFIX):
            continue
        _regular(undo, directory=True)
        entries = _entries(undo, target)  # An unknown legacy state is not deleted.
        ready = undo / 'ready'
        committed = undo / 'committed'
        for marker in (ready, committed):
            try:
                _regular(marker)
            except FileNotFoundError:
                pass
        if committed.exists() and not ready.exists():
            raise ValueError('Impossible portable transaction marker order')
        if ready.exists() and not committed.exists():
            # The install may have stopped after any individual file replace.
            for index, dest, existed in reversed(entries):
                if existed:
                    old = undo / 'originals' / str(index)
                    _regular(old)
                    if not dest.parent.is_dir():
                        raise ValueError('Updater recovery parent disappeared')
                    _restore(old, dest)
                elif dest.exists():
                    _regular(dest)
                    dest.unlink()
            # Safe to remove only empty directories introduced by this update.
            for _, dest, existed in sorted(entries, key=lambda x: len(x[1].parts), reverse=True):
                if existed:
                    continue
                current = dest.parent
                while current != target:
                    try:
                        _regular(current, directory=True)
                        current.rmdir()
                    except OSError:
                        break
                    current = current.parent
        shutil.rmtree(undo)
        handled += 1
    return handled
