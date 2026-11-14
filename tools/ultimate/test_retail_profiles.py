# SPDX-License-Identifier: GPL-2.0-or-later
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from retail_profiles import IntakeError, load_registry, select


class Profiles(unittest.TestCase):
    def setUp(self):
        self.report = {'title_id': 'CUSA03173', 'app_ver': '01.09',
                       'eboot': {'size': 1024, 'sha256': 'a' * 64}}
        self.profile = {'id': 'fixture', 'target': 'windows-x64', 'title_ids': ['CUSA03173'],
                        'eboot': dict(self.report['eboot']), 'recipe_sha256': 'b' * 64}

    def read(self, data):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'registry.json'
            path.write_text(data, encoding='utf-8')
            return load_registry(path)

    def test_exact_recipe(self):
        profiles = self.read(json.dumps({'schema': 1, 'profiles': [self.profile]}))
        first = select(self.report, 'windows-x64', profiles)
        self.assertEqual(first['status'], 'profile_selected_not_prepared')
        self.assertEqual(first['target'], 'windows-x64')
        self.assertEqual(first, select(self.report, 'windows-x64', profiles))
        profiles[0]['recipe_sha256'] = 'c' * 64
        self.assertNotEqual(first['selection_key'], select(self.report, 'windows-x64', profiles)['selection_key'])

    def test_unknown_and_mismatch(self):
        for report, target, profiles in [
            (self.report, 'windows-x64', []),
            (self.report, 'linux-x64', [self.profile]),
            (dict(self.report, title_id='CUSA00900'), 'windows-x64', [self.profile]),
            (dict(self.report, app_ver='01.00'), 'windows-x64', [self.profile]),
            (dict(self.report, eboot={'size': 1024, 'sha256': 'f' * 64}), 'windows-x64', [self.profile]),
        ]:
            with self.subTest(report=report, target=target), self.assertRaisesRegex(IntakeError, 'no_verified_profile'):
                select(report, target, profiles)

    def test_explicit_alias(self):
        self.profile['title_ids'].append('CUSA00900')
        self.assertEqual(select(dict(self.report, title_id='CUSA00900'), 'windows-x64', [self.profile])['profile'],
                         'fixture')

    def test_ambiguity(self):
        with self.assertRaisesRegex(IntakeError, 'ambiguous_profile'):
            select(self.report, 'windows-x64', [self.profile, dict(self.profile, id='other')])

    def test_invalid_registries(self):
        for raw in ['{"schema":1,"schema":1,"profiles":[]}', '{"schema":true,"profiles":[]}',
                    json.dumps({'schema': 1, 'profiles': [dict(self.profile, eboot={'size': True, 'sha256': 'a' * 64})]}),
                    json.dumps({'schema': 1, 'profiles': [dict(self.profile, target='unknown')]})]:
            with self.subTest(raw=raw), self.assertRaisesRegex(IntakeError, 'invalid_profile_registry'):
                self.read(raw)
