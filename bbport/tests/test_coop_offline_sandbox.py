"""B36: a co-op distribution's OFFLINE button must not load co-op events or log in.

Tests import the real production bbport_coop.py and mods.py, using only
temporary dummy filesystem paths. Never run a Bloodborne executable or edit
a player save.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
sys.path.insert(0,str(ROOT/'scripts'))
import bbport_coop as coop
import mods


class OfflineCoopEnvironment(unittest.TestCase):
    def test_offline_reuses_the_same_character_save_folder_without_server_auth(self):
        with tempfile.TemporaryDirectory() as folder:
            install=Path(folder)/'install'
            root=Path(folder)/'view'
            env={
                'BB_ONLINE':'1','SHADPS4_BLOODBORNE_SEAMLESS_COOP':'1',
                'BB_SHADNET_SERVER':'bad.example:1','BB_SHADNET_WEBAPI':'http://bad.example',
                'BB_SHADNET_NPID':'private-player','BB_SHADNET_PASSWORD':'secret',
                'BB_SHADNET_SERVER_KEY':'server-key',
                'SHADPS4_BLOODBORNE_HOST_RULES':'online-rules',
                'SHADPS4_BLOODBORNE_PARTY':'old',
                'SHADPS4_BLOODBORNE_PARTY_ROLE':'old-role',
                'SHADPS4_P2P_PORT':'51610','BB_COMMUNITY_SERVER':'other.example',
                'BB_ONLINE_UNLOCKED_FPS':'1','BB_ONLINE_FPS_CAP':'120',
                'BB_MODS_ENABLED':'1','BB_PATCHES_DIR':'user-patches',
                'BB_FPS':'uncap'
            }
            offline=coop.offline_game_environment(env,install,root)
            self.assertNotIn('BB_ONLINE',offline)
            self.assertNotIn('SHADPS4_BLOODBORNE_SEAMLESS_COOP',offline)
            for key in ('BB_SHADNET_SERVER','BB_SHADNET_WEBAPI','BB_SHADNET_NPID',
                        'BB_SHADNET_PASSWORD','BB_SHADNET_SERVER_KEY',
                        'SHADPS4_BLOODBORNE_PARTY','SHADPS4_P2P_PORT',
                        'BB_COMMUNITY_SERVER','BB_ONLINE_UNLOCKED_FPS'):
                self.assertNotIn(key,offline,key)
            self.assertEqual(offline['BB_USER_DIR'],str(install/'user'))
            self.assertEqual(offline['BB_DATA_DIR'],str(install))
            self.assertEqual(offline['BB_CONFIG'],str(install/'bbport.ini'))
            self.assertEqual(offline['BB_GAME_DIR'],str(root/'CUSA03173'))
            self.assertEqual(offline['BB_IGNORE_LEGACY_GAME_MODS'],'1')
            self.assertEqual(offline['BB_PARTY_HUD'],'0')
            self.assertEqual(offline['BB_MODS_ENABLED'],'1')
            self.assertEqual(offline['BB_PATCHES_DIR'],'user-patches')
            self.assertEqual(offline['BB_FPS'],'uncap')
            self.assertEqual(env['BB_SHADNET_PASSWORD'],'secret') # no mutation of caller

    def test_only_offline_prepare_creates_update_view_not_coop_event_patch_or_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            install=Path(tmp)/'install'
            root=Path(tmp)/'view'
            game=Path(tmp)/'CUSA03173'
            game.mkdir()
            settings={'game':str(game),'update':'','prepared':'stale'}
            with (mock.patch.object(coop,'find_game_folder',return_value=game),
                  mock.patch.object(coop,'game_version',return_value=('Bloodborne',coop.GAME_VERSION)),
                  mock.patch.object(coop,'view_root',return_value=root),
                  mock.patch.object(coop,'view_complete',return_value=False),
                  mock.patch.object(coop,'build_game_view') as build,
                  mock.patch.object(coop,'copy_events',side_effect=AssertionError('co-op events were copied')),
                  mock.patch.object(coop,'global_game_settings',
                                    side_effect=AssertionError('online server was contacted'))):
                self.assertEqual(coop.prepare_offline_game(install,settings),root)
                build.assert_called_once_with(game,None,root/'CUSA03173')

    def test_reuses_verified_109_view_without_regenerating_coop_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            install=Path(tmp)/'install'
            root=Path(tmp)/'view'
            game=Path(tmp)/'CUSA03173'
            settings={'game':str(game),'update':''}
            settings['prepared']=coop.prepared_key(settings)
            with (mock.patch.object(coop,'find_game_folder',return_value=game),
                  mock.patch.object(coop,'game_version',return_value=('Bloodborne',coop.GAME_VERSION)),
                  mock.patch.object(coop,'view_root',return_value=root),
                  mock.patch.object(coop,'view_complete',return_value=True),
                  mock.patch.object(coop,'build_game_view') as build):
                self.assertEqual(coop.prepare_offline_game(install,settings),root)
                build.assert_not_called()


class OfflineModSelection(unittest.TestCase):
    def test_skip_only_automatic_coop_events_not_the_users_other_mods(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            game=root/'CUSA03173'
            game.mkdir()
            legacy=root/'CUSA03173-mods'/'dvdroot_ps4'/'event'
            legacy.mkdir(parents=True)
            (legacy/'common.emevd.dcx').write_bytes(b'placeholder')
            mods_dir=root/'mods'
            chosen=mods_dir/'visual-style'/'dvdroot_ps4'/'parts'
            chosen.mkdir(parents=True)
            (chosen/'costume.partsbnd.dcx').write_bytes(b'placeholder')
            with_legacy=mods.user_layers(game,mods_dir,enabled='1')
            offline=mods.user_layers(game,mods_dir,enabled='1',include_legacy=False)
            self.assertEqual([name for name,_ in with_legacy],
                             ['CUSA03173-mods','visual-style'])
            self.assertEqual([name for name,_ in offline],['visual-style'])
            self.assertEqual(mods.user_layers(game,mods_dir,enabled='0',include_legacy=False),[])

    def test_full_game_preparation_actually_forwards_ignore_legacy_flag(self):
        run=(ROOT/'run.py').read_text(encoding='utf-8')
        mod=(ROOT/'scripts'/'mods.py').read_text(encoding='utf-8')
        launcher=(ROOT/'launcher'/'bbport_launcher_win.py').read_text(encoding='utf-8')
        self.assertIn("env.get('BB_IGNORE_LEGACY_GAME_MODS') == '1'",run)
        self.assertIn("args.append('--ignore-legacy')",run)
        self.assertIn("include_legacy=not args.ignore_legacy",mod)
        self.assertIn('self.play_coop_offline',launcher)
        self.assertIn('self.coop_prepare_offline',launcher)
        self.assertIn('bbport_coop.offline_game_environment(',launcher)
        snippet=launcher.split('def coop_prepare_offline(self, settings):',1)[1].split(
            'def coop_start_offline(self, root, failed):',1)[0]
        for forbidden in ('coop_firewall','resolve_host','global_game_settings',
                          'send_reports','game_environment'):
            self.assertNotIn(forbidden,snippet)


if __name__=='__main__':
    unittest.main()
