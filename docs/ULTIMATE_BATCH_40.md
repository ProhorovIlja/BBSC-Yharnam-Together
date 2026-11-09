# Ultimate B40: an unknown eboot.bin is not proof the CUSA region is unsupported

**2026-11-09**, stacked on [Draft B39 #91](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/91). The owner clarifies that players reporting failed CUSA03023 or another regional edition may be using a repack, a patched 60 FPS executable, altered trainer image, mismatched 1.09 update or damaged dump. It is not valid to infer from a single unrecognized SHA that every clean retail executable for that region fails.

## Actual source bug and revision

`bbport/scripts/game_check.py::problem` previously calculated the LOADED game eboot image SHA and **accepted the game immediately when it matched SUPPORTED_IMAGE**, without independently validating the `TITLE_ID` or `APP_VER` in `sce_sys/param.sfo`. A valid-looking image combined with a mismatched SFO (wrong retail Title ID or APP_VER 01.00) thus passed as supported Bloodborne 1.09. This violates the goal of diagnosing incomplete updates and wrong region metadata safely.

B40 moves metadata checks to independent steps: require listed retail CUSA, then APP_VER 01.09, then parse/verify loaded eboot SHA and known 60 FPS patched hash, then check shader extraction. All nine IDs in the existing SUPPORTED_TITLES remain eligible when the verified same clean loaded image is present; the code does **not** claim all nine physical retail editions are tested in the Yharnam Together co-op runtime.

The `wrong_eboot` diagnostic is now honest: an unrecognized SHA can come from a different clean regional build, patched/repacked eboot, incompatible/partial update, or other image alterations. It is **not evidence** of one specific mod, nor proof CUSA intrinsically unsupported. Known Lance McDonald 60FPS image still receives the precise `patched_eboot` diagnostic, as that exact signature is known; game patch hooks still only run on verified images. The header docs no longer assert blanket byte identity for every regional build.

## Regression

The existing in-tree `bbport/tests/test_game_check.py` fixture is extended to show:
- matching known image SHA with wrong SFO version returns missing_update
- matching SHA with nonretail Title ID returns other_title
- all nine supported retail IDs with the **same verified loaded 1.09 image** may pass
- unknown valid CUSA03023 1.09 image warns about possible modification/region without claiming proof of either
- prior tests for encrypted/unreadable eboot, baked-in 60FPS image, damaged DCX, other compression types and the optional dev-only skip remain.

Runs actual source logic using synthetic SFO/ELF fixtures on Linux and Windows, with exact five-file B39 diff and two source blob hash pins. No proprietary game binaries, DLC, player saves or real CUSA dumps used. Real compatibility across CUSA/DLC/regions and mixed 5-player co-op remains [#84](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/84) and is NOT claimed done.

No Fornex deployment or release, keep Draft.
