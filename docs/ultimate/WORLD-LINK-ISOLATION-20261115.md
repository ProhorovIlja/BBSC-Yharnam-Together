# Personal progress and shared transport isolation

Date: 2026-11-15 (Europe/Moscow).
Base: `05761b877ba3c24401df90c412de86387f13de42`, stacked on PR #249.

## Changes

The real client/server transport in `server/coop/game_link.h` now rejects a frame
addressed to a previous local run before updating liveness, changing the remote
instance, acknowledging reliable data or resetting receive buffers. It still
advertises the current local run so discovery and restart recovery can proceed.

A valid remote restart drops queued visual snapshots from the old stream along
with its old sequence space. Fresh snapshots start at zero. Previously, an old
queued snapshot with a high sequence could suppress subsequent new snapshots.
The existing rule preserving a recent join hello and its reliable suffix remains.
There is no wire format change.

The personal-world source changes from upstream
[PR #592](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/592)
are applied selectively to the three production source/header files. The upstream
merge is `ced3f34d919feecd4e4348b621ed0820385fcdd1`, with source head
`2d287f9c906fa41469408c1c3483477a2fd73920`. Its status is merged, superseding the
earlier research classification as open.

- A guest backs up its own world before joining a world the host has not created yet.
- Existing-world backups are captured before the host's lamps are applied.
- A former guest creating a new home world first restores its own loaded blocks;
  unloaded backup blocks remain available for subsequent loads.
- The guest's saved personal lamp flags are available even on a title-screen join.

Upstream PR #524 (travel lock inversion, merge
`3d2a81c92b80aac8a27bb0cd35bf4368f3cbf0e4`) was already present in the base;
it was not imported again. PR #502 is closed and unmerged; the base already has
the join-hello preservation behavior. These are individual checks of named
changes, not an exhaustive review of all GitHub forks or branches.

## Executable checks

`server/tests/test_game_link_restart.cpp` compiles the actual shared transport
headers, without replacement transport implementations. All four new scenarios
failed against the unmodified base and pass with the fix:

1. A wrong local recipient cannot reset a current stream, remove its pending
   reliable data or refresh its liveness; both same and different remote IDs are tested.
2. Old queued visual sequence numbers cannot enter the new stream.
3. A rejected frame cannot discard a partly received 1,500-byte co-op message.
4. An ignored old-target frame still produces a current-run discovery response.

The 12 existing GameLink GoogleTests are also run against the same production
header: packet encoding, ordering, ACK loss, unreliable freshness, batching,
restart, join hello, keepalive, bounded resend backoff and silence/recovery.

`tools/re/tests/test_team_world_preservation.py` generates and compiles complete
production load, backup, restore, file serialization and guest lamp functions.
Synthetic flag memory and temporary files replace game memory and user saves.
Six scenarios check immediate new-world backup/solo restoration, backup before
host lamp changes, guest-to-host restoration across two block loads, repeat-load
backup preservation, slot-aware cached flag retrieval/removal, and a title-screen
guest relighting both personal and team lamps from separate sources.

The first three preservation scenarios reproduced the original bugs against the
base. A baseline-only adapter supplied the then-absent saved-lamp accessor; it is
not used in current production-source checks. Memory access, protobuf values,
flag ownership and lamp classification, logging, invasion handling and NG+
detection are adapters. The fixture does not validate retail flag classification,
real memory offsets, a real save or gameplay.

Reproduce without Qt or game files:

```sh
git clone https://github.com/google/googletest.git /tmp/gtest
git -C /tmp/gtest checkout 52eb8108c5bdec04579160ae17225d66034bd723
cmake -S tools/ultimate/network-tests -B /tmp/world-link-tests \
  -DULTIMATE_GTEST_SOURCE=/tmp/gtest
cmake --build /tmp/world-link-tests --config Release --parallel 2
ctest --test-dir /tmp/world-link-tests -C Release --output-on-failure --verbose
```

The workflow `Ultimate world and shared game link` runs this suite on Linux,
Windows and macOS. GoogleTest is pinned to v1.17.0's exact source commit.
The server's normal CMake test registration also includes the restart regression.

The existing travel-lock fixture now compiles the actual `OffersTeamTravel` and
`TravelVote` implementation region rather than linking the entire host-rules
translation unit, whose unrelated fmt/enemy-tuning dependencies prevented the
standalone test from building. No travel logic is replaced with a test stub.
The local RE suite collects 136 tests: 132 pass and four retail-event-file checks
skip because no game event tree is provided. The POSIX CI jobs run this suite too.

## Acceptance boundaries and next priorities

These changes are reviewable source fixes. Real multiplayer playtests, long-run
save recovery, filesystem failure injection, a complete client build and network
measurements are still required before release. No measured FPS, latency or
server CPU improvement is claimed by these unit/fixture results.

Recipient validation does not authenticate a sender. A delayed old remote-run
frame addressed to the current local run remains a separate lifecycle problem;
these checks do not provide general replay protection. Authenticated session
generation/endpoint binding must precede activating the hybrid P2P path.

The existing personal-world writer does not return an acknowledged/durable write
result to the load policy. Disk-full/permission/crash failure handling needs its
own transactional tests before claiming save-loss prevention under I/O failure.

Native startup remains a separate release gate. The prior 105-prefix Linux
diagnostic is not playable Bloodborne. The prepared-native profile registry is
still empty, and retail rendering/gameplay/ABI coverage is incomplete. Passing
these transport/fixture tests on three OSes does not establish a native game port
on any of them. No game bytes, private chat text or retail-derived assembly are
included in this change.
