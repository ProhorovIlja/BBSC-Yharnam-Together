# Ultimate B27: keep persistent world progress, expire stale per-run loading bars

**Date:** 2026-11-09. Stacked on B26 Draft PR #58 (B01–B26 cumulative). The playable BBSC/Yharnam Together client + launcher and native-port work are separate release tracks.

## Source-proven defect

In the actual `server/src/bloodborne_world.cpp`, `Service::OnHello` replays **every** `world.loads` entry to a hunter who joins later. `Service::Forget` removes the gone link from `members` without erasing its old `world.loads[name]`. An actual disconnected player's last **JOINING 70%** could therefore be presented to a *new* player well after that game went away, even if the player had rejoined with a new run. The `member.stream.TakeRestarted()` path also cleared `member.party` without invalidating the load bar from its previous run.

The server deliberately keeps durable game state in `WorldLogHost` and `world.places`, and keeps lobby membership/DBNO rules separately. **An old per-run loading bar is not durable game state.**

## Changes

- Add private production `Service::ForgetTransientLoad(const Member&)`, scoped to the member's existing party + name. If another **active** WorldService member already has the same party and identity, leave its current load report untouched. Otherwise clear exactly `world.loads[name]`. Do not change persisted world, enemy HP, kill log, flags, session host, team membership, portraits, or saved return location.
- Call this before clearing `member.party` after **CoopStream restart** (new game on same physical link) and before erasing the old `Member` in `Service::Forget` (the UDP Hub's final `Gone`). `Service::Quiet` and `Service::LinkLost` intentionally retain load state for temporary blips. A returned hunter will publish fresh progress through the existing `kLoadProgress` path; no protocol change.

## Real regression coverage

Extend the original `server/tests/test_bloodborne_world.cpp` (not a stand-in test):
- Two real CoopStreams report a member JOINING 70%, `Quiet` only: a third member sees 70% (short blip retained).
- Call **real `Service::Forget`**, then a new member sends a real Hello: no stale report from the disconnected player.
- Rejoining member publishes LOADING 15%, and the late and future players see **15%**.
- A new game run creates a new CoopStream on the **same IP:port** without a link `Gone`: the old JOINING 80% must disappear before a late player joins, while its fresh 25% report still propagates.
- Keep the original server-world tests for owner handover, co-op kills/flags, snapshot and return places, invasions, DBNO-like vitals, trading and player lifecycle.

The B27 workflow also pins the exact six changed filenames and the three production/test Git blob SHAs relative to B26, asserts the important source integration order, and runs **one isolated Docker verification-tests image** with all existing 12 server test suites. This rebuild is server-only in disposable CI, not Windows emulator/client/release packaging or an ongoing live service.

## Limits and external review

This fixes a confirmed stale UI-data source; **it does not prove** why any historical screenshot showed a missing third-person model or failed joining. Those require same-build 2/3/5 actual game clients on separate PCs, NAT variants, late join, world progress, loading screen and save/reward integrity. No live Fornex deployment, private game assets, player saves, public installer or source-to-binary promotion.

Independent [droogie/BBHost PR #217](https://github.com/droogie/bbhost/pull/217) has significant signaling/peer lifecycle changes; they are not protocol-identical to this branch and must be assessed independently. [Jgamrot/yharnam-pc v2.3.2](https://github.com/Jgamrot/yharnam-pc/releases/tag/v2.3.2) addresses a distinct NP lookup fallback. The native PC port without eboot remains a separate, longer-term development track.
