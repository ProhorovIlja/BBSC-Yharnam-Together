# Ultimate B26: same-UDP-socket identity handover and signaling lease expiry

**Date: 2026-11-09.** Parent: [B25 Draft PR #57](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/57), preserving the cumulative playable server + launcher + client line.

## Source-proven problem and impact

The actual `server/src/server_link.cpp` `Hub::OnHello` path obtains a `members[from.Key()]` entry for every accepted hello, then overwrites its `online_id` and `virtual_endpoint`. On a **reused physical UDP endpoint** with a *different* online ID, the existing code failed to erase the old account's `by_virtual` entry. That stale virtual address could still map to the new occupant's physical link. This risks misrouting another player's game frames or stale member identity, independently of the earlier B24 room-scoped signaling fix.

Separately, `LinkServer::Apply` adds `matching.udpExt[online_id]` whenever a game links but had **no matching removal on Gone**. The old record could survive a final disconnect or change of account at the same physical endpoint. Link movement by the **same** online ID must **not** delete its valid new virtual endpoint.

## Changes

- **Real hub, `Hub::OnHello`:** after all eligibility checks, detect `from.Key()` already owned by *another* account. Send the previous identity's `MemberState::Gone` notice to teammates, `Unlink(from.Key())` to remove its previous `by_virtual` and packet-route pair counters, and emit `result.gone` for the world's normal cleanup. Then establish the new link and new virtual identity. Repeated hellos for the *same* account retain their existing link.
- **Real link server, `LinkServer::Apply`:** track `real endpoint -> authenticated online_id` while a game is linked. For `Gone`, remove that endpoint's old ID lease. Remove `matching.udpExt[oldID]` only if `m_link.HasLink(oldID)` is false, preserving successful same-account port migrations; then consume `Linked` to install the current lease. The existing `httpGate`, world, RPC and address-count teardown still executes.
- **No new protocol IDs, no wire format change, no game asset/installer modifications.** Source of a game ID is its accepted, encrypted hello.

## Regression

The **real C++20 encrypted hub** `server/tests/test_server_link.cpp` now has `IdentityHandoverOnReusedUdpSocket`. It establishes two actual handshakes, removes the old client's local Noise state to simulate a restarted process retaining the same OS UDP source port, signs in a different player ID, and asserts:
1. old link `Gone` and old identity's `MemberState::Gone` notice;
2. only two links remain; old ID no longer exists;
3. packets sent to the old virtual address cannot route to the new player;
4. packets to the new virtual address route with new identity and correct sender virtual address;
5. a repeated hello for the new, same ID does **not** generate a false Gone.

The existing suite exercises *same-online-ID* migration to another port (`VirtualMembers`), replay protection, build/version checks, Noise, encryption and group routing. CI additionally enforces the production stale signaling lease removal semantics from the actual `LinkServer::Apply` source before running this full native hub suite and inherited B24/B25 Qt6 regression tests. Git blob SHA pins enforce exact seven-file diff from B25.

## Acceptance limits

Synthetic C++ encrypted links are not actual launched games. No complete Windows launcher + emulated title integration, no real five-hunter/NAT/late-join frame-by-frame performance or user save tests occurred. All client/server instances must eventually be validated with the **same build and protocol fingerprint**. Do not close private screenshot-derived issues (#21/#23) solely because this C++ correctness gate passes.

Independent candidates remain original [droogie/bbhost PR #217](https://github.com/droogie/bbhost/pull/217) for signaling/lifecycle and [Jgamrot/yharnam-pc 2.3.2](https://github.com/Jgamrot/yharnam-pc/releases/tag/v2.3.2) for an unrelated co-op server NP lookup fallback. Neither was blindly merged: wire/API compatibility and proprietary assets must be reviewed separately.

**Draft-only safety:** no Fornex access/deployment, passwords, private Google Drive screenshots, game binaries, player saves, release or public installer.
