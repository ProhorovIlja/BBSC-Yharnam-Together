"""B38: global server dropdown persistence and account isolation, no real network.

Run on Windows and Linux with the real production co-op settings module.
"""
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
import bbport_coop as coop


class ProfileStorage(unittest.TestCase):
    def test_unlimited_profile_urls_and_safe_https_validation(self):
        settings=dict(coop.DEFAULTS)
        for i in range(24):
            settings=coop.add_global_profile(settings,f'https://region{i}.example.org:44{i%10}')
        self.assertEqual(len(coop.global_profiles(settings)),25)
        self.assertEqual(coop.global_profiles(settings)[0],coop.GLOBAL_SERVER)
        settings=coop.add_global_profile(settings,'  HTTPS://REGION1.EXAMPLE.ORG:441/  ')
        self.assertEqual(len(coop.global_profiles(settings)),25)
        self.assertEqual(coop.profile_url('https://example.org/'), 'https://example.org')
        for url in ('http://example.org','ftp://example.org','https://u:pass@example.org',
                    'https://example.org/?secret=pass','https://example.org/#fragment',
                    'https://example.org:99999','https://','javascript://abc',
                    'https://domain with spaces.com','https://example.org:0'):
            with self.subTest(url=url):
                self.assertEqual(coop.profile_url(url),'')
                with self.assertRaises(ValueError):
                    coop.add_global_profile(settings,url)
        with self.assertRaises(ValueError):
            coop.add_global_profile(settings,'https://good.example.org','x'*65)

    def test_selected_url_account_name_and_secret_are_isolated_by_host(self):
        a=coop.GLOBAL_SERVER
        b='https://dedicated.example.org:443'
        t=int(time.time())
        secret_a=f'{t:08x}'+'a'*32
        secret_b=f'{t:08x}'+'b'*32
        settings=dict(coop.DEFAULTS,server_type='global',global_server=a)
        settings=coop.signed_in_global(settings,{'id':'hunterone','secret':secret_a,'name':'First Hunter'})
        self.assertEqual(settings['global_name'],'First Hunter')
        self.assertTrue(coop.is_signed_in_global(settings))
        settings=coop.add_global_profile(settings,b,'Dedicated EU')
        settings=coop.select_global_profile(settings,b)
        self.assertEqual(settings['global_name'],'')
        self.assertFalse(coop.is_signed_in_global(settings))
        self.assertEqual(coop.global_url(settings),b)
        self.assertEqual(coop.profile_label(settings,b),'Dedicated EU')
        self.assertNotEqual(coop.player_id_for(settings,b)[0],'hunterone')
        settings=coop.signed_in_global(settings,{'id':'huntertwo','secret':secret_b,'name':'Second Hunter'})
        self.assertEqual(settings['global_name'],'Second Hunter')
        self.assertTrue(coop.is_signed_in_global(settings))
        self.assertEqual(coop.player_id_for(settings,b),('huntertwo',secret_b))
        settings=coop.select_global_profile(settings,a)
        self.assertEqual(settings['global_name'],'First Hunter')
        self.assertEqual(coop.player_id_for(settings,a),('hunterone',secret_a))
        settings=coop.select_global_profile(settings,b)
        settings=coop.signed_out_global(settings)
        self.assertFalse(coop.is_signed_in_global(settings))
        self.assertEqual(settings['global_name'],'')
        self.assertIn(coop.server_key(a),settings['server_ids'])
        self.assertNotIn(coop.server_key(b),settings['server_ids'])
        settings=coop.select_global_profile(settings,a)
        self.assertTrue(coop.is_signed_in_global(settings))
        self.assertEqual(settings['global_name'],'First Hunter')

    def test_persist_and_migrate_old_one_server_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            install=Path(directory)
            old=dict(coop.DEFAULTS,global_server='https://old.example.org',
                     global_name='LegacyName',server_type='global')
            old['server_ids']={'https://old.example.org':['legacyhunter','01234567'+'a'*32]}
            coop.save_settings(install,old)
            recovered=coop.read_settings(install)
            self.assertIn('https://old.example.org',coop.global_profiles(recovered))
            self.assertEqual(recovered['global_name'],'LegacyName')
            self.assertEqual(recovered['server_names']['https://old.example.org'],'LegacyName')
            new=coop.add_global_profile(recovered,'https://new.example.org')
            new=coop.select_global_profile(new,'https://new.example.org')
            self.assertEqual(new['global_name'],'')
            coop.save_settings(install,new)
            again=coop.read_settings(install)
            self.assertEqual(again['global_server'],'https://new.example.org')
            self.assertEqual(again['global_name'],'')
            self.assertEqual(len(coop.global_profiles(again)),3)
            again=coop.select_global_profile(again,'https://old.example.org')
            self.assertEqual(again['global_name'],'LegacyName')

    def test_remove_custom_server_only_deletes_its_local_credentials_and_pinning(self):
        settings=dict(coop.DEFAULTS,server_type='global',global_server='https://private.example.org',
                      global_name='PrivateHunter')
        settings=coop.add_global_profile(settings,'https://private.example.org')
        settings['server_ids']={'https://private.example.org':['private','a'*40],
                                coop.GLOBAL_SERVER:['public','b'*40]}
        settings['server_keys']={'https://private.example.org':'c'*64,
                                  coop.GLOBAL_SERVER:'d'*64}
        settings=coop.remove_global_profile(settings,'https://private.example.org')
        self.assertEqual(coop.global_url(settings),coop.GLOBAL_SERVER)
        self.assertNotIn('https://private.example.org',coop.global_profiles(settings))
        self.assertNotIn('https://private.example.org',settings['server_ids'])
        self.assertNotIn('https://private.example.org',settings['server_keys'])
        self.assertIn(coop.GLOBAL_SERVER,settings['server_keys'])
        with self.assertRaises(ValueError):
            coop.remove_global_profile(settings,coop.GLOBAL_SERVER)

    def test_b37_hunters_count_goes_to_selected_url_not_previous_server(self):
        settings=dict(coop.DEFAULTS,server_type='global')
        settings=coop.add_global_profile(settings,'https://other.example.org')
        settings=coop.select_global_profile(settings,'https://other.example.org')
        requested=[]
        def fetch(url,timeout):
            requested.append((url,timeout))
            return {'shards':[{'name':'shard-1','players':4}]}
        self.assertEqual(coop.hunters_online(settings,fetch),{'hunters':4,'shards':1})
        self.assertEqual(requested,[('https://other.example.org/v1/shards',5)])

    def test_production_ui_dropdown_has_auth_async_server_guard(self):
        source=(ROOT/'launcher'/'bbport_launcher_win.py').read_text(encoding='utf-8')
        for needed in ('self.coop_profile_menu = self.ttk.Combobox',
                       'def coop_profile_chosen(self, _event=None):',
                       'self.coop.update(bbport_coop.select_global_profile(self.coop, url))',
                       'def coop_profile_add(self):',
                       'def coop_profile_remove(self):',
                       'self.coop_auth_clear()',
                       'self.hunters_next_poll = 0.0',
                       'self.coop_profile_busy()',
                       'self.coop_auth_answered(view, account, failed, url)',
                       'bbport_coop.server_key(requested_url)'):
            self.assertIn(needed,source)


if __name__=='__main__':
    unittest.main()
