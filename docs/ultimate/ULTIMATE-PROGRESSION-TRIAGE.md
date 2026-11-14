# Ultimate: personal progression and initial bug triage

Status: design and regression intake, not a gameplay fix. This file contains technical paraphrases only, not raw chats, credentials, saves, screenshots, or account identifiers.

## Progression contract

The host world is the live session view, never a replacement personal save. Keep it separate from the guest's personal world even when both contain the same area. Add an in-game per-character Shared Progress setting, default off until verified. Off disables persistent import of shared world changes, not normal personal rewards earned in co-op. On imports only whitelisted, witnessed, committed events from the current session. No backfill of the host's existing world. Scope pending events to character identity (not just slot), NG cycle and source session; freeze the choice for a session so retries cannot silently change policy.

Eligible candidates: verified lamp unlock, shortcut completion, boss completion with valid prerequisites, or explicitly awarded personal loot. Use canonical IDs and per-character idempotency. Already-earned flags and loot never reset or duplicate. Persist boss/loot outcomes consistently: a completed boss must not strand its mandatory unique reward. A lamp's visual/entity state and its travel availability are separate. Do not union raw flags. NPC routes, deaths, rewards, area phase and mutually exclusive quest branches require per-quest transitions. Unknown or conflicting transitions leave personal progress unchanged; retain a diagnostic without disclosing save contents. Invasions and duels never write shared campaign progress. Backup first; no automatic repair of already damaged saves.

Acceptance: BL32 joins low-progress host, returns offline and retains Old Yharnam, Hemwick, doors, lamps, bosses and quest choices. Reverse direction: fresh guest gets only events actually completed together and no pre-existing host unlocks. Repeat off/on, leave, crash, reconnect, restart, same slot/new hunter, different NG, and three/five-player sessions. Compare persistent personal flags and inventory, not merely in-session visuals. Repeat with one client loading and with duplicate/out-of-order events; never test on production saves.

## Initial audit (reported does not mean reproduced)

| Area | Symptoms / case | Evidence or next check |
| --- | --- | --- |
| P0 personal world | Higher-progress guest loses access to Old Yharnam/Hemwick; possible boss rollback; level/inventory remain | Existing fork #22. Upstream PR #554 addresses host rollback when playing alone and updater save protection; explicitly restores a guest's separate world on leaving, not an additive merge. Verify exact fork build and distinguish active guest view from on-disk state. |
| P0 quest and travel | Cathedral Ward entrance closed without prompt, including after offline restart; Tomb of Oedon hunter/Eileen absent or briefly visible; unexpected Iosefka/blue creature; Dream headstones unusable by host or guest after co-op travel | Separate repros; capture prerequisites, character flags, map/authority and prompt state before join, during session and after offline relaunch. Do not force all doors or activate all NPCs. |
| P0 rewards / objects | Cleric Beast / Sword Hunter Badge: pasted account ambiguous about whether missing; empty/noninteractive chest after disconnect; missing crates | Upstream PR #548 explicitly reproduces *missing* Badge after guest quit/restart and fixes that ledger case. Fork #35 is a separate manager-unavailable and slot-fencing investigation. Chest prompt/visibility and quest rewards still need separate repros. |
| P1 combat, interaction and animation | Enemy already dead on guest while host hits it, echoes later; movement possible but interaction/attack/dodge reported broken; Ludwig stuck or fog after kill; Messenger decoration animation loops; Doll level-up stuck | Run paired host/guest captures with exact build, map, role, boss phase, input lock and animation state; compare offline. Do not infer one shared cause. |
| P1 rendering and travel | Transparent/missing assets; players invisible except HP; spawn through floor; CLS catch-up repeatedly teleports separated guest | Compare renderer/streaming with network entity ownership; require collision/map readiness and no unsolicited distance-based teleport. Keep distinct from save corruption. |
| P1 stability and launcher | Slow drag, slow game launch and shutdown, long-session degradation, lobby missing exit | Measure cold/warm launch, shutdown phases, frame-time and process memory across long sessions; experimental drag change exists but needs Windows confirmation. Leak is unconfirmed. |
| P2 social and compatibility | Declined friend request blocks retry for a long time; old menu allegedly scans the entire server for mods | Verify server cooldown versus UI state, preserve anti-spam; reproduce old menu separately and keep compatibility checks scoped to involved session/peers. |

## Invader HUD and recovery (separate from campaign saves)

Invaders see their own hostile-side HUD, not the defenders' party roster. Host DBNO setting controls the rule. Off: dead invader leaves. On: a solo invader leaves on death; with two, the surviving invader may revive the downed ally by the existing body-hit interaction pattern. When both are down, end both hostile visits. Server validates faction, current reservation/session, eligible target, and authoritative hit/revive ordering; defenders cannot revive an invader and stale packets cannot revive an ended visit. Test simultaneous deaths, disconnect while ally is down, duplicate revive, visibility and cleanup. No changes to the current game in this intake.

## Reference points

- Fork issue #22: https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22
- Fork issue #35: https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35
- Upstream home worlds: https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/554
- Upstream phantom key-item ledger: https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/548

For the full audit retain both the complete deduplicated inventory and an outstanding-only view. Record affected build, role, reproduction, source fix/commit, whether present in the target fork, and whether verified in game. A donor fix is not proof of a fix in Ultimate.
