# 2026-11-22 playable source hardening — combined manual candidate

Status: **unmerged integration branch**. This is **not** a game release, production deployment, installed-game acceptance, or complete hybrid P2P implementation. No scheduled, recurring or event-triggered tests are enabled by this branch.

Base: previously validated main `fdbdbc67a19edc2fc8015fdf710ad1905104935f` (documentation-only update of the previous main source).
Integration combines the source and tests from four independently staged branches. All eight paths below are present together in this branch, with no changes to production server credentials, networking ports, user saves or retail game assets.

## Contents and ownership

| Area | Modified paths | Existing tracker | Candidate change |
| --- | --- | --- | --- |
| Portable Windows updater | `bbport/launcher/bbport_update_zip.py`, `bbport/tests/test_portable_update_zip.py` | #283 | Reject duplicate/ambiguous/signed/Unicode/pathological HTTP Content-Length before download, retain acceptable chunked streaming. |
| Support ZIP | `bbport/launcher/bbport_support.py`, `bbport/tests/test_support_bundle.py` | #233 | Export only reviewed settings, redact credential-like keys, validate publicly pinned server keys. Does not scrub attached raw logs/dumps. |
| Game client Discord | `bbport/gpu/bbcoop/discord_activity.h`, `bbport/tests/test_discord_activity.cpp` | #119 | Decode JSON string fields with legal whitespace, escaped quotes, UTF-8/Unicode and UTF-16 surrogate pairs; ignore lookalike keys inside strings. |
| ShadNet directory | `server/directory/directory.py`, `server/directory/test_directory.py` | #376 / umbrella #3 | Limit active HTTP request workers to 256; best-effort 503 when saturated; always release a slot on worker completion or thread creation failure. |

## Evidence already obtained

These **isolated reproductions** used separately assembled copies of the modified functions, **not** the exact repository build. Be explicit about this limit:

- Portable update: 16 synthetic HTTPMessage header cases passed in local CPython, including duplicate headers, outer OWS, chunked without length and huge integers.
- Support settings: local Python test passed with multiple synthetic account/session secrets and malformed nested values; live settings not mutated.
- Client Discord JSON: isolated Linux g++ C++20 build passed ten assertions, including escaped fake keys, whitespace, surrogate-pair emoji and invalid escapes.
- Directory concurrency: isolated CPython live TCP loopback test passed with a one-worker budget, 503 overload, completion and slot recovery.

No full repository, Windows launcher, actual Win32 named pipe, complete fakeredis, Docker, load, or installed Bloodborne 1.09 run was performed for this **new integration head**.

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
- Preserve P0 #22/#35/#137 personal save and reward integrity; #21/#23/#63 hunter/NPC divergence; #80 direct authenticated P2P with relay fallback; and all real Bloodborne 1.09 multi-hunter acceptance.
- Avoid source-workflow files, push/PR event CI launches, production deploys and automatic scheduled tasks without the owner's separate explicit authorization.
- Source comparisons: HTTP framing rejection follows RFC 9110/9112's permitted error treatment; this is a conservative client policy, not an alleged live exploit. Private Nov 14 bug register is not mirrored into public GitHub.

For earlier merged fixes and historical CI, see `docs/ultimate/ISSUE-TRIAGE.md`, `docs/ultimate/DEVELOPMENT-STATE.md`, and `docs/ultimate/MANUAL-SOURCE-CHECKS.md`.
