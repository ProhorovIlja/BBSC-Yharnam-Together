# Seamless Hunt Ultimate — playable track contract

Scope decision, 2026-11-15. This is a release and integration contract, not an implementation, deployment or claim of completed testing.

## Fixed decisions

- Extend the current Yharnam Together + bbport client, launcher and server. Retain the existing seamlesshunt.com service, player entry point and backend continuity. Server improvements are in-place upgrades after compatibility and rollback validation, not a move to another community's service. No production changes in this branch.
- The EBOOT-free runtime is paused for this track. Do not block playable improvements on it. Do not describe the current runtime as EBOOT-free.
- Preserve functions and existing settings when simplifying or replacing code. A rewrite must demonstrate correctness and a measurable resource or usability win on the same workload. Compare against a pinned upstream build and record both regressions and wins.
- Keep existing issues and Drive handoffs as evidence and backlog; this document is a routing index, not a replacement. New work records owner, branch, pinned SHA, donor/licence, test scope, and release status. Keep raw chats, saves, game files and credentials private.

## Gates and existing work

| Area | Existing work | Gate for the playable candidate |
| --- | --- | --- |
| Personal progress and rewards | #22, #35, #250, #251, upstream #592 | Backup failure defers join; verify lamps, doors, quests, boss flags, persistent loot and slot/character isolation after leave, crash, reconnect and update. Keep optional additive Shared Progress separate from live host-world state. |
| Online | #80, #252, #103, #119, #177 | Existing relay is compatible fallback; authority keeps matchmaking, admission, world, rewards, PvP outcomes and travel. Negotiate authenticated direct visual streams only after separation from mixed state packets. Test loss, reordering, NAT changes, duplicate admission, rollback and 2/3/5 clients. Quick Match only for eligible sessions that allow invasions. |
| Client and GPU | #25, #84, #99, #130 | Reproduce rendering/crash signatures before importing patches. Baseline without vendor upscaler or FG; optional features gated by hardware and driver. Compare cold/warm and long runs at matched settings: p95/p99 frame time, RAM/VRAM peaks and growth, loading, input and process exits. Include older and modern supported hardware. |
| Launcher | #26, #77, #85, #179, #242 | Play/EXE/Steam parity; responsive UI and idle CPU/RAM; explicit startup failure; preserve settings, saves and mods on upgrade; test rollback, Unicode paths and clean shutdown. |
| Gameplay and QoL | #103, #116, #119; project bells/duel and progression handoffs | Preserve controls, independent display/chat options and role isolation. Test NG+, rematches and mods without contaminating campaign state or public stats. Add bells as entry points only under the current team-system contract, not a parallel legacy backend. |
| Website | #85, #100; Drive Players/Team Chat/Boss Feed handoff | First verify exact selected-service online count and server-confirmed boss/activity stream against client and website. Expand to location/lamp distributions, deaths, co-op/PvP and Chalice statistics, profiles and leaderboards as trusted event sources become available. Hunter's Dream is a feature benchmark, not a data source or replacement backend. |

## Website data path

Client observations and server-authoritative facts have separate provenance. Prefer facts already accepted by the server for counts, achievements and competitive records. Unknown, stale or unsupported is distinct from zero. Deduplicate by authoritative event identity; restoration, retry, reconnect and boss rematch must not count as new campaign wins. Anonymous aggregates by default; named profiles or public activity require sharing controls. No raw packets, chat, saves, credentials or IP addresses in public telemetry.

Use a bounded asynchronous queue and an aggregated read model; a slow database or website must not stall matchmaking or game traffic. Define freshness, duplicate behavior, retention, queue-full behavior and version compatibility before rollout. Public website requests should not query hot game state directly. Proposed additions require comparison with existing website feeds before implementing a second collector. 3D map is not a prerequisite for statistics or location lists.

## Source intake and release

Use the existing source-watch registry and #9, expanding via upstream, forks, branches, PRs, tags, releases, external projects and mod communities. Evaluate exact diffs, prerequisites, source rights and tests. Supermedo/deadinside, independent droogie bbhost, Mrsuss60/visy, Nightwatch, CLS, Lantern Engine, shadPS4/shadNet and signaling forks are donors, not wholesale merge targets. New rendering features are optional and never raise the baseline without evidence.

First integration candidate: preserve #250/#251 personal-world behavior and #252 transport parity, validate guest rewards and launcher lifecycle, and check an isolated client/server-to-web test with aggregate presence and duplicate/replayed boss events. Run against a pinned baseline with disposable profiles; collect server CPU/RSS, bytes/sec per hunter, tick/queue delay and reconnect outcomes with/without stats publishing. A unit test, merge or artifact build is not game validation or production release.
