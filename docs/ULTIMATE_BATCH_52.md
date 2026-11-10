# Ultimate B52: Small Hair Ornament personal Give dialogue for the Doll

2026-11-10. Stacked on [B51 Draft #111](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/111). Tracks [Issue #112](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/112). **Source:** original Yharnam Together [PR #555](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/555), OPEN at source-audit date. This change is a focused adaptation; upstream #555 also has other fixes and is not claimed merged.

## Confirmed game-source defect

In co-op, a hunter may hold **Small Hair Ornament**, internal goods 4300, yet fail to get the Doll's personal **Give** conversation option. Event m21_00:12100121 sets flag 12100122 for the player who owns the ornament. Another member's multiplayer event-flag message can keep a different value for the currently playing hunter's personal flag, so NPC quest dialogue no longer reflects that character's inventory.

## Actual production fix

- `emulator/src/core/bloodborne_party.h`: add `DollGiveFlag = 12100122`, `SmallHairOrnamentGoods = 4300` and the `DollGiveFix` policy function.
- `emulator/src/core/bloodborne_party.cpp`: implement `DollGiveFix` by reusing already-tested `HeldItemFlagFix`. Only offers a value when `party_configured=true` and current local flag differs from whether the current player holds goods #4300.
- `emulator/src/core/bloodborne_travel.cpp`: add `KeepDollGiveFlagOwn` to the existing game thread and call it after `KeepHeldItemFlagsOwn`. Throttle to at most once per second, require a configured party, a valid local hunter, and readable local inventory. Compute current **local** goods ownership through existing `TradeHeld` and set only the local event flag through guarded original 1.09 `PartyGhostSetEventFlagOffset`. No inventory creation, copy, consumption, save modification, network protocol or cross-player item sharing.
- `emulator/tests/bloodborne/test_bloodborne_flag_rules.cpp`: new real GTest `TheDollsGiveFollowsThePlayersOrnament`: verify true/false/nullopt for all relevant input combinations, exact quest flag/goods and `FlagOwner::PerPlayer` scope.
- `tools/ultimate/test_batch_52_doll_ornament.py`: cross-platform source contract and direct GCC/Clang C++20 compilation of the **actual extracted production** `HeldItemFlagFix` + `DollGiveFix` functions. Includes repeated item acquire/consume sequences and disabled party.

## Important boundaries

- This is a personal NPC dialogue flag fix. It does **not** grant Small Hair Ornament to the player, fix missing quest drops, unblock stuck animations when a teammate attacks the Doll, or resolve key-item persistence across game exit (#35). It also does not bypass NPC event-script or stock character eligibility rules.
- Required release gates: actual 1.09 Windows build, read-only item identification, solo/co-op two-to-five hunters, item held/not held, cross-team user switches, talk/leave/rejoin, Doll Level Up, animation, attack interruption and quit/restart with personal save backup. Source/GCC/Clang tests do not prove gameplay dialogue occurred.
- Do not merge with the broader upstream PR #555 until its independent Doll-hit recovery is scrutinized. Maintain separate Issue #110 quick-cancel fix and #112 Give fix.

No live Fornex, user saves, private game binaries, installer packages or accounts touched.
