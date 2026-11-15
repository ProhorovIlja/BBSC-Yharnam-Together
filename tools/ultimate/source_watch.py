"""Inventory public Git heads/PR heads; ref discovery does not mean code review.

Snapshots contain full SHA/ref mappings for continuity. Compare two snapshots to
find changed refs before fetching source. This tool never merges or runs donors.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

REPOSITORY = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z')
SHA = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')
REF = re.compile(r'(?:refs/heads/.+|refs/pull/[1-9][0-9]*/head)\Z')


def parse_refs(text):
    refs = {}
    for line in text.splitlines():
        parts = line.split('\t')
        if len(parts) != 2 or not SHA.fullmatch(parts[0]) or not REF.fullmatch(parts[1]):
            raise ValueError('invalid Git ref response')
        sha, ref = parts
        if ref in refs and refs[ref] != sha:
            raise ValueError('conflicting duplicate ref')
        refs[ref] = sha
    if not refs:
        raise ValueError('no matching refs; do not interpret as removal of all source')
    return dict(sorted(refs.items()))


def discover(repository, timeout=40, runner=subprocess.run):
    if not REPOSITORY.fullmatch(repository):
        raise ValueError('expected a public GitHub owner/repository name')
    try:
        result = runner(['git', 'ls-remote', '--refs',
                         'https://github.com/' + repository + '.git',
                         'refs/heads/*', 'refs/pull/*/head'],
                        check=True, capture_output=True, text=True, timeout=timeout,
                        env=dict(os.environ, GIT_TERMINAL_PROMPT='0'))
        refs = parse_refs(result.stdout)
        return {'repository': repository, 'status': 'inventoried_not_reviewed',
                'heads': sum(r.startswith('refs/heads/') for r in refs),
                'pr_heads': sum(r.startswith('refs/pull/') for r in refs), 'refs': refs}
    except (subprocess.SubprocessError, OSError, ValueError) as error:
        # Do not retain provider stderr: custom Git configuration may put credentials there.
        return {'repository': repository, 'status': 'failed',
                'error_kind': type(error).__name__, 'refs': None}


def baseline_refs(previous):
    if not previous:
        return None
    if previous.get('status') == 'inventoried_not_reviewed':
        return previous.get('refs')
    return previous.get('last_successful_refs')


def carry_scan_history(current, previous):
    if current['status'] != 'inventoried_not_reviewed':
        old = baseline_refs(previous)
        if old is not None:
            current['last_successful_refs'] = old
    current['delta'] = changes(current, previous)


def changes(current, previous):
    if current['status'] != 'inventoried_not_reviewed':
        return {'status': 'unknown_due_to_failed_scan'}
    old = baseline_refs(previous)
    if old is None:
        return {'status': 'initial_inventory'}
    new = current['refs']
    return {'status': 'compared',
            'added': sorted(new.keys() - old.keys()),
            'removed': sorted(old.keys() - new.keys()),
            'changed': sorted(k for k in old.keys() & new.keys() if old[k] != new[k])}


def write_atomic(path, snapshot):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name + '.', delete=False) as output:
            temporary = Path(output.name)
            json.dump(snapshot, output, indent=2, sort_keys=True)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--workers', type=int, choices=range(1, 9), default=4)
    args = parser.parse_args()
    config = json.loads(args.sources.read_text(encoding='utf-8'))
    repos = config['repositories']
    if not repos or len(repos) != len(set(repos)) or any(not REPOSITORY.fullmatch(r) for r in repos):
        parser.error('source list must contain unique public owner/repository names')
    previous = {}
    if args.previous:
        baseline = json.loads(args.previous.read_text(encoding='utf-8'))
        if baseline.get('schema') != 1:
            parser.error('unsupported baseline schema')
        previous = {row['repository']: row for row in baseline['repositories']}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(discover, repos))
    for row in rows:
        carry_scan_history(row, previous.get(row['repository']))
    failed = sum(row['status'] == 'failed' for row in rows)
    snapshot = {'schema': 1, 'observed_at_utc': datetime.now(timezone.utc).isoformat(),
                'scope': 'configured public heads and PR heads only',
                'coverage': 'partial' if failed else 'all_configured_refs_inventoried',
                'semantic_review_complete': False, 'repositories': rows}
    write_atomic(args.output, snapshot)
    print(json.dumps({'repositories': len(rows), 'failed': failed,
                      'heads': sum(r.get('heads', 0) for r in rows),
                      'pr_heads': sum(r.get('pr_heads', 0) for r in rows),
                      'semantic_review_complete': False}))
    return 2 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
