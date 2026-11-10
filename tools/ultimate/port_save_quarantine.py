#!/usr/bin/env python3
"""Read-only-to-source, OFFLINE save quarantine imported from Windows-port ideas.

Source inspiration: ProhorovIlja/bloodborne_pc_windows_port (pinned
6486642d35418bd26c278bceadaf42e842daf4e4), scripts/party_saves.py and
src/runtime_savepolicy.c. This is a safer, standalone adaptation, NOT the
Windows port's in-place copy_solo_to_party(replace=True).

Only copies to user/save_backups/ultimate_quarantine/<random>.ready.
Never replaces/removes/renames savedata or savedata_party. No auto-restore.
Run only against a user-approved OFFLINE local save copy. A checksum-verified
snapshot is not an atomic multi-file point-in-time save if a game is writing.
No universal power-loss/directory-fsync guarantees.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

SOURCE_FOLDERS = {"solo": "savedata", "party": "savedata_party"}
MAX_FILES = 2048
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
CHUNK = 1 << 20
MANIFEST = "ULTIMATE_SNAPSHOT.json"


class SnapshotError(RuntimeError):
    pass


def _real_directory(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise SnapshotError(f"directory unavailable: {path}") from exc
    if not stat.S_ISDIR(mode) or path.is_symlink():
        raise SnapshotError(f"not a real directory: {path}")


def _files(root: Path) -> list[tuple[str, Path, int]]:
    _real_directory(root)
    found: list[tuple[str, Path, int]] = []
    total = 0
    for directory, dirs, filenames in os.walk(root, topdown=True, followlinks=False):
        parent = Path(directory)
        _real_directory(parent)
        for name in sorted(dirs):
            _real_directory(parent / name)  # reject nested symlinks
        dirs.sort()
        for name in sorted(filenames):
            file = parent / name
            if name.endswith(".bbtmp"):
                continue  # same incomplete temporary-file exclusion as original
            try:
                st = file.lstat()
            except OSError as exc:
                raise SnapshotError(f"source vanished: {file}") from exc
            if not stat.S_ISREG(st.st_mode) or file.is_symlink():
                raise SnapshotError(f"non-regular save input: {file}")
            if st.st_size > MAX_FILE_BYTES:
                raise SnapshotError("save file exceeds protective size bound")
            total += st.st_size
            if total > MAX_TOTAL_BYTES or len(found) >= MAX_FILES:
                raise SnapshotError("save inventory exceeds protective bounds")
            found.append((file.relative_to(root).as_posix(), file, st.st_size))
    found.sort(key=lambda item: item[0])
    return found


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(CHUNK):
            h.update(block)
    return h.hexdigest()


def _copy_one(source: Path, dest: Path) -> str:
    before = source.stat()
    h = hashlib.sha256()
    with source.open("rb") as inp, dest.open("xb") as out:
        while block := inp.read(CHUNK):
            h.update(block)
            out.write(block)
        out.flush()
        os.fsync(out.fileno())
    after = source.stat()
    if ((before.st_size, before.st_mtime_ns, before.st_ino) !=
            (after.st_size, after.st_mtime_ns, after.st_ino)):
        raise SnapshotError("source changed while copying")
    if _digest(dest) != h.hexdigest():
        raise SnapshotError("copied file differs from source")
    return h.hexdigest()


def stage_snapshot(user: Path, which: str) -> Path:
    """Stage a new verified copy, never make it an active game save."""
    if which not in SOURCE_FOLDERS:
        raise SnapshotError("only solo and party save sources are supported")
    user = Path(user)
    _real_directory(user)
    source = user / SOURCE_FOLDERS[which]
    inventory = _files(source)
    if not inventory:
        raise SnapshotError("no complete save files in selected source")

    parent = user / "save_backups"
    if parent.exists() or parent.is_symlink():
        _real_directory(parent)
    else:
        parent.mkdir(mode=0o700)
    quarantine = parent / "ultimate_quarantine"
    if quarantine.exists() or quarantine.is_symlink():
        _real_directory(quarantine)
    else:
        quarantine.mkdir(mode=0o700)

    token = uuid.uuid4().hex
    partial = quarantine / (token + ".partial")
    ready = quarantine / (token + ".ready")
    partial.mkdir(mode=0o700)  # exclusive; no reuse of earlier partial copy
    promoted = False
    try:
        records = []
        for rel, original, size in inventory:
            target = partial.joinpath(*Path(rel).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = _copy_one(original, target)
            records.append({"path": rel, "size": size, "sha256": digest})
        # A successful byte-for-byte copy is insufficient if a second game
        # tick changed an earlier input during a later file's copy.
        refreshed = _files(source)
        if [(rel, size) for rel, _, size in refreshed] != [
                (record["path"], record["size"]) for record in records]:
            raise SnapshotError("source inventory changed during snapshot")
        for rel, original, _ in refreshed:
            record = next(x for x in records if x["path"] == rel)
            if _digest(original) != record["sha256"]:
                raise SnapshotError("source changed during verification")
        manifest = {
            "format": 1,
            "source_kind": which,
            "source_folder": SOURCE_FOLDERS[which],
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "files": records,
        }
        with (partial / MANIFEST).open("x", encoding="utf-8") as out:
            json.dump(manifest, out, ensure_ascii=False, sort_keys=True, indent=2)
            out.flush()
            os.fsync(out.fileno())
        if ready.exists() or ready.is_symlink():
            raise SnapshotError("snapshot destination already exists")
        partial.rename(ready)
        promoted = True
        verify_snapshot(ready)
        return ready
    except Exception:
        # Cleanup only the newly created random staging directory, NEVER
        # the original save or any previous complete snapshot.
        if partial.exists():
            shutil.rmtree(partial)
        # A failed post-promotion check must never leave an unverified
        # directory marked ".ready". Delete ONLY the unique one just created.
        if promoted and ready.exists():
            shutil.rmtree(ready)
        raise


def verify_snapshot(snapshot: Path) -> dict:
    snapshot = Path(snapshot)
    if snapshot.suffix != ".ready":
        raise SnapshotError("only completed snapshots can be verified")
    _real_directory(snapshot)
    manifest_path = snapshot / MANIFEST
    try:
        manifest_stat = manifest_path.lstat()
        if (not stat.S_ISREG(manifest_stat.st_mode) or
                manifest_path.is_symlink() or manifest_stat.st_size > 2 * 1024 * 1024):
            raise SnapshotError("unsafe or oversized snapshot manifest")
        with manifest_path.open("r", encoding="utf-8") as inp:
            manifest = json.load(inp)
    except (OSError, UnicodeError, ValueError) as exc:
        raise SnapshotError("missing or unreadable snapshot manifest") from exc
    if (not isinstance(manifest, dict) or manifest.get("format") != 1 or
            manifest.get("source_kind") not in SOURCE_FOLDERS or
            manifest.get("source_folder") != SOURCE_FOLDERS[manifest["source_kind"]]):
        raise SnapshotError("unrecognized snapshot manifest")
    expected = manifest.get("files")
    if not isinstance(expected, list) or not expected or len(expected) > MAX_FILES:
        raise SnapshotError("invalid file inventory")
    names = set()
    total = 0
    for record in expected:
        if not isinstance(record, dict):
            raise SnapshotError("invalid manifest record")
        rel, size, digest = record.get("path"), record.get("size"), record.get("sha256")
        if (not isinstance(rel, str) or not rel or rel.startswith("/") or
                "\\" in rel or any(x in ("", ".", "..") for x in rel.split("/")) or
                ":" in rel or rel == MANIFEST or rel.endswith(".bbtmp") or rel in names):
            raise SnapshotError("unsafe or duplicate manifest path")
        if (type(size) is not int or size < 0 or size > MAX_FILE_BYTES or
                not isinstance(digest, str) or len(digest) != 64 or
                any(x not in "0123456789abcdef" for x in digest)):
            raise SnapshotError("invalid manifest metadata")
        names.add(rel)
        total += size
        if total > MAX_TOTAL_BYTES:
            raise SnapshotError("snapshot exceeds protective size bound")
        path = snapshot.joinpath(*rel.split("/"))
        try:
            st = path.lstat()
        except OSError as exc:
            raise SnapshotError("missing snapshot file") from exc
        if not stat.S_ISREG(st.st_mode) or path.is_symlink():
            raise SnapshotError("snapshot contains a link or non-file")
        if st.st_size != size or _digest(path) != digest:
            raise SnapshotError("snapshot content checksum mismatch")
    actual = {rel for rel, _, _ in _files(snapshot) if rel != MANIFEST}
    if actual != names:
        raise SnapshotError("snapshot contains extra or missing files")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify-only offline game-save quarantine")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stage-user-dir", type=Path, help="offline COPY of a user's save root")
    group.add_argument("--verify", type=Path, help="existing .ready quarantine snapshot")
    parser.add_argument("--from", dest="which", choices=("solo", "party"))
    args = parser.parse_args(argv)
    try:
        if args.verify:
            info = verify_snapshot(args.verify)
            print("VERIFIED", len(info["files"]), "files")
        else:
            if not args.which:
                parser.error("--from is required with --stage-user-dir")
            snap = stage_snapshot(args.stage_user_dir, args.which)
            print("STAGED", snap.name, "NOT ACTIVE SAVE")
        return 0
    except (OSError, SnapshotError) as exc:
        print("SNAPSHOT_BLOCKED:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
