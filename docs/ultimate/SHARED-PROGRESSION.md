# Shared Progression — additive guest progression

User requirement, 2026-11-15; acceptance for #22, #35 and #137. This PR does not expose
a launcher toggle or enable the planner in the game. Do not treat the spec as a shipping feature.

- **Off (proposed default):** joining and leaving must not replace personal world progress with
  the host snapshot. No optional carryback. Preserve the existing character and separately
  distinguish personal loot from optional world carryback; the live current behavior is not
  equivalent to this mode. Entering the host's temporary world view is not importing it.
- **On:** add only verified progress actually earned by this hunter in the session, after
  restoring the hunter's own world. No automatic import of previously cleared bosses, unlocked
  lamps or the host's inventory. Never clear a completion, replace equipment or remove a
  previously obtained item. Rejoining or retrying the same event must not award it again.
- Locations, lamp unlocks, bosses, unique pickups, runes, gems and NPC milestones need typed
  event adapters. A rune/pickup identity is not a count; a generated gem needs its exact
  identity/provenance, not just its base ID. NPC branch conflicts, nonmonotonic flags, and
  unknown Chalice context are deferred, not unioned. Keep NG cycles and characters separate.
- The opt-in and accepted events belong to the local participant. No host override. Turning
  it off must not remove earlier accepted progress or retroactively import while off.
  Persistent identity, native outcome, replay journal, acknowledgement and crash recovery
  are prerequisites for an actual write path. Do not retry ambiguous grants blindly.
- No blanket OR of game flags: door, lamp-travel, item-lot and mutually exclusive quest flags
  are not interchangeable. No rollback of existing progress to force the host's outcome.

## Evidence and boundaries

The baseline already keeps a personal snapshot aside and layers the team world on load;
it can also replay guest changes including clears. Neither path is this feature. CLS #26
(Communion Chalice) is a useful additive reference, but imports existing peer progress and
can replace a weapon; do not port those semantics. The restore guard in this PR checks
live flag readback before retiring a block or registering an unverified world as home.
Readback is not durable game-save acknowledgement. Test with disposable 1.09 saves across
reconnect, slot switch, NG+, NPC branches and Chalice instances before release.
