# SPDX-License-Identifier: GPL-2.0-or-later
"""Transactional storage for a trusted local AOT builder; not a game recompiler.

Only developer-owned code may supply ``build``. Neither an input dump nor its
manifest supplies a command to execute. Registry approval, compiler provenance,
native ABI closure and game/runtime testing remain separate prerequisites.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import uuid

from retail_intake import IntakeError
from retail_profiles import TARGETS, unique

MAX_MANIFEST = 1024 * 1024
MAX_FILES = 4096
MAX_OUTPUT = 8 * 1024**3
HEX = re.compile(r'[0-9a-f]{64}')


class PreparationError(IntakeError):
    pass


def _reject(reason):
    raise PreparationError(reason)


def _selection(value):
    if (type(value) is not dict or set(value) != {
            'schema', 'status', 'profile', 'target', 'recipe_sha256', 'selection_key'}
            or type(value['schema']) is not int or value['schema'] != 1
            or value['status'] != 'profile_selected_not_prepared'
            or type(value['profile']) is not str
            or not re.fullmatch(r'[a-z0-9-]{1,64}', value['profile'])
            or type(value['target']) is not str or value['target'] not in TARGETS
            or any(type(value[k]) is not str or not HEX.fullmatch(value[k])
                   for k in ('recipe_sha256', 'selection_key'))):
        _reject('invalid_preparation_selection')
    return dict(value)


def _relative(name):
    if type(name) is not str or not name or len(name) > 240 or '\\' in name:
        _reject('invalid_artifact_path')
    parts = name.split('/')
    if any(not re.fullmatch(r'[A-Za-z0-9_.-]+', p) or p in {'.', '..'} for p in parts):
        _reject('invalid_artifact_path')
    # A bundle must have the same names on every supported host filesystem.
    reserved = {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(1, 10)),
                *(f'lpt{i}' for i in range(1, 10))}
    if any(p.endswith('.') or p.split('.')[0].lower() in reserved for p in parts):
        _reject('invalid_artifact_path')
    return PurePosixPath(name)


def _dependencies(value):
    # Supplied by the trusted builder integration, not a user dump. The module
    # digest covers every executable module consumed by that recipe, not assets.
    if (type(value) is not dict or set(value) != {'toolchain', 'runtime_abi', 'modules'}
            or any(type(v) is not str or not HEX.fullmatch(v) for v in value.values())):
        _reject('invalid_build_dependencies')
    return dict(value)


def _file(root, name):
    path = root
    for part in _relative(name).parts:
        path = path / part
        if path.is_symlink():
            _reject('linked_artifact')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        _reject('invalid_artifact_type')
    return path


def _digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        before = os.fstat(f.fileno())
        size = 0
        while chunk := f.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_OUTPUT:
                _reject('artifact_too_large')
            h.update(chunk)
        after = os.fstat(f.fileno())
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if size != before.st_size or signature(before) != signature(after) or signature(after) != signature(path.lstat()):
        _reject('artifact_changed_during_read')
    return {'size': size, 'sha256': h.hexdigest()}


def _json(path):
    with path.open('rb') as f:
        raw = f.read(MAX_MANIFEST + 1)
    if len(raw) > MAX_MANIFEST:
        _reject('manifest_too_large')
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (ValueError, RecursionError) as exc:
        raise PreparationError('invalid_manifest_json') from exc


def _host_header(path, target):
    """Reject console images and wrong architectures; this is not an ABI audit."""
    with path.open('rb') as f:
        header = f.read(4096)
    good = False
    if target == 'linux-x64' and len(header) >= 64:
        good = (header[:7] == b'\x7fELF\x02\x01\x01'
                and struct.unpack_from('<H', header, 16)[0] in {2, 3}
                and struct.unpack_from('<H', header, 18)[0] == 62
                and struct.unpack_from('<H', header, 52)[0] == 64)
    elif target == 'windows-x64' and len(header) >= 64 and header[:2] == b'MZ':
        off = struct.unpack_from('<I', header, 60)[0]
        if off + 26 <= len(header):
            good = (header[off:off + 4] == b'PE\0\0'
                    and struct.unpack_from('<H', header, off + 4)[0] == 0x8664
                    and struct.unpack_from('<H', header, off + 24)[0] == 0x20b
                    and not struct.unpack_from('<H', header, off + 22)[0] & 0x2000)
    elif target == 'macos-arm64' and len(header) >= 32:
        good = (header[:4] == b'\xcf\xfa\xed\xfe'
                and struct.unpack_from('<I', header, 4)[0] == 0x0100000c
                and struct.unpack_from('<I', header, 12)[0] == 2)
    if not good:
        _reject('not_the_selected_host_executable')


def _inventory(root):
    result = {}
    names = {}
    total = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            relative = (Path(directory) / name).relative_to(root).as_posix()
            _relative(relative)
            if relative.casefold() in names and names[relative.casefold()] != relative:
                _reject('ambiguous_artifact_path')
            names[relative.casefold()] = relative
        for name in dirs:
            if (Path(directory) / name).is_symlink():
                _reject('linked_artifact')
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if relative == 'manifest.json':
                continue
            _relative(relative)
            # Inputs, console modules and intermediate code do not belong in a
            # runtime bundle. Renaming one does not bypass _host_header for entry.
            if path.suffix.lower() in {'.bin', '.self', '.prx', '.sprx', '.o', '.obj', '.c', '.cpp', '.s'}:
                _reject('non_runtime_artifact')
            value = _digest(_file(root, relative))
            total += value['size']
            result[relative] = value
            if len(result) > MAX_FILES or total > MAX_OUTPUT:
                _reject('artifact_budget_exceeded')
    if not result:
        _reject('empty_artifact')
    return result


def _sync_dir(path):
    if os.name == 'posix':
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _write_json(path, value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')
    if len(raw) > MAX_MANIFEST:
        _reject('manifest_too_large')
    fd, tmp = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        _sync_dir(path.parent)
    finally:
        Path(tmp).unlink(missing_ok=True)


@contextmanager
def _lock(root):
    """Kernel lock: a crashed process does not leave a permanent busy marker."""
    path = root / '.prepare.lock'
    if path.is_symlink():
        _reject('linked_cache_lock')
    flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_nlink != 1:
            _reject('invalid_cache_lock')
        if os.fstat(fd).st_size == 0:
            os.write(fd, b'\0')
        os.lseek(fd, 0, 0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise PreparationError('preparation_busy') from exc
        yield
    finally:
        os.close(fd)


def _root(path):
    path = Path(path)
    if path.is_symlink():
        _reject('linked_cache_root')
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def _overlap(left, right):
    for parent, child in ((left, right), (right, left)):
        if child.is_relative_to(parent):
            return True
        try:
            info = parent.stat()
        except FileNotFoundError:
            continue
        # realpath need not normalize spelling on a case-insensitive volume.
        # Compare existing ancestors by filesystem identity as well as spelling.
        for candidate in (child, *child.parents):
            try:
                other = candidate.stat()
            except FileNotFoundError:
                continue
            if (info.st_dev, info.st_ino) == (other.st_dev, other.st_ino):
                return True
    return False


def verify_build(folder, selection=None, dependencies=None):
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        _reject('invalid_build_directory')
    manifest = _json(_file(folder, 'manifest.json'))
    if (type(manifest) is not dict or set(manifest) != {'schema', 'selection', 'dependencies', 'entry', 'files'}
            or type(manifest['schema']) is not int or manifest['schema'] != 1):
        _reject('invalid_build_manifest')
    actual = _selection(manifest['selection'])
    actual_deps = _dependencies(manifest['dependencies'])
    if selection is not None and actual != _selection(selection):
        _reject('different_preparation_selection')
    if dependencies is not None and actual_deps != _dependencies(dependencies):
        _reject('different_build_dependencies')
    files = _inventory(folder)
    # Exact types matter: True must not compare equal to an artifact's byte size 1.
    if json.dumps(files, sort_keys=True) != json.dumps(manifest['files'], sort_keys=True):
        _reject('artifact_integrity_failed')
    entry = str(_relative(manifest['entry']))
    if entry not in files:
        _reject('missing_host_entry')
    _host_header(_file(folder, entry), actual['target'])
    return {'folder': folder, 'entry': folder / entry, 'manifest': manifest}


def current(cache, selection=None, dependencies=None):
    root = _root(cache)
    value = _json(_file(root, 'current.json'))
    if (type(value) is not dict or set(value) != {'schema', 'build'}
            or type(value['schema']) is not int or value['schema'] != 1
            or type(value['build']) is not str
            or not re.fullmatch(r'[0-9a-f]{64}-[0-9a-f]{32}', value['build'])):
        _reject('invalid_current_pointer')
    builds = root / 'builds'
    if builds.is_symlink():
        _reject('linked_builds_directory')
    return verify_build(builds / value['build'], selection, dependencies)


def prepare(cache, selection, dependencies, build, cancelled=lambda: False):
    """Run a trusted builder into fresh staging; never replace a working tree.

    ``build(stage, cancelled)`` returns the relative host entry filename. It owns
    compiler/provisioning choices and must poll cancellation during long work.
    The returned cache manifest establishes local consistency, not authenticity.
    """
    selection = _selection(selection)
    dependencies = _dependencies(dependencies)
    identity = json.dumps([selection, dependencies], sort_keys=True, separators=(',', ':')).encode()
    build_key = hashlib.sha256(identity).hexdigest()
    root = _root(cache)
    with _lock(root):
        if cancelled():
            _reject('preparation_cancelled')
        try:
            ready = current(root, selection, dependencies)
        except (OSError, PreparationError):
            ready = None
        if ready is not None:
            return {**ready, 'reused': True}
        builds = root / 'builds'
        if builds.is_symlink():
            _reject('linked_builds_directory')
        builds.mkdir(exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.staging-', dir=root))
        try:
            entry = str(_relative(build(stage, cancelled)))
            if cancelled():
                _reject('preparation_cancelled')
            files = _inventory(stage)
            if entry not in files:
                _reject('missing_host_entry')
            _host_header(_file(stage, entry), selection['target'])
            _write_json(stage / 'manifest.json', {
                'schema': 1, 'selection': selection, 'dependencies': dependencies,
                'entry': entry, 'files': files})
            verify_build(stage, selection, dependencies)
            # Publish only after payload bytes, manifest and directory entries
            # have been flushed. A successful rename alone does not flush data.
            for relative in files:
                with _file(stage, relative).open('r+b') as payload:
                    os.fsync(payload.fileno())
            for directory, _, _ in os.walk(stage, topdown=False):
                _sync_dir(Path(directory))
            if cancelled():
                _reject('preparation_cancelled')
            name = build_key + '-' + uuid.uuid4().hex
            destination = builds / name
            os.replace(stage, destination)
            _sync_dir(builds)
            if cancelled():
                # An unreferenced complete build is harmless; old current stays.
                _reject('preparation_cancelled')
            _write_json(root / 'current.json', {'schema': 1, 'build': name})
            return {**verify_build(destination, selection, dependencies), 'reused': False}
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def launch(cache, assets, user, selection=None, dependencies=None):
    """Start only a prepared host entry. No eboot read, build, shell or fallback.

    This wrapper cannot attest what trusted native machine code later opens;
    OS file/module tracing and ABI/import closure are mandatory release gates.
    Cache contents must not be writable by untrusted concurrent processes.
    """
    root = _root(cache)
    with _lock(root):
        ready = current(root, selection, dependencies)
        target = {'win32': 'windows-x64', 'linux': 'linux-x64', 'darwin': 'macos-arm64'}.get(sys.platform)
        import platform
        machine = platform.machine().lower()
        if (ready['manifest']['selection']['target'] != target
                or machine not in ({'arm64', 'aarch64'} if target == 'macos-arm64' else {'x86_64', 'amd64'})):
            _reject('wrong_launch_platform')
        assets = Path(assets).resolve(strict=True)
        if not assets.is_dir():
            _reject('invalid_asset_root')
        user = Path(user).resolve()
        # Runtime output must not invalidate its own prepared bundle or modify
        # source assets. Check all resolved roots before creating user data.
        for left, right in ((root, assets), (root, user), (assets, user)):
            if _overlap(left, right):
                _reject('overlapping_runtime_directories')
        user.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        for key in ('BB_GAME_DIR', 'BB_EBOOT', 'BB_ELF', 'BB_PROBE'):
            env.pop(key, None)
        env.update(BB_NATIVE_ASSET_ROOT=str(assets), BB_NATIVE_USER_DIR=str(user))
        return subprocess.Popen([str(ready['entry'])], cwd=ready['folder'], env=env,
                                stdin=subprocess.DEVNULL, shell=False)
