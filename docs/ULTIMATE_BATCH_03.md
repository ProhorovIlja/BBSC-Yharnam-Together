# Ultimate B03: Preserve deferred co-op rewards when inventory is unavailable

**Status:** source candidate, **not** a completed gameplay fix, release or installer.

## Why

Direct read of `emulator/src/core/bloodborne_flags_store.cpp` showed that both
`GiveDueNpcGifts` and `GiveDeferredBossItems` removed expired awards from
their respective queues **before** checking the game's `MapItemMan` vtable.
During a map load, that pointer can be unavailable; the old implementation
logged an error, discarded the lot and would never retry. This is a plausible
independent contributor to missing guest rewards, **not** proof that the
historical screenshots exhibited this exact cause.

B03 changes **one game file** so that both paths first check whether they have
due rewards, then check manager readiness, and only then drain the queue.
When not ready they retain the reward and retry no more often than every 250 ms
on the game thread. The normal award/gift-completion order and TLS, server,
updater, world and save formats are unchanged.

Source-level evidence is pinned to exact blobs in
`tools/ultimate/batch_03_manifest.json`. The new synthetic test
`tools/re/tests/test_deferred_rewards_retries.py` **compiles the real C++
production queue helper** with five boss lots and five NPC gifts, and checks
that no item gets lost when the item manager is unavailable, only currently
due entries are consumed, and each is removed once. It also asserts the
actual production NPC/boss paths check readiness before removing rewards.

## Cross-repository intake decisions

- [CLS #46](https://github.com/CLSAMG22/BBSC/pull/46) adds Logarius's Crown
  of Illusions and Celestial Dial to a static reward table in a distinct
  `bloodborne_re.cpp`. Our YT-derived build uses a dynamic item-lot award
  interceptor; the old static table is not a drop-in patch. Compare relevant
  `ITEMLOT_PARAM_ST` rows and event triggers in **private** 1.09 game files
  before deciding if the extra boss-specific fix is necessary.
- [CLS #47](https://github.com/CLSAMG22/BBSC/pull/47) sends a dead guest
  home if the session ended and the game is stuck on a grey screen; it
  references CLS-only leave locks. Map it to YT's leave/DBNO state machine,
  not an address transplant.
- [deadinside #418](https://github.com/deadinside28/bloodborne_pc/pull/418)
  adds host-reload detection to the bbnet20 spectator, but that module is
  not our YT core. Preserve YT's existing wipe rules before porting.
- [Supermedo #161](https://github.com/Supermedo/bloodborne_pc/pull/161)
  adds outside-folder saves backups to a different launcher's
  `bbport_saves.py`; our launcher doesn't contain that exact module.
  Reimplement from requirements after assessing current save backup paths.

These remain candidate inputs; **no claims of exhaustive GitHub coverage**.
See upstream GPU/auth B01 #32, net/world B02 #33, and server #7/#8 source
parity notes.

## Required gameplay gates

A **real Bloodborne 1.09 Windows game and private test accounts** must verify
guest boss clears and NPC gifts during map loads, five-player parties,
disconnect and reconnect, delayed queues across team switching, no duplicate
items, no wrong character/slot awards, and personal/world save recovery.
A pending reward must not carry from one save slot to another; this risk is
not yet tested and is **a release blocker**. Re-test NPC lot flags and
post-award trigger clearing in game.

Do not rebuild the complete Windows client/server/launcher for this single
source change. Focused production-helper tests are the B03 acceptance
target; clean Windows milestone builds are paid for after a larger integration
batch, followed by staging and explicit owner approval.
