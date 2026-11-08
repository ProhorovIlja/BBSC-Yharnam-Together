# Ultimate B05: isolate guest progress observations by character owner

**Status:** experimental production C++ fix, synthetic tests only; not an integrated game release.

## Confirmed source-level problem

The Yharnam Together 1.4.0-derived `KeepGuestProgress` retains `seen_on` and `have_baseline` between ticks. Previously it reset `set_at_home` and `home_since` on a save-slot switch **but not the pickup baseline**. If a party guest reenters a session with a different save character, the previous hunter's observed flags could be treated as the next hunter's first-party observations. This can lose a pickup detection or misattribute an initial flag. It is a code-level isolation problem; it is **not** proof of any one historical personal-save overwrite.

B05 introduces a small owner-transition helper applied *before* session flag tracking. Owner is both the local save slot and the B04 confirmed new-character generation, so replacing a character in the same slot invalidates its observation baseline once the existing detector confirms it.

The guest's `guest_world_kept_ms` timestamps also had no slot-generation cache reset when the `guest_world` file was switched, nor on `ForgetGuestWorldChanges()` for a new character using the same slot. They could affect `KeptChangeYieldsToTeam` comparisons belonging to another character. B05 clears these transient timestamps under the existing `guest_world_mutex` whenever the slot-specific map changes or its saved world list is forgotten. It does **not** delete a player's save, host progress or the original pickup list.

## Tests, evidence, scope

- `tools/re/tests/test_guest_progress_slot_baselines.py` compiles the **production C++** owner-reset helper and executes five-hunter, same-owner and same-slot-new-generation synthetic fixtures.
- Source assertions verify the reset precedes observed pickup flags, that world timestamps are cleared under the slot-specific load/reset, and that the B04 character generation is consulted.
- CI inherits B04 owner/award regressions, B03 readiness, B02 real team-lamp fixture and B01 Vulkan source checks. No full runtime/server/launcher build, no game assets, no external network tests and no live user saves.
- Parent B04 source blob: `f265c686afc5f41eff0e041f45bac93d5dcc4689`. B05 source blob: `a318dee5eed44bf4355fb400c96831fb81165e82`. Pinning and verification are in the JSON manifest and dedicated workflow.

## Cross-project intake, explicitly **not** imported yet

[Supermedo 1.9.8.3](https://github.com/Supermedo/bloodborne_pc/releases/tag/windows-v1.9.8.3) claims to repair a related but broader failure: host world bosses/doors/Chalice state persisted in a guest's personal world on return home. The public GPL `bb-probe-seamless-1.9.8.3-source.zip` archive is documented by its release and mirrored listing, but its source bytes could not yet be opened here. **B05 does not claim to reproduce or port that fix.** Actual comparisons of CLS-based world state with YT 1.4.0 are still required. The independent original [droogie/BBHost](https://github.com/droogie/bbhost) is still a full alternative runtime, not a blindly compatible patch source.

## Release blockers

[P0 progression #22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) and [reward owner #35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) remain open. Test actual Bloodborne 1.09 private backups with 2/3/5 hunters, mid-session switching, same-slot new characters, relogs, late joins, boss wipes, DBNO, DLC/Chalice, personal flag snapshots, and no duplicate/wrong-owner awards. The original Windows runtime linker failure in [#31](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/31) is independent.

**Never deploy experimental changes on Fornex; do not publish a Windows client, server or installer from B05.**
