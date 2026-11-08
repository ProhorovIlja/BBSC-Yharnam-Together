# BBSC: Yharnam Together Ultimate — bugs, screenshots, Issues and regression ledger

> 2026-11-08. This is a **requirements and evidence ledger**, not a list of
> fixed problems. Everything must be cross-checked against an immutable
> CLIENT+SERVER+GAME version before implementation. The latest integrated
> source-only TEST candidate is [#19](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/19).
> Keep the separate native PC port and live Fornex inventory distinct.

## Evidence levels and intake rules

- **USER SCREENSHOT NOTES:** A private Google Drive handoff from 2026-11-01,
  titled *Seamless Hunt — баги кооператива и моды*, explicitly describes
  four regressions derived from the user's screenshots and discussions. This
  ledger imports the **written symptom descriptions**, **not the underlying
  images or any private Discord messages**. Original earlier-chat screenshots
  have **not been independently re-opened in this pass**. Do not claim all
  attached screenshots were inspected or that this list is complete.
- **PUBLIC ISSUE:** State, title, URL and reproduction narrative verified via
  GitHub Issues on 2026-11-08. A closed issue is not proof our fork contains
  the fix. An issue in Nightwatch/visy/BBHost is a *comparison reference*,
  never proof a YT player has the same root cause.
- **SOURCE/PATCH CANDIDATE:** An upstream PR or source function to inspect;
  require base-blob comparison, licensing, tests and targeted playtest.
- **VERIFIED IN FORK:** Only when exact fork commit, CI, fixture and runtime
  build evidence are recorded. Passing source CI is **not** a five-game test.

## P0 — directly reported via user's screenshots / previous messages

| ID | Observed complaint (do not confuse cause with symptom) | Candidate investigation | Acceptance / regression test | State |
| --- | --- | --- | --- | --- |
| USR-001 | Name/HP/team slot visible, but remote hunter body is missing, especially **Hunter's Dream** or **hot join** after host already playing. | Session identity, NetSync, remote actor creation/despawn, party member data requests, map instance. Inspect `emulator/src/core/bloodborne_boards.cpp`, `bloodborne_join.cpp`; compare CLS exact build with official YT 1.3.1 and 1.4.0; correlate [deadinside #422](https://github.com/deadinside28/bloodborne_pc/issues/422) (cross-platform black-screen join), [Nightwatch #6](https://github.com/vladtepes22/NightwatchCoop/issues/6) (guest not an entity) WITHOUT assuming shared root. The private note flags a **hypothesis**, not proof: `FinishWaitingJoins` uses presence of any other hunter on a map rather than the expected member identity. | Host in menu vs already in world, 2/3/5 hunters, Dream/Chalice/DLC, late join, repeated leave-rejoin, independent map travel; assert *the specific expected member* has spawned and has collision/combat state. | REPRODUCE / ROOT CAUSE UNPROVEN |
| USR-002 | Guest sees literal `?ActionEventInfo?` instead of correct role/action text. | Upstream 1.3.1 already has `NameUnnamedGuestRole` in `bloodborne_party.cpp`, called by `PolishMultiplayerUi` and covered by `NamesTheGuestRoleTheGameLeftUnnamed`. Compare actual CLS binary/branch, localization table regeneration, role rows and memory permissions; **do not duplicate upstream patch**. | UI row 6 vs row 7, guest after login/reload/level travel, Russian/English, 5-player team; exact string remains absent. | REGRESSION / EXISTING FIX TO VERIFY |
| USR-003 | After some CLS merges, guests cannot join when the leader is already loaded in game. | Versioned comparison of CLS and official YT, client handshake, lobby vs game-peer, member data, [YT #486](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/486) five-game rig, [deadinside #422](https://github.com/deadinside28/bloodborne_pc/issues/422); don't assume a server lobby denial without a trace. | Five simultaneous/late joins, independent maps, retries, leader reconnect, no waiting-state timeout; capture anonymized transition timeline. | REPRODUCE; PRIVATE CLS MERGE REF NOT YET KNOWN |
| USR-004 | Copied saves/multiple game instances allow repeated messenger-weapon claims or lose Vileblood Register. | Per-instance ID, save separation, gift ownership/claimed flags, scripts, import/migration, no global flag changes without a test. Related [Nightwatch #1](https://github.com/vladtepes22/NightwatchCoop/issues/1) and [YT #508](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/508). | Unique gifts per intended player, no cross-player shop stock depletion, start weapon/Old Hunter Bell/Iosefka vial, Vileblood Register after clone/restore and reinstall. | REPRODUCE / SAVE SAFETY P0 |
| USR-005 | When DBNO is ON, dead team members' HP/name remain visible until **that member actually disconnects**; when DBNO OFF, or a full-team wipe occurs, same disconnect-based roster visibility rule must be respected. | Explicitly requested UX semantics in prior conversation, separate dead/knocked/spectating/disconnected states. | Five hunters, host and guests, simultaneous deaths, full wipe, reconnect/disconnect; assert HUD roster and gameplay state evolve independently. | REQUESTED SEMANTICS / NOT VALIDATED |
| USR-006 | Team cap **five total connected humans**, with possible mixes of allies/invaders; host controls invasions, match filters, friends/invites/quick match/duels, and later optional player-as-boss invasion. | Review YT 1.4.0 team rule / #484/#486 plus server world limits, invader reservations and spectating; do not infer all proposed splits are supported. | 5 friendly; 4+1, 3+2, 2+3 as explicit feature candidates; invite-only/open/friends-only, invasion OFF/ON, duels, mid-fight joins, fair rewards and persistence. | REQUIREMENTS / EXACT ALLOWED SPLITS NEED ENGINE VERIFICATION |
| USR-007 | Website routes show `index.html` instead of clean URLs such as `/download`; authentication DNS/routing previously led to login/sign-up failures. | Historical website/server complaint, **separate web track**. Check Caddy/static hosting rewrite and `/bb/auth/config` vs actual sign-in/up endpoints; no unaudited changes to live Fornex. | Fresh install, deep links, refresh, HTTPS, sign-up/sign-in, server online, no user/account loss. | HISTORICAL / DO NOT ASSUME STILL PRESENT |
| USR-008 | User repeatedly encountered `Error in input stream` during long GitHub/internet/CI work. | Tool/response-volume reliability: bounded API calls, per-file diff excerpts, avoid downloading huge logs or game archives in chat. | Audit scripts capped by calls/output, no raw binary dumps, summary-only CI logs; do not attribute product-side errors to game server. | WORKFLOW SAFETY |

## P0/P1 — public GitHub Issues to reproduce, evaluate and track

| ID | Public evidence | Impact and acceptance target | Status in source (not in YT Ultimate) |
| --- | --- | --- | --- |
| GH-001 | [YT #538](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/538) | In-game co-op menu keyboard: typing a friend's name, Enter, Invite, clipboard, mouse/controller focus. Test fresh 1.4.0 Windows profile and Russian keyboard. | OPEN 2026-11-08 |
| GH-002 | [YT #532](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/532) | `Failed to resolve Bloodborne server status` even after successful auth; CUSA00900/Linux, different `ss.info` fields, hook failures. Test EU/US + Linux/Windows without changing production routing. | OPEN |
| GH-003 | [YT #508](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/508) | Messenger purchases should not exhaust another player's shop stock. Test unique/shop flags with 2–5 players. | OPEN |
| GH-004 | [YT #428](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/428) and [YT merged #533](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/533) | Russian Windows firewall check `NoneType.lower`, PLAY / Start server spinning forever. Upstream #533 addresses console decoding and unexpected exception feedback; confirm exact base, no infinite spinner in current 1.4.0. | ISSUE OPEN, PR MERGED; REGRESSION TEST REQUIRED |
| GH-005 | [YT #542](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/542) | RTX 3080 `WriteInvalid at 0x0` GPU device lost after load, claimant cites Jgamrot #157/#209. Review Vulkan buffer binding/format changes, reproduce on target GPU; do **not** copy unverified upstream patch. | OPEN |
| GH-006 | [visy #4](https://github.com/visy/bloodborne_pc_windows_port/issues/4) | Guest interaction/render failures, party wipe/DBNO, host death world reset. Issue includes multiple distinct symptoms; create separate deterministic regression fixtures for each. | CLOSED IN VISY; YT PARITY UNKNOWN |
| GH-007 | [visy #28](https://github.com/visy/bloodborne_pc_windows_port/issues/28) | Guest lights DLC lamp before host: travel list flag becomes set while lamp object remains unlit, causing persistent softlock. Validate both relevant flag families and migration/rollback. | CLOSED IN VISY; YT PARITY UNKNOWN |
| GH-008 | [visy #35](https://github.com/visy/bloodborne_pc_windows_port/issues/35) | After respawn FPS pacing occasionally locks ~64 FPS until target toggled. Benchmark frame-time p50/p95/p99 and watch frame limiter state. | OPEN |
| GH-009 | [Nightwatch #6](https://github.com/vladtepes22/NightwatchCoop/issues/6) | Visible guest *not registered as an entity* with boss AI/collision, often DLC/boss after death. Pair with USR-001 but keep distinct from invisibility symptom. | CLOSED IN NIGHTWATCH; YT PARITY UNKNOWN |
| GH-010 | [Nightwatch #9](https://github.com/vladtepes22/NightwatchCoop/issues/9) | Enemy/NPC state diverges; enemies in area die without player action, unexpected echo awards. Test deterministic host-authoritative NPC health and rejoin. | CLOSED IN NIGHTWATCH; YT PARITY UNKNOWN |
| GH-011 | [Nightwatch #1](https://github.com/vladtepes22/NightwatchCoop/issues/1) | Per-player unique start weapon, Old Hunter Bell and Iosefka vial rewards. | CLOSED IN NIGHTWATCH; YT PARITY UNKNOWN |
| GH-012 | [deadinside #422](https://github.com/deadinside28/bloodborne_pc/issues/422) | Windows ↔ Steam Deck BBSC join black screen and 33 s timeout despite peer connection; model multi-stage NetSync, wait/load, wrong-status timeout. | OPEN |
| GH-013 | [deadinside #441](https://github.com/deadinside28/bloodborne_pc/issues/441) / [PR #442](https://github.com/deadinside28/bloodborne_pc/pull/442) | Vulkan sampler destruction before submit completion; test lifetime with real queue semantics; no unbenchmarked renderer import. | OPEN ISSUE / UNMERGED PR |
| GH-014 | [deadinside #439](https://github.com/deadinside28/bloodborne_pc/issues/439) / [PR #440](https://github.com/deadinside28/bloodborne_pc/pull/440) | Submission count reaches zero with work queued, resulting in false GPU idle. Race-specific C++ regression and real GPU testing. | OPEN ISSUE / UNMERGED PR |
| GH-015 | [shadNet #43](https://github.com/shadps4-emu/shadNet/issues/43) | STUN UDP 31314 unresponsive on an external public server; successful TCP login ≠ reachable P2P. Validate NAT diagnostics and relay fallback **for our selected service** only. | CLOSED NOT_PLANNED IN SHADNET |
| GH-016 | [CLSAMG22/BBSC #35](https://github.com/CLSAMG22/BBSC/issues/35) | Snatcher kidnapping → Hypogean Gaol permanent black screen/control softlock. Match cutscene/event and save/transition state with clean 1.09. | SOURCE ISSUE TO TRIAGE |
| GH-017 | [CLSAMG22/BBSC #40](https://github.com/CLSAMG22/BBSC/issues/40) | Hunter's Dream softlock; isolate renderer vs event/party vs launcher version. | SOURCE ISSUE TO TRIAGE |
| GH-018 | [CLSAMG22/BBSC #44](https://github.com/CLSAMG22/BBSC/issues/44) | Guest spectator state persists after boss wipe; verify return from spectating on host reload, compare [deadinside #418](https://github.com/deadinside28/bloodborne_pc/pull/418). | SOURCE ISSUE TO TRIAGE |
| GH-019 | [CLSAMG22/BBSC #8](https://github.com/CLSAMG22/BBSC/issues/8) | Game closes after friend joins password lobby; investigate crash dumps, timing and net state not a generic networking workaround. | SOURCE ISSUE TO TRIAGE |
| GH-020 | [CLSAMG22/BBSC #5](https://github.com/CLSAMG22/BBSC/issues/5) | PLAY ignores selected local server. Verify launcher environment/endpoint before connecting. | SOURCE ISSUE TO TRIAGE |
| GH-021 | [droogie/bbhost #220](https://github.com/droogie/bbhost/issues/220) / [#224](https://github.com/droogie/bbhost/issues/224) | GPU hang on GTX 1660 SUPER, DLSS/FSR switching: benchmark on independent original BBHost, do not assume 1.4.0 integration shares Vulkan code. | SOURCE ISSUES TO TRIAGE |
| GH-022 | [Jgamrot/yharnam-pc #231](https://github.com/Jgamrot/yharnam-pc/issues/231) | Three-player online failure in another Windows launcher/BBSC distribution; check exact version, not interchangeably with official YT. | SOURCE ISSUE TO TRIAGE |

## Mods / UX user explicitly requested

- MOAL (talk scripts and ~15 event files): compatible with some PC ports but
  co-op menu is reportedly unavailable to mod author; risk for YT events,
  boss rematches, lamps and two-invader mods. Keep opt-in until source-safe
  event merge and five-player saves are tested.
- Doll Rebirth: two required components (mod files + XML). Check respec
  currency and re-level HP/stamina, online world/progression, rollback.
- Jump on L3 / enhanced variant: replaces `c0000.hks`, conflicts with
  any other replacement of that file. Validate climbing, trick transforms,
  interactions, keyboard remapping and five-player input.
- Game version 1.09 `Bloodborne.xml`: private 2026-11-01 audit observed
  incompatible enabled-patch overlaps at `0x026C4FD7`, `0x02C0137D`,
  `0x025629F0` among performance, SSR and uncapped-FPS patches.
  Those addresses are **not revalidated against private EBOOT here**;
  never auto-enable all checked XML patches.
- Other requested QoL: manual NG+, lamp features, respec, return to desktop,
  settings for AA/DoF/SSR, corpses, LOD, FPS, graphics and effects.
  Track as feature requests, with mod interoperability and no regression
  of quests or game-world persistence.

## 2026-11-08 original screenshot archive and sanitized public issues

Seven original image files were archived in the non-shared Drive account
`gungrain@gmail.com`:
`Bloodborne — Seamless Hunt — HANDOFF / 05-TESTS-LOGS /
2026-11-08 — PRIVATE Discord Bug Screenshots`.
They remain private and **are not mirrored into public GitHub**. The private
index `00-PRIVATE-README-and-SHA256.md` records the first six files' SHA-256 and
technical categories; `07-private-technical-intake.md` records image 07 with
SHA-256 `6d699a608fbf643d3a992f75696117052e0b9df40ce72ff2c8f4f21c9d11695a`. These are historical version-dependent bug reports,
**not** reproducible evidence that current 1.4.0 has them.

The source-aware, release-gated acceptance criteria are tracked in:

| Public sanitized issue | Category | Screenshot evidence, privately stored |
| --- | --- | --- |
| [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) | P0 world progression, lamp, door, quest and persistent save | 01, 02, 07 |
| [#23](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/23) | P0 enemy/actor, NPC, loot, party/boss state synchronization | 01, 02 |
| [#24](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/24) | P0 account sign-in and certificate trust diagnostics | 03, 04 |
| [#25](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/25) | P1 missing floor/geometry, VRAM and FPS decay, UI latency | 01, 02, 04, 06, 07 |
| [#26](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/26) | P1 leave-lobby UX, offline developer tooling, anti-cheat/mod false positives | 01, 02, 05 |

**Screenshot 07, operational release rule:** the new screenshot is a unique
private **file**, but duplicates the core gameplay/performance complaints
already in #22/#25. Its additional concern is unauthorized or prematurely
approved server releases. The neutral engineering control is recorded in
[server roadmap #3](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/3)
and [runtime evaluation #9](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/9):
explicit owner-approved deployment, protected production credentials, isolated
staging, immutable client/server protocol manifest, five-hunter sign-off and
rollback. The screenshot is **not** evidence of personal wrongdoing, and no
names or private discussion excerpts belong in GitHub.

**TLS wording correction:** the historical launcher message `certificate:
not sent` means the **account request was not sent** because certificate
verification blocked it; this is not evidence that the server failed to send
a certificate at all. Distinguish unavailable roots, invalid chain,
hostname mismatch, proxy interception and missing server certificate.
See source `bbport_auth._tls_error` and the tested Windows truststore.
[Experimental UI clarification PR #27](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/27)
does not disable TLS verification.

Any later screenshot must be deduplicated against **private SHA-256 evidence
and technical symptoms** before upload and public Issue creation. If its
binary attachment is unavailable, leave it **pending**, never falsely claim
a successful Drive upload. Avoid raw Discord or user names in public code.

## 2026-11-08 source spot-check: two original screenshot regressions

The current integrated 1.4.0 candidate was inspected **at exact blob SHAs**
without any game or private screenshot bytes:

- `emulator/src/core/bloodborne_boards.cpp`, SHA
  `3318b6e3c330f7bef7cca90d546f56c7a41fa783`, line ~821:
  `FinishWaitingJoins` computes one `here` value with
  `SomeoneElseStands(view.board.members, view.member, PlayingMap())`
  **before** looping over all waiting tasks, and passes the same
  `here` to every `MemberDataWait::Tick`. This confirms the shared
  map-presence condition described in the private screenshot handoff.
  It does **not** establish which task's actor fails, and is **not yet
  proof of causation**. Before changing it, prove how each remote
  `member_id` correlates to its vitals board identity; otherwise a
  speculative fix may break multi-map joining.
- `emulator/src/core/bloodborne_join.cpp`, SHA
  `9283bb49bb6875f5e5616bd8928a7541dfbbb03a`:
  `RebuildJoinTask` saves waiting tasks by member identity, and
  `RecreateRemotePlayers` matches the session member via the engine
  equality function. This logic must remain identity-specific in
  regression tests with 3 and 5 members.
- `emulator/src/core/bloodborne_party.cpp`, SHA
  `54637fea5b6f15d8410f68b1f8ba70d2344127dd`,
  contains `NameUnnamedGuestRole`; `bloodborne_party_rules.cpp`,
  SHA `5511b8310afe77c20a9a182f43f707bf6e1d9ee2`,
  invokes it in `PolishMultiplayerUi` when the writable role table
  is present. **Do not add a duplicate `?ActionEventInfo?` fix.**
  Test exact Windows bundled code, table access and reload behavior.

Next correctness gate for USR-001 and USR-002: actual two-/three-/five-game
repro with per-member identity, map and join task state; a source-level
hypothesis cannot be marked fixed from CI alone.

## Triage procedure for all new Issues / discussions / comments

1. Collect repository + immutable commit/branch + issue URL, state and last
   update, affected versions and screenshots/log *descriptions*. Search
   **open and closed**, merged and unmerged PRs, fork issue trackers,
   discussions, commit comments and release notes. Read project/handoff
   reports too. Stop if access/permissions are missing.
2. De-duplicate by actual symptom + build + source path, not issue title.
   Link similar bugs across Nightwatch, CLS, original droogie/BBHost,
   visy, deadinside, Supermedo, shadPS4 and the selected YT fork. Do not
   assume the same root cause or that an upstream fix is already present.
3. Reproduce with **private** game 1.09, correct region and 2→3→5 hunters;
   separate solo vs co-op, host vs guest, Linux vs Windows, fresh vs copied
   saves, Hunter's Dream, DLC, chalices, save reload, network jitter.
4. Write synthetic/unit regression first, and then a real Windows/game rig
   scenario; record actual bad/good log markers, packet version, commit SHA,
   GPU/OS/driver and crash/frametime counters.
5. Backport only proven source/behaviour, respecting licensing and precise
   runtime/protocol compatibility. Update this ledger with explicit **NOT
   REPRODUCED / REPRODUCED / FIX CANDIDATE / TEST PASSED / PLAYTEST PASSED**
   states. A closed issue or green source CI alone does **not** qualify.
6. Never put private game binaries, player screenshots, Discord logs,
   credentials or live server databases into a public GitHub issue or PR.

The machine-readable GitHub Issues index will come from a bounded, read-only
GitHub REST inventory (not a claim to inspect literally all of GitHub). Each
search page and repo's issue/PR pages must expose truncation and source dates.
