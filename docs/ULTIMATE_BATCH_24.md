# Ultimate B24: peer signaling is scoped to the caller's own matchmaking room

**Date:** 2026-11-09. **Parent:** B23 / Draft PR #55. The cumulative client + server + launcher history is retained; this changes no released service.

## Confirmed source problem

In `server/src/cmd_matching.cpp`, `ClientSession::CmdRequestSignalingInfos` previously read a target's endpoint from the global `udpExt[npid]` table *before* verifying a room relationship. It then scanned **every room with the same matching key** and selected the first matching NP ID, without checking that the requester belonged to that room. Two concurrent five-person parties under the same title key could therefore resolve another party's member address or member ID. A user who had left a room could also retain an accessible UDP address in the shared table.

This was demonstrated by reading the actual handler and associated room state/Join/Leave paths. It is a source-proven authorization and routing defect, **not** a claim that it has caused the historical screenshot reports.

## Production fix

- Require the requester to have a nonzero `m_matching.roomId` and to be an actual member of the **exact** `(matchingKey, roomId)` room.
- Require the target to be a different actual member of that room. Reject empty/self targets; return `NotFound` for a nonmember.
- Only after this check, look up the authorized member's STUN endpoint. Prefer a complete (nonempty IP and nonzero port) public pair and otherwise fall back to that member's advertised room address/port.
- Carry the member's ID in a value copy obtained under `roomsLock`; release that lock before reading `udpLock`, avoiding lock nesting and remote pointers.
- Preserve the existing protocol command, protobuf layout, client API and valid 2–5-person same-room signaling behavior.

## Regression gate

A dedicated C++20 test compiles the **actual production header and Qt6 `Room` model**, with one host plus four guests. It tests host→four peers, guest→guest, different rooms under the same title context, out-of-room callers, self/empty ID and leave/rejoin identity replacement. CI also inspects the actual production handler to guarantee it calls the helper on the exact active room **before** reading `udpExt` and no longer scans all rooms.

These tests use synthetic room members and addresses, not a five-running-game integration session.

## Related upstream, not blindly transferred

[Jgamrot/yharnam-pc 2.3.2](https://github.com/Jgamrot/yharnam-pc/releases/tag/v2.3.2) solved its own third-member NP lookup failure by a client fallback for servers that reject the lookup command; it is a different failure mode than this server-side cross-room peer resolution. Independently, [droogie/bbhost PR #217](https://github.com/droogie/bbhost/pull/217) includes changes to peer signaling, connection lifecycle and connection IDs. Such changes require paired client/server compatibility review and tests rather than direct cherry-picking.

## Still blocking final release

Actual Windows launcher + game + same-version server, two/three/five-hunter late join, reconnect, NAT, actor spawning, world/quest/save integrity, DBNO/PvP, network p95/p99, clean Windows package and A/B BBHost vs BBPort FPS/RAM tests remain required. This patch is server-authoritative endpoint authorization only. Nothing touched Fornex, account secrets, screenshots, game binaries, players' saves, public installer or hosting deployment.
