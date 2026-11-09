"""B39: LAN/VPN adapter preflight, no real discovery sockets or game runtime.

The Windows adapter inventory uses only an injected PowerShell response.
This test NEVER sends traffic, changes firewall, accesses game files, reads
passwords or connects to a running server.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
import bbport_party_network as party


def row(uid,name,addr,prefix,description=''):
    return {'id':uid,'name':name,'address':addr,'prefix':prefix,
            'description':description}


class NetworkSourceTests(unittest.TestCase):
    def setUp(self):
        self.rows=[
            row('eth','Ethernet','192.168.10.33',24,'Intel Ethernet'),
            row('rd','Radmin VPN','26.2.3.4',8,'Radmin VPN adapter'),
            row('ts','Tailscale','100.101.102.103',32,'Tailscale Tunnel'),
            row('zt','ZeroTier One','172.22.5.2',24,'ZeroTier Virtual Port'),
            row('public','Ethernet public','8.8.8.8',24,'External NIC'),
            row('invalid','Loopback','127.0.0.1',8),
            row('multicast','MC','239.1.1.1',24),
            row('badprefix','Radmin bad','26.3.4.5',33),
        ]
        self.nic=party.adapter_inventory(json.dumps(self.rows))
        self.by_id={n['value'].split(':',1)[1]:n for n in self.nic}

    def test_parse_realistic_windows_nic_inventory_and_vpn_provider(self):
        self.assertEqual(len(self.nic),5)
        self.assertEqual(self.by_id['rd']['provider'],'radmin')
        self.assertEqual(self.by_id['ts']['provider'],'tailscale')
        self.assertEqual(self.by_id['zt']['provider'],'zerotier')
        self.assertEqual(self.by_id['eth']['provider'],'lan')
        self.assertEqual(self.by_id['public']['provider'],'lan')
        self.assertEqual(self.by_id['rd']['ranges'],['26.0.0.0/8'])
        self.assertEqual(self.by_id['zt']['ranges'],['172.22.5.0/24'])
        self.assertEqual(self.by_id['ts']['ranges'],['100.101.102.103/32'])

    def test_ambiguous_network_requires_explicit_vpn_or_adapter_selection(self):
        with self.assertRaises(party.PartyNetworkError):
            party.choose_adapter(self.nic,'auto')
        self.assertEqual(party.choose_adapter(self.nic,'radmin')['value'],'adapter:rd')
        self.assertEqual(party.choose_adapter(self.nic,'tailscale')['value'],'adapter:ts')
        self.assertEqual(party.choose_adapter(self.nic,'zerotier')['value'],'adapter:zt')
        with self.assertRaises(party.PartyNetworkError):
            party.choose_adapter(self.nic,'lan')
        self.assertEqual(party.choose_adapter(self.nic,'lan','adapter:eth')['value'],'adapter:eth')
        with self.assertRaises(party.PartyNetworkError):
            party.choose_adapter(self.nic,'custom')
        with self.assertRaises(party.PartyNetworkError):
            party.choose_adapter([], 'radmin')

    def test_selected_nic_targets_only_its_own_lan_or_vpn_broadcast(self):
        self.assertEqual(party.discovery_targets(self.by_id['eth']),['192.168.10.255'])
        self.assertEqual(party.discovery_targets(self.by_id['rd']),['26.255.255.255'])
        self.assertEqual(party.discovery_targets(self.by_id['zt']),['172.22.5.255'])
        self.assertEqual(party.discovery_targets(self.by_id['public']),[])
        self.assertEqual(party.party_available(self.nic,'zerotier'),{
            'provider':'zerotier','adapter':'adapter:zt',
            'local_address':'172.22.5.2','targets':['172.22.5.255']})

    def test_tailscale_uses_verified_online_cli_peers_not_broadcast(self):
        status={'BackendState':'Running','Peer':{
            'peer-a':{'Online':True,'TailscaleIPs':['100.101.2.3','fd7a::1']},
            'peer-b':{'Online':False,'TailscaleIPs':['100.102.4.5']},
            'peer-c':{'Online':True,'TailscaleIPs':['100.101.102.103','100.103.9.7',
                                                   '8.8.8.8','not-an-ip']}}}
        self.assertEqual(party.discovery_targets(self.by_id['ts'],status),
                         ['100.101.2.3','100.103.9.7'])
        self.assertEqual(party.tailscale_peer_addresses(status),
                         {'100.101.102.103','100.101.2.3','100.103.9.7'})
        self.assertEqual(party.tailscale_peer_addresses(dict(status,BackendState='Stopped')),set())
        self.assertEqual(party.tailscale_peer_addresses('bad json'),set())
        with self.assertRaises(party.PartyNetworkError):
            party.discovery_targets(self.by_id['ts'])
        self.assertEqual(party.party_available(self.nic,'tailscale',tailscale_status=status)['targets'],
                         ['100.101.2.3','100.103.9.7'])

    def test_no_public_ipv4_adapter_broadcast_or_unrestricted_scan(self):
        self.assertFalse(party.discovery_targets(self.by_id['public']))
        nic=dict(self.by_id['eth'],ranges=['0.0.0.0/0','192.168.0.0/16','239.1.0.0/16',
                                          '192.0.2.0/24','bad subnet'])
        self.assertEqual(party.discovery_targets(nic),['192.168.255.255'])
        nic=dict(self.by_id['eth'],provider='unknown')
        with self.assertRaises(party.PartyNetworkError):
            party.discovery_targets(nic)

    def test_bad_json_and_nonpreferred_addresses_have_no_network_effect(self):
        for bad in ('{invalid','x'*262145,'[]oops','{}'):
            self.assertEqual(party.adapter_inventory(bad),[])
        self.assertEqual(party.adapter_inventory([row('x','bad','169.254.1.2',16)]),[])
        self.assertEqual(party.adapter_inventory([row('x','bad','192.168.1.2',True)]),[])
        self.assertEqual(party.adapter_inventory([row('x','bad','192.168.1.2','24')]),[])
        self.assertEqual(party.adapter_inventory([row('x','bad','192.168.1.2',24)]*257),[])
        self.assertEqual(party.adapter_inventory({}),[])

    def test_native_windows_adapter_command_is_fixed_not_user_supplied(self):
        called={}
        class Result:
            returncode=0
            stdout=json.dumps([row('zt','ZeroTier Virtual','172.22.5.2',24)])
        def fake_runner(command,**opts):
            called.update(command=command,opts=opts)
            return Result()
        found=party.windows_network_candidates(fake_runner)
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]['provider'],'zerotier')
        self.assertIn('Get-NetAdapter',called['command'][-1])
        self.assertEqual(called['command'][:3],
                         ['powershell.exe','-NoProfile','-NonInteractive'])
        self.assertEqual(called['opts']['timeout'],10)
        self.assertTrue(called['opts']['capture_output'])
        def error_runner(*args,**opts):
            raise OSError('powershell unavailable')
        self.assertEqual(party.windows_network_candidates(error_runner),[])


if __name__ == '__main__':
    unittest.main()
