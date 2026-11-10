# Ultimate B42: server-authenticated team chat delivery through the existing reliable stream

**2026-11-10**, stacked on [Draft B41 PR #97](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/97) (Linux and Windows C++ policy tests passed). Issues [#95](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/95) text and [#96](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/96) proximity voice. B42 is the first actual **server protocol** piece, not yet an in-game chat UI.

## Source-level integration
- Added additive `ChatSend` and `ChatEvent` to `coop.proto` with envelope tags **53** and **54**. Existing tags, meaning and protocol 8 preserved for backwards-compatible old clients. Existing game payloads are unchanged.
- `Service::Take` accepts `ChatSend` independently of gameplay world presence, so team lobbies may talk at the title screen. A request is discarded without a signed-in, non-quiet and non-hostile link whose `member.lobby` **exactly equals** `AuthenticatedMember(member.online_id)`. On synthetic legacy unverified identities chat stays disabled, not incorrectly trusted.
- `Service::OnChat` snapshots *current* `TeamLobby::TeamOf` membership from connected, authenticated links. Only `scope=2` TEAM messages are routed through B41 `Comms::Gate` and its strict UTF-8, flood and recipient rules. Scope 1 GLOBAL and scope 3 DIRECT are **disabled**, for now, because cross-shard global and private recipient settings are incomplete.
- Successful messages reach only one authenticated current link per team peer; sender receives a status-only acknowledgment. No client-provided sender text, team id, credentials or IP is ever forwarded. Neither accepted text nor failed text is logged or persisted in the world. No dependence on map state, position or combat tick.
- Oversized protobuf text/recipient fields are rejected before further processing (512 byte text ceiling, max server member field for target). `Gate` additionally verifies Unicode/scalar and rate constraints.
- `test_bloodborne_world.cpp` uses the existing real server CoopStream loopback protocol rig: two teammates, separate third user and spoofing fourth user; validates exactly routed team text, group leave, globally disabled, direct disabled, pre-login denied, invalid identity denied and flood cap. No real game files.
- CI checks strict source constraints then compiles actual Qt6/protobuf C++ service in isolated Docker and runs all registered CTests; no production deployment or user saves.

## Still to develop
1. Client-side `ChatEvent` view, text input, keyboard/controller bindings and localized UX. The server can route a synthetic authenticated `ChatSend`; current launcher cannot show or send it.
2. Server-side privacy/block preferences wired into `Gate::Peer`, exact name-to-account resolution for DM, and cross-shard global delivery with authenticated dedupe and bounded backpressure. Do not enable until tests and moderation/opt-outs.
3. Real P2P/relay voice transport with Opus and spatial permissions, separate from the ordered stream.
4. Real Windows clean-package 2–5 device/latency/connectivity trials. Fornex, save data and private game assets untouched.

## New external improvements monitored
- [Supermedo/bloodborne_pc](https://github.com/Supermedo/bloodborne_pc) Windows **v1.9.8.2** (2026-11-07) reports dead-connection reuse causing repeated summons to fail, with server address refresh / relay fallback after 5s. Audit our connection lifecycle before adaptation; it is not automatically the same code path.
- [droogie/bbhost PR #217](https://github.com/droogie/bbhost/pull/217): signaling / lifecycle and spectator camera API, separate architecture; [PR #231](https://github.com/droogie/bbhost/pull/231) controller input prompt graphics; [PR #229](https://github.com/droogie/bbhost/pull/229) trophies popup. Compare provenance, hook availability, performance and license first.
- BBGL [mark3317/bbgl](https://github.com/mark3317/bbgl) LAN/VPN Party modes remain B39/B41 source foundations, not yet operational.
- Branch topology: local counting [PR #91](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/91) and 1.09 region check [PR #92](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/92) are parallel/diverged. Must reconcile before release.
