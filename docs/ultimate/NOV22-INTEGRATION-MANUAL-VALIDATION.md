# 2026-11-22 playable source hardening — combined manual candidate

Status: **unmerged integration branch**. This is **not** a game release, production deployment, installed-game acceptance, or complete hybrid P2P implementation. No scheduled, recurring or event-triggered tests are enabled by this branch.

Base: previously validated main `fdbdbc67a19edc2fc8015fdf710ad1905104935f` (documentation-only update of the previous main source).
Integration combines the source and tests from four independently staged branches. All eight paths below are present together in this branch, with no changes to production server credentials, networking ports, user saves or retail game assets.

## Contents and ownership

| Area | Modified paths | Existing tracker | Candidate change |
| --- | --- | --- | --- |
| Portable Windows updater | `bbport/launcher/bbport_update_zip.py`, `bbport/tests/test_portable_update_zip.py` | #283 | Reject duplicate/ambiguous/signed/Unicode/pathological Content-Length; accept only CPython-decodable plain chunked transfer, reject partial HTTP 206 and non-200 responses before download. |
| Support ZIP | `bbport/launcher/bbport_support.py`, `bbport/tests/test_support_bundle.py` | #233 | Export only reviewed settings, redact credential-like keys, validate publicly pinned server keys. Does not scrub attached raw logs/dumps. |
| Game client Discord | `bbport/gpu/bbcoop/discord_activity.h`, `bbport/tests/test_discord_activity.cpp` | #119 | Decode JSON string fields with legal whitespace, escaped quotes, UTF-8/Unicode and UTF-16 surrogate pairs; ignore lookalike keys inside strings. |
| ShadNet directory | `server/directory/directory.py`, `server/directory/test_directory.py` | #376 / umbrella #3 | Default to 64 concurrent HTTP request workers, configurable through DIRECTORY_MAX_HTTP_WORKERS in the range 1–256; best-effort 503 with a 100-ms socket write budget when saturated; always release a slot on completion or thread-start failure. |

## Evidence already obtained

These **isolated reproductions** used separately assembled copies of the modified functions, **not** the exact repository build. Be explicit about this limit:

- Portable update (expanded after initial handoff): a source-faithful local CPython module passed 3 unittest methods (21 HTTPMessage header patterns, 7 abnormal HTTP statuses, 5 finite-download cases). Duplicate Transfer-Encoding, unknown/gzip transfer encodings, unexpected 206 Partial Content and early refusal before writes are now covered. No Windows updater packaging test yet.
- Support settings: local Python test passed with multiple synthetic account/session secrets and malformed nested values; live settings not mutated.
- Client Discord JSON: a reconstructed matching-source Linux C++20 portable fixture compiled and passed with both g++ and clang++ (-Wall -Wextra -Werror), checking escaped keys, whitespace, surrogate-pair emoji, invalid escapes, join secrets and IPC frame sizes. No Win32 named-pipe test.
- Directory concurrency: updated faithful isolated CPython 3-method unittest suite passed: actual TCP loopback held one POST worker, received 503 on second client, recovered the slot, rejected invalid worker limits and released a permit after a mocked thread-start failure. Production class now defaults to 64, with a configurable 1–256 cap. No complete real directory/fakeredis suite or staging load acceptance.

No full repository, Windows launcher, actual Win32 named pipe, complete fakeredis, Docker, load, or installed Bloodborne 1.09 run was performed for this **new integration head**.

## Additional manual verification after the four-branch integration

These are **explicit foreground checks**, not full-repository CI, scheduled jobs or production tests:

- **Python HTTP framing:** a local source-faithful CPython 3-method unit suite passed (21 header patterns, seven rejected non-200 responses, bounded streaming). A separate disposable socket-server fixture returned seven raw HTTP/1.1 responses through actual `urllib.request.HTTPResponse`, covering normal Content-Length, duplicate values, chunked decoding, conflicting length+chunked, unknown gzip transfer, HTTP 206, and EOF-delimited replies. All seven passed, with no real downloaded or installed ZIP.
- **Discord IPC:** portable helper copied from candidate source compiled with GCC and Clang C++20 under `-Wall -Wextra -Werror`. An isolated 25,000-case deterministic parser stress run with Clang AddressSanitizer and UndefinedBehaviorSanitizer passed. A 4,096-case deterministic round-trip/malformed test was also committed to the candidate's C++ fixture and checked in a local stand-alone GCC/Clang+sanitizer build. Real MSVC, Win32 named-pipe operation and the full game client are still untested.
- **Directory worker slots:** three local Python tests passed on a source-faithful isolated class: TCP stalled POST/503/recovery, invalid cap refusal and simulated thread-start failure. The class now defaults to 64 workers with `DIRECTORY_MAX_HTTP_WORKERS` limited to 1–256; an overload response gets a 100 ms send timeout. This is not a staging load test, Caddy proxy acceptance, or actual fakeredis/server Docker validation.
- **Support ZIP:** three local Python unit methods passed for nonmutating `without_secrets` against nested server credentials, unknown future session fields and malformed key pins. No complete installed support ZIP privacy audit or raw log/dump scrubbing was performed.
- **Upstream duplicate prevention:** the latest Amanises 1.5.1 source includes targeted stuck-loading guest visibility, `KeepOwnWorldAside`, game sign-in URL handling, GPU PM4 and NPC/render crash fixes. Corresponding functions/patch names were verified **already present** in this fork's main; no blind duplicate or incompatible upstream merge was made. Actual five-player and installed client acceptance is still outstanding.

## On-demand validation only

From the checkout of **this exact integration head** (never production):

```sh
python -m unittest discover -s bbport/tests -p test_portable_update_zip.py -v
python -m unittest discover -s bbport/tests -p test_support_bundle.py -v
g++ -std=c++20 -Wall -Wextra -Werror -Ibbport bbport/tests/test_discord_activity.cpp -o /tmp/test_discord_activity
/tmp/test_discord_activity
python -m pip install -r server/directory/requirements.txt 'fakeredis[lua]>=2.23,<3'
cd server/directory && python -m unittest -v test_directory
```

Repeat Python tests and the C++20 fixture using Windows Python 3.11/3.12 and MSVC Developer PowerShell. The full ShadNet container build, timeout/worker saturation under concurrent load, high-latency router behavior, optional Discord join-request UI, and real portable updater rollback need separate attended testing before merge.

Manual failure gates: no successful private player save backup; no guarantee a failed portable update leaves installed files intact; source test process crash; changing client wire or public server API; any new credential in a support bundle; incomplete HTTP response handling; game regression in join, reconnect, party state or save migration.

## Release and issue rules

- Do not close #283, #233, #119 or #376 based only on these new isolated checks.
- Owner-closed historic #22 and completed #349 remain closed. Track remaining *unverified* cross-file save durability/native ACK in new open P0 #377; keep #35/#137 guest rewards, #21/#23/#63 hunter/NPC divergence and #80 direct authenticated P2P/relay open until actual 1.09 multi-hunter acceptance.
- Avoid source-workflow files, push/PR event CI launches, production deploys and automatic scheduled tasks without the owner's separate explicit authorization.
- Source comparisons: HTTP framing rejection follows RFC 9110/9112's permitted error treatment; this is a conservative client policy, not an alleged live exploit. Private Nov 14 bug register is not mirrored into public GitHub.

For earlier merged fixes and historical CI, see `docs/ultimate/ISSUE-TRIAGE.md`, `docs/ultimate/DEVELOPMENT-STATE.md`, and `docs/ultimate/MANUAL-SOURCE-CHECKS.md`.
