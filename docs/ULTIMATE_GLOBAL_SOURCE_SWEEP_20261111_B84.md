# Ultimate B84 — cross-ecosystem source census and evidence register

Date: 2026-11-11. Scope: **existing playable Yharnam Together Ultimate client, launcher, server and multiplayer**. Its custom co-op system replaces original BBSC Bell matchmaking. This is a source-search checkpoint, NOT a claim that the entire internet or GitHub has been exhaustively read or that every candidate is now in the build.

## Reproducible search coverage (GitHub connector, 2026-11-11)

| Query/scope | Observed coverage | Coverage boundary |
| --- | --- | --- |
| Official `Amanises-Yharnam-Together/BBSC-Yharnam-Together` branches | **586 branch names, 7 cursor pages**, final cursor empty | Full API branch-name enumeration at query time; NOT inspection of all 586 branch code diffs |
| Own playable `ProhorovIlja/BBSC-Yharnam-Together` | **84 branch names**, including cumulative Ultimate B70–B84 chain, current own Draft PRs sampled | PR #151 B84 is active; older branches can differ; no automatic merge |
| Own Windows-port `ProhorovIlja/bloodborne_pc_windows_port` | **94 branch names**, including QoS, launch, NAT, auth, port, shader, native recompiler work | Port remains separate; candidate logic only with ABI/serialization evidence |
| Public repo search `Yharnam Together` | **9 repo matches**, official and several forks | GitHub repo search is term-indexed, not a complete network of forks |
| Public repo search `Bloodborne bbhost` | **63 repo matches**, including `droogie/bbhost` and many forks | Default-name search; more forks can exist |
| Public repo search `bloodborne coop` | **11 repo matches**; Nightwatch, Nucleus handler, mark3317/bbgl | Search is not exhaustive |
| Public repo search `nightwatch bloodborne` | **7 repo matches** | Search is not exhaustive |
| Public repo search `bloodborne pc port` | First **100** results inspected; search may extend beyond page one | Explicitly incomplete |
| Upstream YT pull requests | **50** recent PR metadata entries sampled, and selected PR bodies read | Older PRs and per-file diffs not all read |
| Droogie BBHost pull requests | **50** recent PR metadata entries sampled; selected #238/#239 descriptions read | Branch/ABI and engine differ |
| Visy port pull requests | **20** PR metadata entries returned | Independent protocol, port and engine |
| Own playable issues | **43** currently open issue records enumerated, including all user-reported P0 clusters below | Issue status may change |
| Upstream YT issues | **5** currently open issue records returned | Confirm issue quality before adopting solutions |

Representative YT topic branches from the complete name inventory: `game-link-resend-backoff`, `world-snapshot`, `world-sync-plan`, `launcher-upnp`, `launcher-connect-help`, `map-live-3d`, `save-backups`, `save-restore`, `online-unlocked-fps`, `boss-hp-after-wipe`, `team-worlds`, `fix/ng-plus-team-world`. Their presence is NOT evidence that the branches should be merged, or that branch implementations are unreleased improvements. Need compare code and ancestry.

Specific forks identified for source-level comparison:
- [Official YT](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together), [oat018](https://github.com/oat018/BBSC-Yharnam-Together), [edisnord](https://github.com/edisnord/BBSC-Yharnam-Together), [Tutuzaooo](https://github.com/Tutuzaooo/BBSC-Yharnam-Together), [sousalucasc](https://github.com/sousalucasc/BBSC-Yharnam-Together), [nmoya Linux](https://github.com/nmoya/BBSC-Yharnam-Together-linux).
- [Droogie BBHost](https://github.com/droogie/bbhost), [visy Windows port](https://github.com/visy/bloodborne_pc_windows_port), [Nightwatch](https://github.com/vladtepes22/NightwatchCoop), [Mark3317 BBGL](https://github.com/mark3317/bbgl), [Supermedo port](https://github.com/Supermedo/bloodborne_pc), [shadPS4](https://github.com/shadps4-emu/shadPS4), [eFMann shader/upscaler fork](https://github.com/eFMann/shadPS4-Bloodborne-DLSS-FSR).
- External current public sources checked: [YT v1.4.0 release](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/releases/tag/v1.4.0), [BBPort updates](https://bbport.org/updates), [Supermedo 1.9.8.x release pages](https://github.com/Supermedo/bloodborne_pc/releases), [visy credited patches](https://github.com/visy/bloodborne_pc_windows_port/blob/master/docs/PATCHES_FOR_FORKS.md), [BloodbornePC Nightwatch feedback thread](https://www.reddit.com/r/BloodbornePC/comments/1xeolsc/bloodborne_seamless_coop_on_pc_with_nightwatch/). Published performance claims and single-user reports are NOT our verified benchmarks.

## Google Drive provenance and screenshot inventory

Two connected Google Drive accounts were searched read-only for project histories, BBSC, Yharnam, screenshots and port compatibility: **gungrain@gmail.com** and the second connected project account. Writes performed ONLY on the explicitly requested **gungrain** account.

- Canonical gungrain `01-HISTORY-MD` (private Drive folder): **30** previous archive items before this turn, and user's current 2026-11-11 source archive uploaded and read back (private Drive).
- Private Discord bug screenshots folder contains **7 PNGs** plus technical intake and SHA256/readme manifests. Captured themes: world progress, TLS/SSL, anti-cheat, missing textures and server governance; keep private and only cite titles in public.
- Another Screenshots folder contains **4 PNGs** named 1–4. Their correspondence to particular historical user screenshots was NOT established. Other folders named screenshots were found, but some are unrelated source code/marketing imagery.
- Connected second Drive contains a separate Bloodborne HANDOFF, preserved older chat archives and multiple native Google Docs, including launcher, compatibility, website, upload-order, and latency references.
- [Canonical requirements](ULTIMATE_CROSS_CHAT_REQUIREMENTS_MASTER.md), [historical source manifest](ULTIMATE_CROSS_CHAT_SOURCE_MANIFEST.md), [bug backlog](ULTIMATE_BUG_ISSUE_BACKLOG.md), [B83 source compatibility](ULTIMATE_BATCH_83.md), and gungrain Ultimate Doc B54+ (private Drive) retain the context. **Do not claim every image from every chat is uploaded** without per-message image/hash mapping.

## Reviewed external candidate matrix: no first-hit transplant

| Candidate | Actual evidence/source | Disposition for Ultimate | Gate |
| --- | --- | --- | --- |
| Network frame wire-size invariant | Inherited from [upstream GameLink](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/blob/main/server/coop/game_link.h): fixed 16-byte sender estimate vs 0–255 variable bytes; real local code reviewed | **Implemented B84** in shared YT client/server; [Draft #151](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/151) | [CI 3/3 passed](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/43010114675) and B82/B83 compatibility; live 2–5 hunter network benchmark remains |
| Phantom key items after crash | [YT PR #548](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/548): rig-verified persistent per-slot debts for badges/tools, but own Ultimate ledger is intentionally offline without stable savedata acknowledgment | **P0 #137 open**, not covered by B84; earlier B68–B81 partial protection is not equivalent to verified file-save transaction | Character identity, crash-safe on-disk grant/ACK, avoiding duplicates and save corruption |
| Guest pickups survive crash/rejoin | [YT PR #566](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/566) | Compare implementation to B64/B80 and host-only world | Real game rig, save provenance, replay |
| Party settings live in team screen | [YT draft #577](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/577): source author says new in-game semantics conflict with older launcher numeric settings | Candidate, not integrated | Schema migration, launcher UI consistency, tests |
| Friendly fire | [YT draft #575](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/575) | Candidate, off by default | PvP policy, friend-only private team, invader interactions |
| Enemy scaling, GPU frame pacing | [YT #569](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/569), [#549](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/549) | Benchmark candidates | Avoid double scaling, no forced graphics overrides without GPU test |
| Public server auth, signing and diagnostics | [YT #539](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/539), [#559](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/559), own [P0 #24](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/24) | Existing/partial; verify actual behavior | Windows trust store, DNS/TLS, server error messages, Fornex **read-only** |
| Draw prep / memory pressure / save safety | [droogie/bbhost #239](https://github.com/droogie/bbhost/pull/239), [#238](https://github.com/droogie/bbhost/pull/238), [#233](https://github.com/droogie/bbhost/pull/233) | Source review and isolated portable algorithms, not binary/plugin transplant | Different Vulkan/graphics ABI; license, perf A/B and platform gating |
| Visy LAN/VPN and NAT reporting | [visy #26](https://github.com/visy/bloodborne_pc_windows_port/pull/26), [#7](https://github.com/visy/bloodborne_pc_windows_port/pull/7), [#16](https://github.com/visy/bloodborne_pc_windows_port/pull/16) | Alternative UX/protocol design for own [P0 #93](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/93); not a drop-in replacement for server-owned team world | Security, enrollment, private LAN trust, fallback, coexistence |
| Mod event parser accepts zero instructions | [Supermedo 1.9.8.1](https://github.com/Supermedo/bloodborne_pc/releases) notes malformed/empty mod events accepted for co-op patching | Candidate for event patcher compatibility; no change made | Verify current YT parser and license, test zero instruction metadata |
| Community reports of Nightwatch Chalice/lag | [Nightwatch](https://github.com/vladtepes22/NightwatchCoop) and [community thread](https://www.reddit.com/r/BloodbornePC/comments/1xeolsc/bloodborne_seamless_coop_on_pc_with_nightwatch/) | Acceptance scenarios / UX ideas only | Independent multiplayer implementation and anecdotal reports |

## Mandatory next gates (not completed)

1. Reconcile all prior screenshot references and text notes to exact Drive file IDs/hash/message source. Missing/unknown items stay **unverified**.
2. Compare 586 branch tip diffs and recent fork ancestry by thematic clusters, not by branch names; triage against actual Ultimate code to prevent duplicate features.
3. Prioritize P0: #137 guest reward durability, #35 delayed boss/NPC awards, #22/#23 world/enemy/NPC progression, #24 TLS, #63/#79 NPC, #73 chest; keep gaming save safety stronger than convenience features.
4. Parallel launcher and QoL targets: one-click VPN/LAN, team/private/global chat toggles, optional map player visibility, BL/build display, co-op/quick match/invasions, settings migration, launcher startup/exit performance and compatibility (references in own issues #93, #103, #95, #77, #84).
5. For every adopted source: precise upstream commit + file diff + license and ABI review + isolated tests + 2/3/5 hunter acceptance, packet loss/jitter and server-load measurements. Only build downloadable client/launcher/server after **integration** passes; no real player saves/live Fornex alteration.

Search limitations: GitHub code search mainly indexes default branches; raw public search is indexed and ranked, not exhaustive; Drive keyword search may omit private/unindexed folders; the internet changes continually. The **recorded counts and links** make this audit inspectable rather than asserting universal coverage.
