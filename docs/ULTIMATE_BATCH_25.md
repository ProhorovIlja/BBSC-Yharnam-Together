# Ultimate B25: don't strand a matchmaking room on ContextStop or duplicate join

**Date: 2026-11-09.** Continues cumulative B01–B24 directly atop Draft PR #56. No independent build or release.

## Concrete source defects found in B24

The actual `server/src/cmd_matching.cpp` contained three related lifecycle gaps.

1. `ClientSession::CmdContextStop` set `m_matching.initialized=false` and `ctxId=0`, **without calling `DoLeaveRoom`** when `roomId` was active.
2. `CleanupMatchingOnDisconnect` returned early if `!m_matching.initialized`. Thus, after the ContextStop path above, disconnect **skipped cleanup of the still occupied room**, leaving a ghost member and held slot.
3. `CmdCreateRoom` and `CmdJoinRoom` didn't guard against a previously occupied room. Another successful request could overwrite `m_matching.roomId` and lose the only per-connection reference to the old membership; `CmdContextStart` likewise silently replaced context ID while a room was still active.

These failures follow directly from code paths. They may contribute to stale roster/failed late join, but no historical screenshot has yet been reproduced in the current client/server combination.

## Production changes

- `CmdContextStop` first invokes the existing **real** `DoLeaveRoom(roomId)` (which handles membership removal, room destruction or owner migration and member-left notifications), followed by idempotent `ResetMatchingRoomState(roomId)` even if the old room has already disappeared. **Only then** clear `ctxId` and `initialized`.
- `CleanupMatchingOnDisconnect` checks `roomId` independently of the context flag; leave and local reset also cover an inconsistent / partially retired context.
- `CmdCreateRoom` and `CmdJoinRoom` return existing protocol `RoomAlreadyJoined` while a different room is still active. Guard runs after decoding and *before* allocating/inserting/replacing room/member state. `CmdContextStart` likewise refuses an overwrite while room ownership remains active.
- `server/src/matching_lifecycle_guard.h` defines the two tiny production predicates (`MayEnterRoom`, `RoomRequiringCleanup`) against the genuine `MatchingSessionState`. No protocol or protobuf change.

## Tests and acceptance

The B25 C++20/Qt6 unit runs actual `Room` and `MatchingSessionState` types and the production guard with a full five-hunter room; covers stopped context **with an occupied room**, duplicate join/create intent, release and repeat-stop idempotence. Source contracts verify that `ContextStop` calls the actual `DoLeaveRoom` **before** disabling the context, disconnect doesn't skip `!initialized`, and Create/Join guards precede allocation/room writes. Dedicated CI repeats the previous B24 Qt6 peer-scope test. Source-locked six-file diff and Git blob hashes protect the cumulative branch.

**Limit:** this does **not** execute a full shadNet service through a real TCP/protobuf ContextStop request or five launched Bloodborne clients. The tests validate the production guard and code-order integration, not full real game synchronization.

## External reference and remaining work

The public shadNet matching documentation explicitly describes a matchmaking slot being returned on `ContextStop` or disconnect, and the independent Wozzardman/shadp2p Bloodborne RE research documents the game's voluntary `LeaveRoom` behavior. They support the lifecycle expectation, not proof of identical source in our branch. The original droogie/BBHost signaling PR #217 and the Jgamrot/yharnam-pc third-player NP-ID lookup fix remain separate candidates requiring protocol parity checks.

The major remaining release gates are real Windows client/server matched builds, two/three/five-player gameplay, peer removal/rejoin with NAT, missing-actor/world/quest/save regression checks, boss/mob progression and DBNO/PvP, FPS/RAM and networking p95/p99 comparisons. Fornex and private Drive files remain untouched; no public installer, binaries or game assets are produced by B25.
