# SPDX-License-Identifier: GPL-2.0-or-later
"""Select an exact developer-reviewed preparation profile, never launch the game."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from retail_intake import IntakeError, MAX_EXEC, inspect

TARGETS = {'windows-x64', 'linux-x64', 'macos-arm64'}
MAX_REGISTRY = 128 * 1024


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def load_registry(path):
    with path.open('rb') as stream:
        data = stream.read(MAX_REGISTRY + 1)
    if len(data) > MAX_REGISTRY:
        raise IntakeError('invalid_profile_registry')
    try:
        doc = json.loads(data, object_pairs_hook=unique)
        if (type(doc) is not dict or set(doc) != {'schema', 'profiles'} or
                type(doc['schema']) is not int or doc['schema'] != 1 or
                type(doc['profiles']) is not list):
            raise ValueError('schema')
        seen = set()
        for p in doc['profiles']:
            if (type(p) is not dict or set(p) != {'id', 'target', 'title_ids', 'eboot', 'recipe_sha256'}
                    or not re.fullmatch('[a-z0-9-]{1,64}', p['id']) or p['id'] in seen
                    or p['target'] not in TARGETS or not re.fullmatch('[0-9a-f]{64}', p['recipe_sha256'])
                    or type(p['title_ids']) is not list or not p['title_ids']
                    or any(not re.fullmatch('CUSA[0-9]{5}', t) for t in p['title_ids'])
                    or len(set(p['title_ids'])) != len(p['title_ids'])
                    or set(p['eboot']) != {'sha256', 'size'}
                    or not re.fullmatch('[0-9a-f]{64}', p['eboot']['sha256'])
                    or type(p['eboot']['size']) is not int or not 64 <= p['eboot']['size'] <= MAX_EXEC):
                raise ValueError('profile')
            seen.add(p['id'])
        return doc['profiles']
    except (TypeError, ValueError, KeyError, RecursionError) as exc:
        raise IntakeError('invalid_profile_registry') from exc


def select(report, target, profiles):
    matches = [p for p in profiles if p['target'] == target and report['title_id'] in p['title_ids']
               and report['app_ver'] == '01.09' and p['eboot'] == report['eboot']]
    if len(matches) != 1:
        raise IntakeError('ambiguous_profile' if matches else 'no_verified_profile')
    p = matches[0]
    key = json.dumps([1, p['id'], target, report['title_id'], report['app_ver'], report['eboot'],
                      p['recipe_sha256']], sort_keys=True, separators=(',', ':')).encode('ascii')
    return {'schema': 1, 'status': 'profile_selected_not_prepared', 'profile': p['id'],
            'target': target, 'recipe_sha256': p['recipe_sha256'],
            'selection_key': hashlib.sha256(key).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('game', type=Path)
    ap.add_argument('registry', type=Path, help='developer-reviewed registry; not supplied by the game dump')
    ap.add_argument('target', choices=sorted(TARGETS))
    args = ap.parse_args()
    try:
        result = select(inspect(args.game), args.target, load_registry(args.registry))
    except (IntakeError, OSError, RuntimeError) as exc:
        print(json.dumps({'schema': 1, 'status': 'rejected',
                          'reason': str(exc) if isinstance(exc, IntakeError) else 'cannot_read_input'}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
