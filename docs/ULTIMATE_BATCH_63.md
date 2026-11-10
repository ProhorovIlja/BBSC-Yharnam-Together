# Ultimate B63: fresh game RPC snapshots and Unicode-safe activity strings

**2026-11-10. Parent:** [B62 Draft #127](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/127). Actual source changes and tests; no public release / Fornex deployment.

## Bugs found in OUR production source, not theoretical features

1. `emulator/src/core/bloodborne_party_death.cpp::PostVitalsAndPanel` publishes the last local `PartyPanel` to a guarded global. The Discord IPC thread calls `ReadPartyPanel` every ~2 s, but that old snapshot had **no freshness lifetime**. A game stall, paused/out-of-context map transition or interrupted game tick could leave yesterday's area, BL, class, active boss name and boss elapsed timer in Discord indefinitely. The game does explicitly `SetPartyPanel({})` on a detected missing game data pointer, but this does NOT protect a stalled tick.
2. `discord_presence_policy.h` truncated `details` and `state` by `resize(120)`, then stripped trailing UTF-8 continuation bytes. If truncation landed after the **second byte of a 3-byte sequence**, that algorithm stripped the continuation byte but left the orphan **leading** byte behind, producing malformed Unicode/JSON display on Russian / Asian / other multibyte text.

## Integrated B63 fixes

- **Game thread, one cheap monotonic timestamp:** new `PartyPanel::rpc_snapshot_steady_ms`, set on every *completed* `PostVitalsAndPanel` update immediately before protected `SetPartyPanel`. The value is based on C++ `steady_clock` (milliseconds since monotonic epoch **within the same process**) so wall-clock changes do not falsely refresh an old game tick. Invalid/empty panels initialize to 0.
- **Real Discord publisher, not another service:** before building a rich presence message, Discord compares its own `steady_clock` against the cached panel's timestamp through `DiscordActivity::GameSnapshotFresh`. A sample must be >0, not from the future and at most **10,000 ms old**. A stale sample becomes `PartyPanel{}`; no more outdated game-derived boss/arena, BL, build, death/spectate state or boss timer. The team/lobby status is read independently from its existing live `bbcoop_lobby_view` path, preserving invitation and party information rather than treating the title screen as an always-running character tick. Exact desktop behavior still requires test.
- **Validated Unicode:** replace the broken truncation with `BoundValidUtf8` on both user-facing Discord text fields. It walks 1-, 2-, 3- and 4-byte code points, drops any incomplete sequence *before* its lead byte, rejects malformed continuation, overlong encodings, surrogate codepoints and values above Unicode U+10FFFF. Applies to any output length, with 120-byte upper bound. No additional live game memory reads or strings sent to backend.
- **Exhaustive boundary regressions:** C++20 test checks active/expired/future/missing snapshot lease and exact UTF-8 2/3/4-byte end-of-buffer boundaries, valid UTF-8, invalid overlong/surrogate/too-large/truncated sequences, and Unicode area rendering in ReferenceCard. Existing screenshot B62, B61 two-line fallback, all 16 STR/SKL/BLT/ARC combinations and fight/solo timers continue running.
- **No extra allocations per game tick:** timestamp store is a single integral field in an already-copied struct. Discord's UTF-8 pass is bounded by 120 bytes of user-facing text. Prevent sudden UI reflow from stale boss state, not guaranteed frame-accurate game event delivery.

## Global source intake this pass (NOT indiscriminate cherry-picking)

| External repo / PR | Source-backed contribution | Safe follow-up |
| --- | --- | --- |
| [Amanises-Yharnam-Together PR #524](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/524), OPEN | Travel Together receiver takes `stream_mutex` then waits on `travel_mutex`, while sender takes `travel_mutex` and queues under `stream_mutex`. Upstream proposes a dedicated bounded travel inbox lock and reproduces deadlock via an actual C++20 state-machine test. | P0 network deadlock audit. Compare our `bloodborne_host_rules_game.cpp` and existing Travel Together lock order; adapt fix **only if the inversion still exists**. Do not cherry-pick the whole PR without reading the specific patch. |
| [Amanises PR #559](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/559), OPEN | Guest can be inside session but never signed into Bloodborne's game server; invisible guest/HP=1/1, 176 vs 3,300 packets/min in observed logs. Adds transparent sign-in diagnostic; author could not fully reproduce the root cause. | Verify local auth and backend connection state separately from Team member roster; avoid claiming a proven root cause. No credentials/log dumps to public tickets. |
| [droogie/bbhost PR #217](https://github.com/droogie/bbhost/pull/217), OPEN | Redone signaling/peer connection lifecycle, retry/timeout/mutual activation; spectator camera plugin API 28 and Windows waiting-thread diagnostics. Author warns old clients and servers must upgrade together. | Audit transport protocol compatibility and spectator API/lifetime. **Do not** transplant a protocol-changing networking stack or plugin ABI into existing shadNet clients without versioned migration and isolated 2–5 player proof. |
| [CLSAMG22/BBSC PR #9](https://github.com/CLSAMG22/BBSC/pull/9), OPEN | Repeated guest deaths and boss wipe cause stale HP bars, wrong respawn, repeated reload and stuck loading screens. Proposal coordinates boss bar, host revival and load watchdog. | Source-informed game rig tests for B60/B63 boss timer and boss-name reset, no direct use of unrelated save/reload mechanisms. |
| [Discord Rich Presence guide](https://github.com/discord/discord-api-docs/blob/main/developers/discord-social-sdk/development-guides/setting-rich-presence.mdx) | Discord Activity defines game name, `details`, `state`, `party`, `timestamps`, assets. Two independently controlled text rows only; name and elapsed timer are additional. | Preserve both B62 ReferenceCard and earlier StatusFirst, don't misrepresent 5-row conceptual image as editable native Discord rows. |

This is a bounded source review of specific current PRs and docs; **not a claim that every GitHub repo, fork or commit was searched**.

## Real acceptance gates

- Gameplay test fresh/stale transitions with at least 2s and 10s stopped game ticks, no last map/BL/boss leak; validate legitimate background/main-menu downtime doesn't incorrectly hide current *live lobby* state.
- Real Windows app ID + Discord desktop + 9 supported 1.09 CUSA region versions, DLC/Chalice Unicode and spectator/wipe boss transitions; test long names in actual Discord clients (rendering may still normalize spaces).
- Actual compiling Windows client, full session safety, 2–5 player rig and saves-isolated rollback. Source CI alone is not a playable Ultimate release.
- Preserve previous B62 privacy defaults and no production Fornex, player saves, game binary or copyrighted asset changes.

**B63 scope:** correct stale display and Unicode string corruption in source + tests, no host/world or key-item gameplay fix claimed. Track #9, #119 and #122.
