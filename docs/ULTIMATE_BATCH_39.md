# Ultimate B39: selected LAN/VPN adapter preflight, sourced from BBGL Party research

**2026-11-09.** Stacked on [B38 Draft PR #90](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/90), whose Windows/Linux CI passed [3/3](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42688006151). Related [Issue #93](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/93) is a **third connection mode** request: one-click LAN/VPN Party through Radmin, Tailscale and ZeroTier, where players need not configure a shadNet host IP, an account or a manually operated server. Existing **Global Dedicated, Local Host shadNet and PLAY OFFLINE must remain**.

## Source audit and provenance

- Found the actual author: [mark3317/bbgl](https://github.com/mark3317/bbgl), GPL-2.0, and [mark3317/bbsc-gl](https://github.com/mark3317/bbsc-gl), GPL-2.0, NOT Mark337. BBGL is a [Jgamrot/yharnam-pc](https://github.com/Jgamrot/yharnam-pc) fork with a BBSC-GL co-op mod fork originally based on CLS BBSC. The original **droogie/bbhost** remains a separate networking candidate and is NOT CLS BBSC.
- [BBGL Party adapter source](https://github.com/mark3317/bbgl/blob/main/launcher/bbport_coop.py) uses Windows Get-NetAdapter and Get-NetIPAddress. Its [Party discovery source](https://github.com/mark3317/bbgl/blob/main/launcher/bbport_party.py) uses adapter-targeted UDP discovery 37601, TCP control 37600 and gameplay UDP 37658; Tailscale CLI status peer inventory rather than broadcast. [BBGL tests](https://github.com/mark3317/bbgl/blob/main/tests/test_party_connection.py) use real loopback sockets with 3 peers and stale-peer/UDP-failure scenarios.
- [BBGL P2P handoff](https://github.com/mark3317/bbgl/blob/main/docs/P2P-HANDOFF.md) states the chosen private LAN/VPN is the bootstrap trust boundary, **NOT secure public internet discovery** and no new WAN NAT traversal/relay. This is not enough to auto-admit strangers from a shared Radmin/tailnet. No unauthorized group joining, consent-bypass or unsafe cross-session keys should be copied.
- [BBSC-GL Party sources](https://github.com/mark3317/bbsc-gl/tree/develop/party) host local authority/epoch and API compat, with separate C++ native hooks, chalices and reward logic; it is **not wire-compatible with Ultimate YT Link4**, or instantly imported. Its reported full-story+NG+ and quest/reward improvements require source comparisons and actual Windows game tests before promotion. Respect GPL attribution and third-party notices.

## Actual B39 source changes

Added self-contained **`bbport/launcher/bbport_party_network.py`**, an API for controlled **preflight only**:
1. `windows_network_candidates` runs a fixed, argument-free PowerShell adapter inventory with Get-NetAdapter / Get-NetIPAddress, 10s timeout and no network packets or credentials. No untrusted shell command interpolation. `adapter_inventory` safely parses bounded JSON, filters loopback, malformed IPv4/prefix and annotates provider by Windows interface name/description (Radmin, Tailscale, ZeroTier, other VPN, physical LAN). IP prefix alone is *not* trusted to identify a VPN.
2. `choose_adapter` rejects ambiguity when more than one usable interface matches, rather than broadcast on all NICs or silently routing on an unrelated network. The caller may explicitly select a named interface.
3. `tailscale_peer_addresses` accepts the local Tailscale status JSON (no API token or cloud call) and selects only online IPv4 peers in Tailscale 100.64.0.0/10, excluding offline/IPv6/unrelated IPs. ZeroTier and Radmin use selected adapter IPv4 subnet broadcast as **candidate targets only**.
4. `discovery_targets` does not send any packets. Normal physical LAN broadcast is *strictly RFC1918* (10/8, 172.16/12, 192.168/16), NOT Python's broad is_private, which includes documentation/reserved addresses on some versions. The caller receives target proposals for the **chosen NIC only**.
5. `party_available` returns a typed candidate list only. It does **not** assert game connection, world synchronization or safe group membership.

## Verification

`bbport/tests/test_party_network_preflight.py` imports the exact production module on **Windows 2022** and **Ubuntu 24.04** Python 3.12, using only fake PowerShell outputs and injected Tailscale status: tests three VPNs, ambiguous selection, public interface protection, online/offline peers, invalid/malicious data, wrong/missing adapter and zero traffic. A SHA manifest verifies all source/test blobs and a five-path B38→B39 diff. B38 Global server tests run again to ensure adding a LAN module cannot silently damage separate accounts/server selection.

## Next required work before any playable Party mode

- Implement the actual scoped discovery/advertisement and optional preflight, consent, group identity/session binding and secure peer authentication. Do not simply auto-join any UDP announcement that shares the same VPN.
- Integrate a compatible **local Party bridge for YT Link4, Matching2, combat, personal world and durable quest/reward state**. Map to our server rules explicitly; do not import BBSC-GL Python protocol directly into YT C++ without source-backed proofs.
- Verify 1/2/3/4/5 hunters, host migration, room capacity and invasions, loading/travel, Henryk/Eileen, personal save and item lot receipts, reconnect, NAT and provider-relay behavior. Serverless VPN mode isn't a global internet P2P mode; direct WAN secure relay fallback remains [#80](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/80).
- Only then expose real **PLAY ONLINE → LAN/VPN PARTY** in launcher, because a button with no usable network backend would be misleading.
- No local VPN programs were installed, configured or connected, no new listener socket was opened, no real Bloodborne or Fornex was touched.

**Status: production-source preflight foundation + real Python tests, NOT a working YT no-server game yet. Draft only.**
