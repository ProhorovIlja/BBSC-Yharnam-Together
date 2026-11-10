# Ultimate B55: target-bound boss rematches, save-matched NG+ backup, global source review

**Date:** 2026-11-10. **Parent:** B54 Draft #117; **tracked:** #116, #22, #35, #70. No release / no production access.

## Concrete B54 code flaw and repair

B54 `UltimateJourney::Confirmation` bound a one-use confirmation to action, character, save revision and `Place` only. If the player selected Boss A and a caller changed the selected boss to Boss B at another arena but kept the same character, save revision and `Place::BossLamp`, the old confirmation would be accepted. Likewise a reload into another map with no save-write and a changed NG+ cycle could retain old confirmation scope. B54 also accepted any `verified_backup=true`, even when the purported backup belonged to an earlier save revision.

In the *actual* `emulator/src/core/ultimate_journey_policy.h`, the game adapter is now required to provide:
- nonzero `world_epoch` that advances for **every** map/world reload; a known `cycle_index` (0 for the first cycle, unknown means deny);
- for rematch, nonzero `boss_id` and `arena_key` describing the specifically selected boss and actual arena;
- for NG+, the `verified_backup_save_revision`, which must match the character's current `save_revision`; `verified_backup` alone no longer suffices.

`Offer` pins **character + save revision + world epoch + playthrough cycle + selected boss + arena + action + location**. `Confirm` consumes the token before rechecking current input and cannot authorize a switched boss, arena, map/world, character or cycle. Rematch is still denied in co-op, on invasion or while saving until real safe instancing exists; no first-kill rewards/progression/notifications are authorized by this policy.

`tools/ultimate/ultimate_journey_policy_smoke.cpp` adds C++20 tests for the exact flaws (switch to different boss at same lamp, alternate arena, reload without save, NG+ cycle change, missing world/cycle/boss/arena and backup mismatch), in addition to all B54 tests. **Important:** compilation passes do not prove the game adapter emits trustworthy world epochs, backup generations, boss kill records, or captures crashes atomically. No gameplay hook uses this policy yet.

## External research reviewed this pass

| Source and state (2026-11-10) | Relevant candidate | Safe intake action |
| --- | --- | --- |
| Official Yharnam Together [PR #554](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/554), OPEN | Host's home world does not roll back to the original solo snapshot | P0: read HomeWorlds changes and migration rollback; reject rename-failure fallback that deletes the last-good file. Independently test hosts/guests and both public/local server world identity before transplant. |
| Official [PR #548](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/548), DRAFT | `PhantomKeyItemLedger` persists owed badge/tool across game restarts and successive guest sessions | P0: check append/dedupe/atomic persistence and per-character/new-slot isolation against our already owner-tagged in-memory deferred queues; verify inventory delivery, do not grant duplicates. |
| Official [PR #560](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/560), OPEN | Correct server connection/sign-in error instead of misleading 'not signed in to PlayStation Network' | Extract diagnosis state machine, Unicode messages, no password/token display; native menu and headless real-world tests required. |
| Official [PR #564](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/564), MERGED | Guest must not respawn its own kill while host kill message is still in flight | Existing B48 #107 adapts a source-scoped guard. Compare upstream remaining edge cases; don't duplicate fixed logic. |
| [droogie/bbhost PR #233](https://github.com/droogie/bbhost/pull/233), MERGED | CPU scheduling/command-buffer staging, low thread count and 6 GB VRAM; Unicode paths | Benchmark p50/p95/p99 CPU/GPU and 1% low on common hardware; no blind copy of renderer or GPL-incompatible code. |
| [bbport.de changelog](https://bbport.de/changelog/) 1.9.8.4 (8 Nov) | Russia relay route for Seamless and SuperMedo chalice glyph search | Compare network failure modes, relay encryption/cost, no service changes until measured. |
| Same changelog 1.9.8.3 (8 Nov) | Guest's personal world no longer replaced by host's progress, Bath Messengers dialog restored | Compare fix to upstream #554 and existing issue #22, do not assume same implementation. |
| Same changelog 1.9.8.2 (7 Nov) | 5 s stale peer connection reset and relookup; relay fallback | Reference for reconnect state machine and delayed summons; prefer actual metrics/reproduction under our own server/client protocol. |
| Same changelog 1.9.8.1 (6 Nov) | Event-mod empty-instruction event patcher accepts zero instructions | Candidate for compatible event patcher with hostile/malformed input bounds; mod tests #70. |
| [Bloodborne Enhanced](https://www.nexusmods.com/bloodborne/mods/19) and [Jgamrot/yharnam-pc](https://github.com/Jgamrot/yharnam-pc) | Manual NG+, lamp boss rematches, QoL | Behavior reference only, preserve permissions and isolate gameplay state from co-op story. |

The list is a **targeted, time-bounded source intake, not a claim to have inspected every repository, fork, branch or file on GitHub**. Related old Drive history and separate native .exe charter remain indexed by the cross-chat ledger, but no inaccessible data is assumed checked.

## Non-negotiable release gates

1. Full implementation of character-scoped `save_revision`, `world_epoch`, `cycle_index`, boss/arena identification and verified **durable** backup for all supported CUSA 1.09 versions. NG+ rollback must survive a mid-operation process crash, full disk, antivirus locking and power loss.
2. Boss rematch in a separate temporary instance with no permanent enemy-death/quest/first-kill flags or native achievements, and clear opt-in rules for repeat rewards. Multiplayer rematches require tested per-party approval, reconnect, wipe and public-server isolation before enabling.
3. Preserve safe current production. Do not delete an existing personal-world file on failed backup/rename/migration; verify asset ownership and gameplay-mod licensing.
4. Run a full Windows game build, 2–5 player rig with clean isolated saves and private rollback snapshots, and p50/p95/p99 latency/frame/VRAM measurements before declaring a feature finished.

**Implemented here:** B54 safety gap fixed at source level plus regression tests/CI. **Not implemented:** boss ESD/talk actions, real NG+ transitions, rematch enemy spawning, P0 owner-world and key-item fixes, production sync and Fornex deployment.
