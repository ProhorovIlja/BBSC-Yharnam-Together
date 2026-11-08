# Ultimate B04: never grant a deferred boss/NPC reward to another hunter

**Status:** SOURCE CANDIDATE, not game-tested, not shipped.

## Specific defect and boundary

B03 prevented the guest's boss item lot or NPC gift from vanishing while the
game's `MapItemMan` is unavailable, but it deliberately held the due award in
memory until a later tick. The original queue recorded **only the lot, due
time, and (for NPCs) the gift**. A different character could load before the
item manager returned, and the pending award would then be granted to the
wrong save. See [P0 Issue #35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35).

B04 tags each deferred boss lot and NPC gift with its **save slot** plus a
monotonic **character generation**. Generation increments when the existing
`ForgetSlotIfNewCharacter` detector confirms that the same save slot now
contains a different character. The game-thread grant checks that owner
before reading due rewards, before draining, and before *each* item grant.
Unowned rewards cannot be enqueued. Queues are protected by the existing mutex.

Items belonging to a **different** owner are retired rather than awarded to
the current character, with a local diagnostic. This is a *safety policy*:
it prevents cross-character loot, but if the original character left while
a reward was pending it may **not** receive its own item. It does not persist
pending items across application crashes. Future durable, per-character
journaling is a separate design gated by savedata ownership, idempotency and
anti-duplication constraints. Never use production player saves to validate.

If identity changes midway through an awarding tick, any **remaining**
ungranted items are requeued under the mutex rather than paid to the new
character. They are discarded on the next tick for that different owner.
The code still cannot establish whether the native game award function
actually succeeded after a valid `MapItemMan` vtable check, or whether it
can fail midway through an engine load. Treat that as a release blocker.

## Focused verification without full rebuild

- `tools/re/tests/test_deferred_reward_character_owners.py` compiles
  the **production C++ owner type and queue eviction helper** with a
  five-hunter synthetic queue: mismatched slots, reused slot with new
  generation, due and not-yet-due items.
- Source-level tests check generation increments after confirmed new-
  character detection, proper enqueue tagging and before-grant checks
  in both NPC and boss paths.
- Retain B03's real queue-readiness C++ fixture and B02's world-lamp
  regression. Pin the relevant source hashes in
  `tools/ultimate/batch_04_manifest.json`. No files from private
  CUSA03173 game dumps, DS3, personal saves or Discord screenshots.

## Selected cross-project evidence, not cherry-picked

- [CLS #38](https://github.com/CLSAMG22/BBSC/pull/38):
  revive has different client relay packet and actor world semantics,
  including five-player/DBNO policy questions.
- [deadinside #417](https://github.com/deadinside28/bloodborne_pc/pull/417):
  collision/physics after in-place guest respawn is engine-address-specific.
- [deadinside #418](https://github.com/deadinside28/bloodborne_pc/pull/418):
  wipe recovery logic lives in its independent bbnet20 spectator module.
- [YT upstream #540](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/540):
  **already implemented in our separate server #7/#8**. Verified the v2
  `Guard::AllowDatagram` logs flooding without temporary IP bans, operator-only
  `Banned(address)`, `LogFloods`, `floods` admin statistics, and
  `AFloodingLinkIsDroppedAndReportedNeverBanned` source test. All eight
  PR-affected files differ from B04 because server v2 is still a separate
  tested branch. Do not copy #540 over server #7 and lose its other hardening;
  combine client/server only at a pinned milestone with Link4 and world data
  safety checks.

These remain **open evaluation candidates**, not proof of compatibility.

## Before integrating any release

Run real Windows Bloodborne 1.09 with 2/3/5 players, delayed boss and NPC
rewards, changes from one save slot to another and new characters in the same
slot, game reloads, exits, boss wipes/DBNO, and actual inventory/flag audits.
Recheck no duplicate/wrong-slot awards, no loss of original world progress,
and proper team/host party authority. Confirm Link4 and build fingerprint
compatibility before any full milestone build. Only a private staging
environment and explicit owner sign-off can authorize a production cutover.

**No automatic packaging of launcher, client, server or installer for B04.**
