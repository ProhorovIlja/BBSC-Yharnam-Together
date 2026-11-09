"""B37: public shard occupancy is not guessed, leaked or requested on the UI thread.

These tests import the real production bbport_coop launcher module. They do
not contact a network, load game files or use actual player credentials.
"""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
import bbport_coop as coop


class DirectoryCountTests(unittest.TestCase):
    def settings(self,typ='global',url='https://eu.example.org'):
        return {'server_type':typ,'global_server':url}

    def test_two_active_shards_sum_and_no_private_fields_returned(self):
        captured=[]
        def fetch(url,timeout):
            captured.append((url,timeout))
            return {'shards':[
                {'name':'eu-1','players':2,'capacity':100,'address':'10.0.0.1:31313',
                 'member':'private','secret':'never pass this'},
                {'name':'eu-2','players':3,'capacity':100,'address':'10.0.0.2:31313',
                 'name_extras':['hidden']}]}
        result=coop.hunters_online(self.settings(),fetch)
        self.assertEqual(result,{'hunters':5,'shards':2})
        self.assertEqual(captured,[('https://eu.example.org/v1/shards',5)])
        self.assertNotIn('members',result)
        self.assertNotIn('secret',result)

    def test_empty_directory_is_zero_but_empty_error_is_unknown(self):
        self.assertEqual(coop.hunters_online(self.settings(),
                         lambda url,timeout:{'shards':[]}),{'hunters':0,'shards':0})
        for answer in (None, {}, {'error':'not found'}, {'shards':None},
                       {'shards':{}}, {'shards':'nope'}, []):
            with self.subTest(answer=answer):
                self.assertIsNone(coop.hunters_online(self.settings(),
                                      lambda url,timeout:answer))

    def test_unknown_local_or_invalid_url_never_sends_request(self):
        def forbidden(url,timeout):
            raise AssertionError('network must not be accessed')
        self.assertIsNone(coop.hunters_online(self.settings('local'),forbidden))
        self.assertIsNone(coop.hunters_online(self.settings('global','http://bad.example.org'),forbidden))
        self.assertIsNone(coop.hunters_online(self.settings('global','https://bad.example.org:99999'),forbidden))
        self.assertIsNone(coop.hunters_online(self.settings('global','https://other.example.org/path?password=secret'),forbidden))

    def test_malformed_counts_and_duplicate_shards_do_not_fake_total(self):
        bad=[
            {'name':'eu','players':-1},
            {'name':'eu','players':True},
            {'name':'eu','players':1.0},
            {'name':'eu','players':'7'},
            {'name':'eu','players':100001},
            {'name':'','players':1},
            {'name':'x'*129,'players':1},
            {'players':7},
            'bad-shard'
        ]
        for item in bad:
            with self.subTest(item=item):
                self.assertIsNone(coop.hunters_online(self.settings(),
                            lambda url,timeout:{'shards':[item]}))
        self.assertIsNone(coop.hunters_online(self.settings(),
                          lambda url,timeout:{'shards':[{'name':'eu','players':2},
                                                          {'name':'eu','players':3}]}))
        self.assertIsNone(coop.hunters_online(self.settings(),
                          lambda url,timeout:{'shards':[{'name':str(n),'players':1}
                                                          for n in range(513)]}))

    def test_failure_is_unknown_and_no_tls_bypass_allowed(self):
        for error in (TimeoutError('no response'),OSError('unreachable'),
                      ValueError('invalid JSON'),TypeError('invalid data')):
            with self.subTest(error=type(error).__name__):
                def fail(url,timeout):
                    raise error
                self.assertIsNone(coop.hunters_online(self.settings(),fail))
        launcher=(ROOT/'launcher'/'bbport_launcher_win.py').read_text(encoding='utf-8')
        self.assertIn('self.coop_check_hunters',launcher)
        self.assertIn('self.hunters_next_poll = now + 45.0',launcher)
        self.assertIn('threading.Thread(target=self.coop_check_hunters',launcher)
        self.assertIn("if self._closing or key != self.hunters_last_key",launcher)
        self.assertNotIn('verify=False',launcher)


if __name__=='__main__':
    unittest.main()
