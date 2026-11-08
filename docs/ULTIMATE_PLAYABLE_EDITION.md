# BBSC: Yharnam Together TEST | Ultimate Playable Edition

Status: experimental source branch, NOT a tested game or public release.

## Goal
Best-of playable Windows client, launcher, multiplayer and performance using
Yharnam Together v1.4.0, compatible BBHost/BBPort, Supermedo, deadinside28,
visy, Awaken/Lantern, shadPS4, other forks/PRs and original free-source fixes.
Compare measured CPU/GPU frametime, VRAM, crashes, audio, input, networking,
five-player parties and world persistence; do not assume compatible engines.

Current BBPort still needs a user-supplied Bloodborne 1.09 folder including
PS4 eboot.bin. The fully standalone Windows port without original eboot is a
different project, currently paused.

## In this branch
- BBSC: Yharnam Together TEST launcher with visible TEST label.
- Updater pinned to immutable fork repository ID 1450213757, only test tags
  vX.Y.Z-test.N and SHA-256-checked setup assets, no official fallback.
- Separate Inno AppId, program/shortcut folder, launcher data and update temp.
- Portable ZIP uses BBSC Yharnam Together TEST folder and portable.txt semantics.
- Existing build/release stack reused. No server/client protocol changes.
- Additional synthetic EMEVD parser regression imported from isolated, green PR #11: modded empty events (0 instructions at -1) are valid; nonempty/invalid offsets remain rejected.

## Next release gates
1. Actually build Windows exe/portable ZIP/Inno Setup with MSYS2 CLANG64,
   PyInstaller and the existing make-release script, not just source CI.
2. Verify installer/portable payload parity, hashes, provenance, licensing,
   no game/assets/saves/credentials, data preservation and rollback.
3. Compare BBHost and BBPort v1.4.0 on equal hardware and gameplay scenes.
4. Re-test real client 1.4.0 join, five players, NAT, maps, hot join, boss
   fights, invites, invasions, DBNO, save integrity, private/public login.
5. Opt-in mod matrix for MOAL, Doll Rebirth, Jump L3 and XML patch collisions.

Google Drive research confirms private Bloodborne CUSA03173, Dark Souls III,
mods and historical compatibility documents. Do NOT redistribute game binaries,
private files, commercial assets or saves through GitHub or public CI.

Full Windows builds and actual gameplay testing are not yet performed here.
Keep Fornex production untouched and experimental release unpublished.
