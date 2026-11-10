# Ultimate B53: teammate hits Doll during Level Up, unblock local hunter's kneeling animation

2026-11-10, stacked on [B52 Draft #113](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/113). Tracked [Issue #114](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/114). Grounded in original official Yharnam Together [PR #555](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/555), still OPEN/not merged at review time.

## Source-confirmed bug

During an active Doll Level Up, a teammate can damage/attack the Doll and interrupt her scripted dialogue. The game fails to turn off the current hunter's personal blessing flag `72100100`. Her kneel/stand animation event `m21_00:12100112` therefore never finishes, leaving that player stuck kneeling. B51's quick cancel fix only handled a blessing turning off too early; it cannot rescue a blessing that **never turns off at all**.

## Actual production changes

- `emulator/src/core/bloodborne_party.h`: `DollHitEndsBlessing` records the local game's Doll HP only while co-op is enabled and the blessing's state. It returns true only for a **real HP drop across consecutive observed samples while the local blessing is active**. No first-sample, healed, null/absent Doll, unrelated NPC or solo trigger.
- `emulator/src/core/bloodborne_kills_hp.cpp` plus `emulator/src/core/bloodborne_re_internal.h`: expose a `Coop::DollHp()` query using the local game's `DollCharacter` and existing `CharacterHp` routine, returning nullopt when the Doll character is absent or invalid. This doesn't use remote teammates' NPC health.
- `emulator/src/core/bloodborne_travel.cpp`: add `EndDollBlessingWhenSheIsHit()`, invoked **before** B51's `ClearDollLevelUpFlagAfterHerBlessing`. Guard on party controller, loaded local hunter and current blessing; if source-confirmed hit occurred, set **only that local blessing flag 72100100 to false** through existing 1.09 event-flag setter. Do not force-reset the kneel/stand flags or alter inventory/saves/world NPC progression.
- Real emulator GTests for `AHitOnTheDollEndsHerBlessing` and `AHitOnTheDollOutsideHerBlessingChangesNothing`; portable GCC+Clang native C++20 test extracts and compiles the **actual** `DollHitEndsBlessing` class with hit, heal, absent NPC, solo, mode-switch and continuous blessing scenarios. Windows/Linux source contracts verify actual hook order and guard.

## Scope and validation

This does **not** make the Doll invulnerable to other hunters, grant any item, change combat targeting, grant levels, or change event scripts. The real-game 1.09 Windows rig still needs to show that an interrupted player stands up, that the Doll heals/respawns normally, and that other players' dialogue stays isolated. Test with solo and 2–5 hunters, quick Circle cancellation B51, Give item B52, Doll killed/attacked during both animations and eventual correct recovery.

Upstream #555 has not been indiscriminately merged; its three components B51 (quick cancel), B52 (Give item) and B53 (hit) were adapted separately with test and source provenance. These Drafts do NOT resolve P0 host personal-world rollback #22 or persistent phantom-earned key items #35.

No original Bloodborne/DS3 assets, Fornex production, player saves, keychains, credentials or installer files touched. CI is not gameplay proof.
