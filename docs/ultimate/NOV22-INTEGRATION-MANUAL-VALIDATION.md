# 2026-11-22 playable source hardening — combined manual candidate

Status: **unmerged integration branch**. This is **not** a game release, production deployment, installed-game acceptance, or complete hybrid P2P implementation. No scheduled, recurring or event-triggered tests are enabled by this branch.

Base: previously validated main `fdbdbc67a19edc2fc8015fdf710ad1905104935f` (documentation-only update of the previous main source).
Integration combines the source and tests from ten focused source branches (including follow-up save, Discord, Redis and auth fixes). All fifteen unique modified source/test paths below are present together in this branch, with no changes to production server credentials, networking ports, user saves or retail game assets.

## Backup index hardening — issue #379

A separate source review of `save_backups` found two failure modes: a folder name can match the date regex but still be an impossible calendar value, which raises `ValueError` when parsed; a dated folder or root can be a symlink/junction and should not be traversed as a real game backup. New [fix/launcher-backup-list-validation-20261122](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/tree/fix/launcher-backup-list-validation-20261122) skips malformed calendar names **without deleting them**, rejects linked/junction backup directories, and reuses already staged backup preflight.

Two source-oriented `test_coop_update_preflight.py` fixture cases were added for an impossible date alongside a valid backup and a symlink pointing outside the installation. Their independent local reconstructions passed. The complete current scratch suite now reports **39 Python tests PASS**. This is a foreground set of separately copied/reconstructed functions, not exact repository/Windows source-suite CI or gameplay validation; no issue was closed.

## New P0 save-backup archive gap — issue #381

This audit cross-checked the actual game's `emulator/src/core/bloodborne_server_world.cpp::RetireOwnWorld` archive path against launcher `bbport/launcher/bbport_coop.py::save_files`. The game retains old personal-world snapshots at `SlotFileName("personal_world_before_home", slot) + ".1"`, `+".2"`, etc. Previous launcher backups read only `bloodborne_party_*.txt`, so these numbered recovery snapshots were omitted; `restore_saves` also left stale numbered archives behind.

New shared `party_sidecars` selects the original `*.txt` and numbered `*.txt.N` paths, preserving original Unicode filenames and declining link/junction sidecars. Both backup and restore use it. Tests added to `test_coop_update_preflight.py` check ordinary + numbered snapshots, Unicode filenames, stale archive removal during restore and symlink refusal. The inherited `test_coop_launcher.py` source assertion was also updated to the new `prepare_coop_update` helper rather than demanding old direct GUI calls.

**Important verification finding:** first staged regexp accidentally had over-escaped dots and failed to match ordinary filenames. It was fixed and re-read verbatim in both the standalone branch and integration branch; a direct local Python reproduction confirmed the incorrect expression failed and the corrected expression matches normal and numbered archives. The newest **34 on-demand, independently reconstructed Python unit checks** passed; this is **not** the full exact-repository source test suite or Windows/retail 1.09 validation. Keep [#381](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/381) and [#377](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/377) open for installed save, NG+, multi-slot, crash/power-loss and authentic game-native ACK acceptance.

Source comparison confirmed 15 changed source/test paths and four docs against main; main stays unmodified. No CI workflow, production instance, or account data was touched.

## Contents and ownership

| Area | Modified paths | Existing tracker | Candidate change |
| --- | --- | --- | --- |
| Portable Windows updater | `bbport/launcher/bbport_update_zip.py`, `bbport/tests/test_portable_update_zip.py` | #283 | Reject duplicate/ambiguous/signed/Unicode/pathological Content-Length; accept only CPython-decodable plain chunked transfer, reject partial HTTP 206 and non-200 responses before download. |
| Support ZIP | `bbport/launcher/bbport_support.py`, `bbport/tests/test_support_bundle.py` | #233 / #378 | Export only reviewed settings; reject symlinked logs, junctions and linked attachments; omit raw host overrides; exclusively stage a unique ZIP; include a privacy warning. Does not fully scrub raw logs/dumps or eliminate all path races. |
| Game installer save preflight | `bbport/launcher/bbport_coop.py`, `bbport/launcher/bbport_launcher_win.py`, `bbport/tests/test_coop_update_preflight.py`, `bbport/tests/test_coop_launcher.py` | #379 | Download, verify save backup and unchanged source, then stop server and run setup. Exclusively allocate dated backup dirs; preserve original and numbered personal-world archive sidecars through backup and restore; refuse linked co-op sidecars/backups and overlapping installs. No filesystem power-loss claim. |
| Game client Discord | `bbport/gpu/bbcoop/discord_activity.h`, `bbport/gpu/bbcoop/discord_status.cpp`, `bbport/tests/test_discord_activity.cpp` | #119 | Decode legal JSON string escapes/Unicode and inspect the **root** event type separately: nested user/event fields cannot impersonate outer ACTIVITY_JOIN. Preserves existing nested data reads. |
| ShadNet directory | `server/directory/directory.py`, `server/directory/test_directory.py` | #376 / umbrella #3 | Default 64 concurrent request workers (configurable 1–256), 100-ms overload 503 write budget, and finite 3-second Redis connection/read waits per socket operation. Release slots after worker failures. |

| Account authentication worker | `bbport/launcher/bbport_auth.py`, `bbport/tests/test_launcher_auth.py` | #280 | Return exactly one generic form completion if OS resources prevent creating or starting the auth thread, including OSError; never return exception/password details. |

## Evidence already obtained

These **isolated reproductions** used separately assembled copies of the modified functions, **not** the exact repository build. Be explicit about this limit:

- Portable update (expanded after initial handoff): a source-faithful local CPython module passed 3 unittest methods (21 HTTPMessage header patterns, 7 abnormal HTTP statuses, 5 finite-download cases). Duplicate Transfer-Encoding, unknown/gzip transfer encodings, unexpected 206 Partial Content and early refusal before writes are now covered. No Windows updater packaging test yet.
- Support settings: local Python test passed with multiple synthetic account/session secrets and malformed nested values; live settings not mutated.
- Client Discord JSON: a reconstructed matching-source Linux C++20 portable fixture compiled and passed with both g++ and clang++ (-Wall -Wextra -Werror), checking escaped keys, whitespace, surrogate-pair emoji, invalid escapes, join secrets and IPC frame sizes. No Win32 named-pipe test.
- Directory concurrency: updated faithful isolated CPython 3-method unittest suite passed: actual TCP loopback held one POST worker, received 503 on second client, recovered the slot, rejected invalid worker limits and released a permit after a mocked thread-start failure. Production class now defaults to 64, with a configurable 1–256 cap. No complete real directory/fakeredis suite or staging load acceptance.

No full repository, Windows launcher, actual Win32 named pipe, complete fakeredis, Docker, load, or installed Bloodborne 1.09 run was performed for this **new integration head**.

## Additional manual verification after the integrated source batches

These are **explicit foreground checks**, not full-repository CI, scheduled jobs or production tests:

- **Python HTTP framing:** a local source-faithful CPython 3-method unit suite passed (21 header patterns, seven rejected non-200 responses, bounded streaming). A separate disposable socket-server fixture returned seven raw HTTP/1.1 responses through actual `urllib.request.HTTPResponse`, covering normal Content-Length, duplicate values, chunked decoding, conflicting length+chunked, unknown gzip transfer, HTTP 206, and EOF-delimited replies. All seven passed, with no real downloaded or installed ZIP.
- **Discord IPC:** portable helper copied from candidate source compiled with GCC and Clang C++20 under `-Wall -Wextra -Werror`. An isolated 25,000-case deterministic parser stress run with Clang AddressSanitizer and UndefinedBehaviorSanitizer passed. A 4,096-case deterministic round-trip/malformed test was also committed to the candidate's C++ fixture and checked in a local stand-alone GCC/Clang+sanitizer build. Real MSVC, Win32 named-pipe operation and the full game client are still untested.
- **Directory worker slots:** three local Python tests passed on a source-faithful isolated class: TCP stalled POST/503/recovery, invalid cap refusal and simulated thread-start failure. The class now defaults to 64 workers with `DIRECTORY_MAX_HTTP_WORKERS` limited to 1–256; an overload response gets a 100 ms send timeout. This is not a staging load test, Caddy proxy acceptance, or actual fakeredis/server Docker validation.
- **Support ZIP:** three local Python unit methods passed for nonmutating `without_secrets` against nested server credentials, unknown future session fields and malformed key pins. No complete installed support ZIP privacy audit or raw log/dump scrubbing was performed.
- **Upstream duplicate prevention:** the latest Amanises 1.5.1 source includes targeted stuck-loading guest visibility, `KeepOwnWorldAside`, game sign-in URL handling, GPU PM4 and NPC/render crash fixes. Corresponding functions/patch names were verified **already present** in this fork's main; no blind duplicate or incompatible upstream merge was made. Actual five-player and installed client acceptance is still outstanding.

## Additional 2026-11-22 safety fixes and source-only evidence

- **Game installer backup gate, issue #379:** the main GUI previously ignored `OSError` on `back_up_saves` after stopping the co-op server and still launched the setup. New `bbport_coop.prepare_coop_update` enforces download → backup → stop; source backup writer immediately rereads copied synthetic saves and rejects mismatches, removing failed backup folders. New GUI catches `http.client.HTTPException` and refuses updates during another install or co-op preparation. Six cross-platform unittest methods committed in `test_coop_update_preflight.py`; five local independently reconstructed CPython smoke tests of ordering, corrupted copy, disk error, incomplete HTTP response and normal backup passed. **Exact full-repo, Win10/11 GUI and installed game saves remain untested.** This reuses the narrow idea in the still-open stacked draft #272, not the draft's unrelated UI/CI/release machinery.
- **Support bundle filesystem/privacy gate, issue #378:** fail-closed preflight for symlinks and Windows reparse points, including directory junctions on Python 3.11; raw host_overrides.custom.json removed from automatic ZIP; random exclusively created staging replaces predictable `.part`, cleaned on error. Text notice `REVIEW-BEFORE-SHARING.txt` cautions about raw log/dump content. Newest-trace selection survives deleted log files during rotation. Five actual local symlink/ZIP filesystem tests plus one fault-injected stat test passed using an isolated reproduction. **Full exact-module Windows/Linux suites, race-free file-handle-based nofollow and installed ZIP sharing acceptance are not complete.**
- These are manual-only code candidates, not claims that all game data is durably backed up or all report logs are free of secrets. Never apply these to a user's only copy of a save.

## Additional manually isolated verification — final source continuation

- **Local CPython (no private game/saves):** in `/mnt/data/bbsc_manual_validation`, 31 `unittest` methods pass in one foreground run. The copied-function fixtures include 5 new exclusive-backup cases, 2 Redis timeout/503 cases and 4 auth worker-start/failure cases, plus previous updater, support ZIP and directory tests. **These are separate faithful reproductions, NOT test execution on a complete GitHub repository checkout.**
- **Discord client:** new `RootField` branch uses the actual production discriminator callsite and has tests for nested `evt` inside objects/arrays, leading whitespace and no root event. Its matching local C++20 fixture compiles and passes on `g++` and `clang++` with `-Wall -Wextra -Werror`; Clang AddressSanitizer/UndefinedBehaviorSanitizer also passed. There is no actual Windows named-pipe or integrated gameplay test.
- **Account UI:** when constructing/starting a `threading.Thread` throws OSError, `run_thread` sends a generic BUSY response and no credential text. The separate local smoke tested both startup failure modes and successful/failed worker callbacks. Installed Tk event-loop confirmation remains pending.
- **Redis:** `redis_client()` now sets `socket_connect_timeout=3.0` and `socket_timeout=3.0`. One socket operation is bounded but a multi-command request or DNS lookup has no global 3-second deadline. The existing 64-worker saturation limit and overload 503 remain unchanged.
- **Save preflight:** `back_up_saves` allocates exclusive timestamp directories, rejects obvious linked/junction backup roots, rereads source files after backup and refuses an installer if the game changed them during backup. This is *not* a crash-atomic multi-file transaction or a guarantee against a malicious concurrent filesystem actor. Verified game's `SlotFileName` pattern `bloodborne_party_<list>_slot<N>.txt` matches the launcher's `bloodborne_party_*.txt` backup inclusion, including `home_world` and `personal_world` sidecars. No production player save was accessed.
- **External 2026-11-22 GPU research:** [Supermedo SSR fragment shading rate #380](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/380) records an upstream reported high-resolution improvement; no graphics patch imported without safe feature/extension and real GPU validation. [droogie bbhost Matching2 identity commit daea6d0](https://github.com/droogie/bbhost/commit/daea6d09479b6) is a useful peer/transport identity invariant for #80 but is not API-compatible drop-in YT netcode.

## Confirmed archive-sidecar follow-up in the same unmerged branch

A subsequent candidate update adds `party_sidecars` selection for both `bloodborne_party_*_slotN.txt` and numbered `.txt.1` through `.txt.63` (which `RetireOwnWorld` uses to preserve prior personal-world states), while skipping partial files, unrelated logs, and symbolic links. `save_files` now includes the archives in a backup; `restore_saves` removes current stale archives before reinstating the selected snapshot; `test_coop_update_preflight.py` and `test_coop_launcher.py` contain added source cases. A follow-up regular-expression correction `f0afecc7cf6ea9a11399973ae9f11ff35ef96740` is necessary for actual names to match.

Three additional independently reconstructed Python archive tests passed locally (normal/numbered selection, replacement/cleanup of stale .txt.2, linked sidecar rejection). **Aggregate isolated scratch validation is now 37 Python unittest methods PASS**, not an assertion that 37 original-repository tests ran. Unverified: installed save migration and rollback through crashes, NTFS ACL/reparse races, power failure, and game-native save acknowledgment. These remain covered by #379 and #377.

## On-demand validation only

From the checkout of **this exact integration head** (never production):

```sh
python -m unittest discover -s bbport/tests -p test_portable_update_zip.py -v
python -m unittest discover -s bbport/tests -p test_support_bundle.py -v
python -m unittest discover -s bbport/tests -p test_coop_update_preflight.py -v
python -m unittest discover -s bbport/tests -p test_coop_launcher.py -v
python -m unittest discover -s bbport/tests -p test_launcher_auth.py -v
g++ -std=c++20 -Wall -Wextra -Werror -Ibbport bbport/tests/test_discord_activity.cpp -o /tmp/test_discord_activity
/tmp/test_discord_activity
python -m pip install -r server/directory/requirements.txt 'fakeredis[lua]>=2.23,<3'
cd server/directory && python -m unittest -v test_directory
```

Repeat Python tests and the C++20 fixture using Windows Python 3.11/3.12 and MSVC Developer PowerShell. The full ShadNet container build, timeout/worker saturation under concurrent load, high-latency router behavior, optional Discord join-request UI, and real portable updater rollback need separate attended testing before merge.

Manual failure gates: no successful private player save backup; no guarantee a failed portable update leaves installed files intact; source test process crash; changing client wire or public server API; any new credential in a support bundle; incomplete HTTP response handling; game regression in join, reconnect, party state or save migration.

## Release and issue rules

- Do not close #283, #233, #378, #379, #119, #280 or #376 based only on these new isolated checks.
- Owner-closed historic #22 and completed #349 remain closed. Track remaining *unverified* cross-file save durability/native ACK in new open P0 #377; keep #35/#137 guest rewards, #21/#23/#63 hunter/NPC divergence and #80 direct authenticated P2P/relay open until actual 1.09 multi-hunter acceptance.
- Avoid source-workflow files, push/PR event CI launches, production deploys and automatic scheduled tasks without the owner's separate explicit authorization.
- Source comparisons: HTTP framing rejection follows RFC 9110/9112's permitted error treatment; this is a conservative client policy, not an alleged live exploit. Private Nov 14 bug register is not mirrored into public GitHub.

For earlier merged fixes and historical CI, see `docs/ultimate/ISSUE-TRIAGE.md`, `docs/ultimate/DEVELOPMENT-STATE.md`, and `docs/ultimate/MANUAL-SOURCE-CHECKS.md`.


## Supplementary manual gates — native save metadata / direct IP / header drip (2026-11-22)

The newer unmerged branch `fix/save-tree-nofollow-20261122` branches from `integration/nov22-playable-manual-hardening` and modifies `bbport/launcher/bbport_coop.py`, `bbport/tests/test_coop_update_preflight.py`, and `bbport/tests/test_coop_launcher.py`. Source regression cases are committed but not yet run against a complete checkout.

Before integrating: on disposable files, verify symlinked and Windows reparse/junction native save roots, nested folders, save files, numbered world archives, backup note, arbitrary backup tree entry, invalid-UTF8 note, >4096-byte note, and valid nested ordinary saves. Fail before stopping the server or installer whenever a relevant save path is linked. Repeat with concurrent rename/replacement to document the limits of path-based preflight, and verify rollback with actual Windows 1.09 save format. The metadata browser must not read outside the user tree or become blocked by corrupt note bytes. Cross-file crash durability remains a separate P0 gate in #377.

Also run direct-host/UPnP fixtures for 0/8, 127/8, 169.254/16, multicast, 240/4 and 255.255.255.255 rejection; verify correct operation of LAN, legacy VPN, and existing TEST-NET fixtures on Windows.

Absolute header-deadline candidate for #382 is now in the newer isolated branch `fix/directory-header-absolute-deadline-20261122`: `_DeadlineHeaderReader` uses select() and monotonic time for total line/header budget, while keeping prefetched POST bytes and restoring normal idle timeout on blank header terminator. Three new exact-source regression methods are committed to `server/directory/test_directory.py`; four reconstructed local loopback tests pass. **Still unverified in exact full source, Windows, real Redis and staging load**. Keep #382 OPEN until real acceptance. No CI workflow was added or run.

Manual only: `python -m unittest discover -s bbport/tests -p test_coop_update_preflight.py -v` and `python -m unittest discover -s bbport/tests -p test_coop_launcher.py -v` on exact branch source, both Windows and Linux. Do not enable event-triggered CI workflows or modify production endpoints.

