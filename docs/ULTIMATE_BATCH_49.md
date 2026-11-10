# Ultimate B49: seamless co-op for all nine Bloodborne 1.09 editions

**2026-11-10**, stacked on B48 Draft PR #107. Grounded upstream source: [official Yharnam Together #546](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/546), **merged** at verification time; 7 files, CUSA00900, CUSA00207, CUSA03173 and six other retail versions. Related in our project [#84](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/84) and separate parallel [Draft PR #92](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/92) for clean 1.09 eboot diagnostics.

## Source-reproduced defect

- `bbport/launcher/bbport_coop.py::TITLE_IDS` and `bbport/scripts/game_check.py::SUPPORTED_TITLES` already list nine game versions sharing the known Bloodborne 1.09 executable. But `emulator/src/core/bloodborne_patches.cpp::IsSeamlessCoopGame` still returned false for any ID except `CUSA03173`. Thus a US `CUSA00900` user could enter the game with the launcher-installed team UI but without seamless core hooks: blinking placeholder `test` party labels, inactive Create Team button, no actual co-op.
- Separate `emulator/src/core/bloodborne_join.cpp` matching2 trace and `emulator/src/core/bloodborne_re_tracer.cpp` also hardcoded the EU game edition, which made debugging other regions incomplete.

## Production changes

- Add `emulator/src/core/bloodborne_titles.h`: exact canonical nine retail IDs with `IsBloodborneTitle`, `SeamlessCoopGameFor` and `GetsSeamlessCoop`. Only Bloodborne is eligible; unrelated CUSA titles still strictly blocked. `APP_VER=01.09` is expected; mismatched param.sfo is warned but actual executable **hook-site byte verification** is the final enforcement, as the launcher may load the correct 1.09 executable alongside an outdated param.sfo.
- Use the shared classifier in the patch installer gate, join diagnostics and RE trace. No copy of the actual game executable or bypass of the `CoopSitesMatch` whole-core-before-write protection. All-or-none installation remains.
- Real emulator gtest in `emulator/tests/bloodborne/test_bloodborne_titles.cpp` registered with `emulator/tests/CMakeLists.txt`; independent standalone C++20 unit test checks valid/invalid IDs and versions. Windows/Linux Python source checks parse **actual** launcher and game-check title constants via AST and assert byte guard remains. No game files required.

## Security and release requirements

An older version's param.sfo may be accepted only if executable site bytes match the supported 1.09 binary; it is not support for 1.00 or unverified patches. Passing C++ unit tests does not certify offsets for every retail dump, DLC authorization, other account/session backend setup or cross-play with real users. Test CUSA00900/CUSA00207/CUSA03173, mixed regions, game 1.09, boss/NPC/voice/social features, and CUSA without matching 1.09 executable; avoid accidentally overwriting private saves.

## Existing parallel work

PR #92 adds game-check clean eboot 1.09/region **diagnostics** in bbport/scripts/game_check.py and does not edit these three engine co-op gate files. It remains a divergent Draft on B39 and must be reconciled before releasing an installer. No other external fixes imported without source parity.

No Fornex production, game assets, save files, installer packaging or publicly downloadable game touched.
