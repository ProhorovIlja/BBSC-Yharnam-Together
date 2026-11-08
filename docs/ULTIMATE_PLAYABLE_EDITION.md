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

## November 8 integrated TEST candidate

[PR #19](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/19) is
the FIRST combined, cross-component source candidate, built on the stacked
launcher/TLS/3D map/source-discovery work (#10, #13, #15, #16). It imports exact
tested game/UPnP files from #14 and #17; the save restore block from #18 is
ported **surgically**, preserving #13's authenticated Windows truststore context
and the separate TEST release updater. This does not merge or close the source
PRs.

| Integrated subsystem | Provenance | Source CI status | Required real-world validation |
| --- | --- | --- | --- |
| TEST launcher, isolated updater and branding | #10 | [success](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42492015676) | Windows 10/11 frozen EXE, portable ZIP, independent update manifest and settings |
| HTTPS account sign-in, system truststore | #13, upstream YT #539 | [success](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/13) | Valid/revoked/host-mismatched TLS, proxies, correct error localization |
| Co-op selection refreshes 3D map | #15, upstream YT #537 | [success](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/15) | Real Windows Tk UI and no unintended redraws |
| Travel Together receive/vote lock order | #14, upstream YT #524 | [success](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/14) | Five-player rig, simultaneous votes, disconnect, scene transitions |
| Local UPnP all-or-rollback, mapping ownership | #17, informed by visy #16's NAT audit | [success](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/17) | Consumer routers, CGNAT/double NAT, repeated Start/Stop, port ownership |
| Staged save restore and verified rollback | #18, adapts actual YT save manager (not Supermedo module) | [success](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/18) | Real Bloodborne saves, Windows antivirus/locked files, power-loss recovery |
| Cross-GitHub project-family discovery | #16 | [success](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42491615551) | Exhaustive subsystem-level review of discovered forks/branches/PRs; search result counts are bounded |

The combined [integration CI run 42493465944](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42493465944)
passed: strict source boundary, Python launcher/auth/map/UPnP/save and source-audit
tests, C++20 real Travel Together state-machine regression with libfmt, and
PowerShell release-script syntax. This proves source/fixture coherence only.
It does **not** establish runtime stability, performance improvement, wire
compatibility with the independent original droogie BBHost, or a usable release.

**Not yet integrated:** parked shared GameLink reconnect draft #12 (requires
five-hunter restart/packet-loss rig); server drafts #7/#8 (must remain
production-isolated until server/client protocol parity and migration plan);
additional original BBHost renderer/network changes (separate bake-off);
offline chalice glyphs and external backups; native EBOOT-free standalone
port (different research track).

**Release gate:** only after reproducible Windows packaging, installer checks,
performance/latency comparisons against original droogie/bbhost, and gameplay
including five hunters, duels, invasions, boss fights, DBNO, map travel,
reconnect and persistent save recovery. No public Fornex changes until explicit
validated cutover.
