"""B39: local host anonymous Link-count status uses the real co-op client module.

The fake server here never accesses a real network or proprietary game file.
The production C++ Link hub updates the SharedState aggregate and /status.
"""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
import bbport_coop as coop


class LocalHostCountTests(unittest.TestCase):
    def local(self,host='26.50.60.70'):
        return {'server_type':'local','host_ip':host}

    def test_connected_link_members_are_read_from_the_chosen_local_host(self):
        urls=[]
        def fetch(url,timeout):
            urls.append((url,timeout))
            return {'ok':True,'service':'shadnet-webapi','link_members':5}
        self.assertEqual(coop.local_hunters_online(self.local(),fetch),
                         {'hunters':5,'shards':1})
        self.assertEqual(urls,[('http://26.50.60.70:31315/status',4)])

    def test_verified_zero_is_not_network_failure_or_old_server(self):
        self.assertEqual(coop.local_hunters_online(self.local(),lambda u,timeout:{
            'ok':True,'service':'shadnet-webapi','link_members':0}),
            {'hunters':0,'shards':1})
        self.assertIsNone(coop.local_hunters_online(self.local(),lambda u,timeout:{
            'ok':True,'service':'shadnet-webapi'}))  # old server without new API
        self.assertIsNone(coop.local_hunters_online(self.local(),lambda u,timeout:{
            'ok':True,'service':'other-server','link_members':0}))

    def test_garbage_or_unsupported_status_never_claims_zero(self):
        invalid=[None, {}, [], {'ok':True}, {'ok':False,'service':'shadnet-webapi','link_members':5},
                 {'ok':1,'service':'shadnet-webapi','link_members':5},
                 {'ok':True,'service':'shadnet-webapi','link_members':-1},
                 {'ok':True,'service':'shadnet-webapi','link_members':True},
                 {'ok':True,'service':'shadnet-webapi','link_members':'5'},
                 {'ok':True,'service':'shadnet-webapi','link_members':100001},
                 {'ok':True,'service':'shadnet-webapi','link_members':3.5}]
        for answer in invalid:
            with self.subTest(answer=answer):
                self.assertIsNone(coop.local_hunters_online(self.local(),
                                             lambda url,timeout:answer))

    def test_no_probe_when_local_address_invalid_or_server_is_global(self):
        def forbidden(url,timeout):
            raise AssertionError('no network access allowed')
        for host in ('', '127.0.0.1','http://example.org',
                     'https://example.org','10.0.0.1/evil','a:bad',
                     'user:pass@host.example.org','localhost'):
            with self.subTest(host=host):
                self.assertIsNone(coop.local_hunters_online(self.local(host),forbidden))
        self.assertIsNone(coop.local_hunters_online({'server_type':'global',
                            'host_ip':'26.50.60.70'},forbidden))

    def test_timeout_and_unparseable_data_are_unknown_not_zero(self):
        for error in (TimeoutError('timed out'),OSError('host down'),
                      ValueError('invalid JSON'),TypeError('invalid data')):
            def failure(url,timeout):
                raise error
            self.assertIsNone(coop.local_hunters_online(self.local(),failure))

    def test_production_server_exposes_live_hub_member_count_abstracted_from_identities(self):
        shared=(ROOT.parent/'server/src/client_session.h').read_text(encoding='utf-8')
        link=(ROOT.parent/'server/src/link_server.cpp').read_text(encoding='utf-8')
        web=(ROOT.parent/'server/src/webapi_server.cpp').read_text(encoding='utf-8')
        launcher=(ROOT/'launcher'/'bbport_launcher_win.py').read_text(encoding='utf-8')
        self.assertIn('std::atomic<int> linkMembers{0};',shared)
        self.assertIn('m_shared->linkMembers.store(static_cast<int>(m_link.Members())',link)
        self.assertIn('shared->linkMembers.load(std::memory_order_relaxed)',web)
        self.assertIn('body.insert("link_members"',web)
        self.assertNotIn('body.insert("players"',web)
        self.assertNotIn('body.insert("accounts"',web)
        self.assertIn('bbport_coop.local_hunters_online(settings)',launcher)
        self.assertIn("settings.get('host_ip', '')",launcher)
        self.assertIn('self.hunters_next_poll = now + 45.0',launcher)


if __name__=='__main__':
    unittest.main()
