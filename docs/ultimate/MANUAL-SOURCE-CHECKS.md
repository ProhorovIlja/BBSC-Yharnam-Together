# Manual source checks — playable Yharnam Together

This document contains **on-demand commands only**. It intentionally does not schedule any tasks, create a watcher or enable a GitHub Actions workflow. Run checks only for the current authorized development request and the exact branch/commit being evaluated.

## Launcher and private support bundles

From the repository root, with Python 3.11+ on the host under test:

```sh
python -m unittest discover -s bbport/tests -p test_coop_launcher.py -v
python -m unittest discover -s bbport/tests -p test_launcher_upnp.py -v
python -m unittest discover -s bbport/tests -p test_support_bundle.py -v
python -m unittest discover -s bbport/tests -p test_portable_update_zip.py -v
python -m unittest discover -s bbport/tests -p test_coop_update_preflight.py -v
```

Cover actual Windows and Linux. The support-bundle tests use synthetic credentials and must never be given real accounts, game dumps or private server logs. For the unmerged 2026-11-22 updater branch, exercise duplicate, contradictory, oversized and Unicode Content-Length values using Python's actual HTTPMessage, then verify the interrupted-download and update-recovery tests on Windows. For the unmerged support-allowlist branch, verify that unknown settings, per-server credentials and malformed public-key pins cannot enter the generated coop.json while leaving the player's real settings unmodified.

## Regional directory: Redis state and HTTP socket framing

Install test dependencies into a disposable virtual environment (do not alter the production server):

```sh
python -m pip install -r server/directory/requirements.txt 'fakeredis[lua]>=2.23,<3'
cd server/directory
python -m unittest -v test_directory
```

The tests include malformed/duplicate Content-Length, finite POST deadlines, shard address rejection, typed metrics and simulated Redis leases. On the unmerged HTTP-worker branch also execute its live socket saturation/503/recovery regression, with dedicated staging load and Windows TCP reset checks before deployment. They do **not** prove production DoS resistance. For any candidate deployment, use a private staging instance with an explicit rollback plan and separate authorization.

## Client Discord presence parser and frame caps

Portable fixture only, from the repository root. On Linux with C++20:

```sh
g++ -std=c++20 -O2 -Wall -Wextra -Werror -Ibbport bbport/tests/test_discord_activity.cpp -o /tmp/test_discord_activity
/tmp/test_discord_activity
```

On Windows from an MSVC Developer PowerShell:

```powershell
cl /nologo /std:c++20 /EHsc /W4 /Ibbport bbport/tests/test_discord_activity.cpp /Fe:test_discord_activity.exe
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
./test_discord_activity.exe
```

The unmerged Discord JSON-field branch adds tests for legal JSON whitespace, escaped key-lookalikes, Unicode names and surrogate pairs. The helper fixture checks frame-size policy, valid opcodes and basic JSON/join contracts; it does not exercise the actual Win32 named-pipe loop inside the installed game. Real Discord join/ask-to-join and teardown still require an attended runtime test.

## ShadNet region and image smoke

Use an isolated build machine with Docker and the pinned protobuf submodule:

```sh
git submodule update --init --depth 1 server/externals/protobuf
docker build --target region-verify -f server/hosting/Dockerfile .
docker build -f server/hosting/Dockerfile -t yharnam-shadnet:manual .
```

Neither command deploys, runs or restarts the public server. For a separate image smoke test, explicitly run a disposable container after confirming ports and data mounts cannot access production.

## Acceptance boundary

Record: exact tested SHA; platform and Python/Qt/compiler versions; command; pass/fail and failed cases; for a shipped product also installed Windows launcher/Discord, Bloodborne 1.09 multi-client and durable save acceptance. Never equate a passing source fixture or container image with verified gameplay, NAT traversal, relayed transport or production rollout.

Historical CI checks from PRs #355, #363, #364, #366, #369–#374 remain inspectable on GitHub as evidence, but no new event-triggered CI workflow is retained for the directory or Discord fixture. The additional support-archive check in the preexisting launcher workflow was reverted; run it manually using the command above.
