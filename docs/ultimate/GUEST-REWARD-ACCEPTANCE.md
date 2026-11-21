# Guest reward and progression acceptance

Source-level candidate for the playable edition; no production deployment and no claim of save acknowledgement. Related: #22, #35,
#137. The older #140 addressed a transient phantom return path. The playable baseline has a
different slot ledger, so this change preserves it rather than cherry-picking that implementation.

- Boss and dialogue gifts wait for a readable player and native item manager before extraction.
- Pending lots belong to the observed slot and in-process generation. Existing slot transitions
  and detected same-slot replacement invalidate the queues. This is not durable identity.
- Phantom key processing pauses when the list is missing or when the needed give path is unready.
  The slot ledger replaces its old file only after a successful temporary write and close.
- Native item awards return void. In-process retries are suppressed while a return attempt is
  ambiguous. Observing every owed item in the stable own inventory is only an inventory
  acknowledgement: the current candidate can clear the sidecar before the game save commits.
  File replacement is not a game-save ACK or a power-loss durability guarantee.
- The queued boss/NPC rewards remain process-local; exits before grant can still lose them.

## Private game gate

Use disposable 1.09 saves with independently recorded flags, inventory and slot IDs. Hash or
snapshot the original clones before play; byte equality is not required after ordinary saves.
Keep host-team world and guest-personal world observations separate. On a private two-client
rig first, then three and five clients where relevant:

1. Join a less advanced host with a more advanced guest. Check the active team world, leave,
   reload the guest and check personal doors, lamps, quests, boss flags and inventory.
2. Queue a boss lot and an NPC gift while leaving or traveling to Dream, DLC or Chalice. Withhold
   the item manager for 2, 8 and 30 seconds. Restore it and record native attempts, gift flags
   and before/after inventory. Repeat checks after a same-slot reload and after reconnect.
3. Switch A to B, then B to A, while a reward is pending. Also replace the hunter in A. No
   reward from a previous character may appear on the new character.
4. Earn a phantom key item; exit normally, crash before return and crash between grant and
   game save on separate clones. Compare the actual loaded inventory and sidecar. Record any
   loss or duplicate rather than inferring success from logs.
5. Reproduce Dream travel and lamp/door behavior after a wipe, clean leave and reconnect.
   Do not mark #22 or #35 fixed solely from the host-independent tests.

## Separate closure evidence

| Issue | Record before marking fixed |
| --- | --- |
| #22 | Guest's individual lamps, doors, boss and quest flags match the recorded pre-join guest state after a full process restart; host/team flags remain separate. |
| #35 | Deferred boss and NPC lots appear exactly once for the correct hunter after ready-state recovery, including reload/restart as required by the issue. A different hunter occupying the same slot receives none. |
| #72 | The interaction prompt itself is present on a known-unlocked Dream tombstone after co-op travel and after reconnect; distinguish no prompt from an empty destination list. |
| #137 | Run separate interrupted clones: after the ledger write but before native grant, after inventory observation but before game save, and after a verified savedata commit. Compare the loaded inventory and journal after a fresh process on each clone, then replace the hunter in the same slot and verify no replay to the replacement. |

Record the exact client, server and launcher SHAs, CUSA/1.09, initial and loaded item
counts, and the observed save boundary. If the boundary cannot be triggered or confirmed,
report that case as unverified rather than inferring durability from the sidecar or CI.

## Interrupted journal staging

If the slot ledger has a sibling `.tmp` path, a later writer will not replace
or clear the committed ledger. The staged data can be incomplete and is not
evidence that a grant happened. Stop the game, copy the save, ledger and
staging path as a set, and investigate the copy. Do not merge or replay the
staged data based on timestamps or the slot number. Record the loaded
hunter, observed key-item counts and whether game savedata had committed.
