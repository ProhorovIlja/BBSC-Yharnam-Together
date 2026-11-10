# Ultimate B51: Doll's Level Up quick cancel no longer skips hunter stand-up

2026-11-10. Stacked on B50 Draft PR #109. Source provenance: open official Yharnam Together [PR #555](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/555), which also contains several **unverified additional** fixes not imported here. Tracked in [our issue #110](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/110).

## Reproduced defect in our source

Old `emulator/src/core/bloodborne_party.h::DollLevelUpClear::Tick()` saw that the Doll's blessing flag `72100100` had been switched off and immediately cleared the player's own Level Up flag `6700`. But map `m21_00`, event `12100112`, can keep the player kneeling for its minimum 54 frames; the own-animation event is guarded by `6700`. Pressing Circle before the animation ended therefore allowed `6700` to be cleared too early and the stand-up step never ran.

## Actual source integration

- `DollLevelUpClear` now takes both `blessing_on` and `steps_on`; after a witnessed blessing turns off, it waits until the player's own animation steps `72100101` AND `72100102` are both off. It then permits clearing `6700` once. This resets state when the co-op mode is disabled, so no stale status crosses a solo session.
- `emulator/src/core/bloodborne_travel.cpp::ClearDollLevelUpFlagAfterHerBlessing()` computes `steps_on` from live `EventFlagOn(DollBlessingFlag + 1 / + 2)` and passes it to the state machine. No boss progression, extra event flag, save/inventory, game bytes, server or character state is altered.
- Existing emulator GTests `TheDollsLevelUpFlagGoesOffOnceHerBlessingIsOver` and `TheDollsLevelUpFlagStaysWithoutABlessingOrOutOfCoop` are updated, and `TheDollsLevelUpFlagStaysOnUntilThePlayerStoodUp` is added for the precise early Circle cancellation bug.

## Verification and limitations

- Windows/Linux Python test checks **actual real engine call site**, step flags, GTest, and missing old premature-clearing logic. Linux GCC and Clang compile/exercise verbatim extracted production `DollLevelUpClear` class with early cancel, finished animations, repeated action, solo-mode reset.
- Source/portable compilation is NOT a real-game demonstration: still need Bloodborne 1.09 rig, controller Circle/mouse cancel, two and five hunters, Doll hit while playing dialogue and second Level Up in same Dream visit.
- Upstream #555 also proposes ending the blessing when teammate strikes the Doll, plus repairing Small Hair Ornament Give dialog per-player flag. Those are **separate** unmerged changes not claimed fixed by B51.
- Stacked B50 protects staged user saves from overwrite but does not fix game-owned world rollback (#22) or missing phantom key items (#35). None of those storage files are touched in B51.

No Fornex deployment, game assets, user saves, installer publication, cheats or network protocol changes.
