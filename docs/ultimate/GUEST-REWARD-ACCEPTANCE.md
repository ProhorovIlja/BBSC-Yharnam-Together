# Guest reward and progression acceptance

Candidate only; no production deployment and no claim of save acknowledgement. Related: #22, #35,
#137. The older #140 addressed a transient phantom return path. The playable baseline has a
different slot ledger, so this change preserves it rather than cherry-picking that implementation.

- Boss and dialogue gifts wait for a readable player and native item manager before extraction.
- Pending lots belong to the observed slot and in-process generation. Existing slot transitions
  and detected same-slot replacement invalidate the queues. This is not durable identity.
- Phantom key processing pauses when the list is missing or when the needed give path is unready.
  The slot ledger replaces its old file only after a successful temporary write and close.
- Native item awards return void. No attempt is automatically retried after an ambiguous native
  call. The file change is not a game-save ACK and is not a power-loss durability guarantee.
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
