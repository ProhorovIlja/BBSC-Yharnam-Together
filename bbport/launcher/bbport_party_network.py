# SPDX-License-Identifier: GPL-2.0-or-later
"""LAN/VPN Party preflight primitives, NO GAME SESSION and NO SOCKET LISTENER.

Inspired by the selected-NIC discovery patterns in mark3317/bbgl
(launcher/bbport_coop.py and launcher/bbport_party.py, GPL-2.0).
This independent module is intentionally OFF until Ultimate's authenticated
local Party / Link4 bridge exists. Never discover via an unrelated adapter.
"""
import ipaddress
import json
import os
import re
import subprocess

NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
TAILNET = ipaddress.IPv4Network('100.64.0.0/10')
# ipaddress.is_private also accepts RFC 5737 test ranges on some Python
# versions. Ordinary physical LAN broadcast must be limited to RFC 1918.
HOME_LAN = tuple(ipaddress.IPv4Network(net) for net in
                 ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))
PROVIDERS = ('radmin', 'tailscale', 'zerotier')
# This program does NOT take commands or values from third-party network data.
WINDOWS_ADAPTER_QUERY = r"""Get-NetAdapter | Where-Object Status -eq 'Up' | ForEach-Object {
  $nic = $_
  Get-NetIPAddress -InterfaceIndex $nic.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
  Where-Object AddressState -eq 'Preferred' | ForEach-Object {
    [pscustomobject]@{
      id=[string]$nic.InterfaceGuid;
      name=[string]$nic.Name;
      description=[string]$nic.InterfaceDescription;
      address=[string]$_.IPAddress;
      prefix=[int]$_.PrefixLength
    }
  }
} | ConvertTo-Json -Compress"""


class PartyNetworkError(ValueError):
    """An unambiguous selected LAN/VPN adapter or safe target list is needed."""


def _provider(text):
    """Recognize provider by OS adapter metadata, not IP range alone."""
    value=text.lower()
    if 'tailscale' in value:
        return 'tailscale'
    if 'radmin' in value:
        return 'radmin'
    if 'zerotier' in value or 'zero tier' in value:
        return 'zerotier'
    if any(word in value for word in ('wireguard','hamachi','openvpn','wintun',
                                       'tap-windows','vpn')):
        return 'vpn-other'
    return 'lan'


def adapter_inventory(payload):
    """Parse bounded Windows PowerShell JSON into stable, source-only NIC records."""
    if isinstance(payload, bytes):
        payload=payload.decode('utf-8-sig', errors='strict')
    if isinstance(payload,str):
        if len(payload)>262144:
            return []
        try:
            rows=json.loads(payload or '[]')
        except ValueError:
            return []
    else:
        rows=payload
    if isinstance(rows,dict):
        rows=[rows]
    if not isinstance(rows,list) or len(rows)>256:
        return []
    records={}
    for row in rows:
        if not isinstance(row,dict):
            continue
        name,identity,description=row.get('name'),row.get('id'),row.get('description','')
        if not isinstance(name,str) or not 0<len(name)<=128:
            continue
        if not isinstance(identity,str) or not 0<len(identity)<=128:
            continue
        if not isinstance(description,str) or len(description)>256:
            continue
        try:
            ip=ipaddress.IPv4Address(row['address'])
            length=row['prefix']
            if type(length) is not int or not 0<=length<=32:
                continue
            net=ipaddress.IPv4Network(f'{ip}/{length}',strict=False)
        except (ValueError,KeyError,TypeError,ipaddress.AddressValueError):
            continue
        if ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast:
            continue
        key='adapter:'+identity
        provider=_provider(name+' '+description)
        candidate=records.setdefault(key,{'value':key,'text':name,'provider':provider,
                                          'vpn':provider!='lan','addresses':[],
                                          'ranges':[]})
        if str(ip) not in candidate['addresses']:
            candidate['addresses'].append(str(ip))
        if str(net) not in candidate['ranges']:
            candidate['ranges'].append(str(net))
    return sorted(records.values(),key=lambda nic:(not nic['vpn'],nic['text'].casefold()))


def windows_network_candidates(runner=None):
    """Read local NIC metadata only; no DNS, VPN login, port scanning or network packets."""
    if runner is None:
        runner=subprocess.run
    try:
        result=runner(['powershell.exe','-NoProfile','-NonInteractive','-Command',
                       WINDOWS_ADAPTER_QUERY],capture_output=True,text=True,
                      timeout=10,creationflags=NO_WINDOW)
        if result.returncode:
            return []
        return adapter_inventory(result.stdout)
    except (OSError,ValueError,UnicodeError,subprocess.SubprocessError):
        return []


def choose_adapter(candidates,mode='auto',selected=None):
    """Never guess between two VPNs/networks; require a precise interface choice."""
    if selected:
        eligible=[nic for nic in candidates if nic.get('value')==selected]
    elif mode in PROVIDERS:
        eligible=[nic for nic in candidates if nic.get('provider')==mode]
    elif mode=='lan':
        eligible=[nic for nic in candidates if nic.get('provider')=='lan']
    elif mode=='auto':
        vpn=[nic for nic in candidates if nic.get('vpn')]
        eligible=vpn if vpn else [nic for nic in candidates if not nic.get('vpn')]
    else:
        raise PartyNetworkError('Unknown LAN/VPN network type.')
    if len(eligible)!=1:
        raise PartyNetworkError('Select exactly one connected LAN/VPN adapter.')
    nic=eligible[0]
    addresses=nic.get('addresses')
    if not isinstance(addresses,list) or len(addresses)!=1:
        raise PartyNetworkError('Choose a network interface with one active IPv4 address.')
    try:
        ip=ipaddress.IPv4Address(addresses[0])
    except (ValueError,TypeError):
        raise PartyNetworkError('Network adapter has an invalid IPv4 address.') from None
    if ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast:
        raise PartyNetworkError('Network adapter must be reachable on the chosen VPN/LAN.')
    return nic


def tailscale_peer_addresses(status):
    """Get online tailnet peers from vetted local Tailscale CLI JSON, never broadcast."""
    if isinstance(status,str):
        try:
            status=json.loads(status)
        except ValueError:
            return set()
    if not isinstance(status,dict) or status.get('BackendState')!='Running':
        return set()
    peers=status.get('Peer') or {}
    if not isinstance(peers,dict) or len(peers)>512:
        return set()
    found=set()
    for item in peers.values():
        if not isinstance(item,dict) or item.get('Online') is not True:
            continue
        ips=item.get('TailscaleIPs') or []
        if not isinstance(ips,list):
            continue
        for value in ips[:16]:
            try:
                ip=ipaddress.IPv4Address(value)
            except (ValueError,TypeError):
                continue
            if ip in TAILNET:
                found.add(str(ip))
    return found


def discovery_targets(adapter, tailscale_status=None):
    """Find *candidate* targets on the selected adapter only; NO packet sent here.

    LAN/Radmin/ZeroTier use scoped subnet broadcast; Tailscale uses explicit
    online peers from the local tailnet CLI, as Tailscale doesn't relay broadcast.
    Authentication/consent is a separate mandatory Party protocol phase.
    """
    provider=adapter.get('provider')
    own=set(adapter.get('addresses') or [])
    if provider=='tailscale':
        if tailscale_status is None:
            raise PartyNetworkError('Tailscale peer inventory is unavailable.')
        return sorted(tailscale_peer_addresses(tailscale_status)-own)
    if provider not in ('lan','radmin','zerotier','vpn-other'):
        raise PartyNetworkError('Unknown network adapter provider.')
    result=set()
    for raw in (adapter.get('ranges') or []):
        try:
            net=ipaddress.IPv4Network(raw,strict=False)
        except (ValueError,TypeError):
            continue
        if not 8<=net.prefixlen<=30:
            continue
        # Never broadcast to a publicly routed adapter merely because it
        # happens to be selected as an ordinary physical LAN adapter.
        if provider=='lan' and not any(net.subnet_of(home) for home in HOME_LAN):
            continue
        result.add(str(net.broadcast_address))
    return sorted(result-own)


def party_available(candidates,mode='auto',selected=None,tailscale_status=None):
    """A visible PRE-FLIGHT only, NOT proof that the game/Party can connect."""
    nic=choose_adapter(candidates,mode,selected)
    return {'provider':nic['provider'],'adapter':nic['value'],
            'local_address':nic['addresses'][0],
            'targets':discovery_targets(nic,tailscale_status)}


__all__=['PartyNetworkError','adapter_inventory','windows_network_candidates',
         'choose_adapter','tailscale_peer_addresses','discovery_targets',
         'party_available']
