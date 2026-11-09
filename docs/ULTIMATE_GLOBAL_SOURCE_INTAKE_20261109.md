# Ultimate global research intake: two missions, traceable evidence, zero premature imports

**Checkpoint: 2026-11-09.** This is a **systematic discovery baseline**, not a claim to have inspected every public repository or to have implemented all candidate features. Keep the existing B01–B10 source fixes and source-level tests. Do not rebuild or release the launcher/game/server for each individual patch.

## What was actually checked

A first-page metadata search of **20 different GitHub repository discovery queries** collected **301 search hits corresponding to 241 distinct public candidate repositories** (153 distinct in the direct Bloodborne/PC/coop/mod family, 89 in adjacent shadNet/Souls/DS3 tooling; one overlap). The two inspectable snapshots live at:

- `tools/ultimate/source_radar_20261109_primary.json`
- `tools/ultimate/source_radar_20261109_adjacent.json`

The snapshots retain the exact search terms and all returned repository names, default branches, archive flags and query matches; **they do not contain executable source or game files**. GitHub results were limited to the first 35 per query: these are **candidates**, not exhaustive coverage or 241 approved improvements. Forks may repeat each other's code; search relevance is not evidence of technical merit.

Ten primary ecosystem repositories were separately sampled for **branches and recent PRs**: Amanises/Yharnam Together, original droogie/BBHost, deadinside28/BBPort, Supermedo, visy, LanternEngine/Awaken, NightwatchCoop, Mrsuss60, shadPS4 and CLSAMG22/BBSC. Their branch search was **one page each**, not full enumeration. Further work should paginate fork graphs, branches, PRs and commits from this seed set, tracking resume cursors externally if needed.

A distinct reviewed **21-item candidate list**, with original PR links, scope, compatibility gates and explicit status (already included, needs diff review, design-only, risky, runtime benchmark, not cherry-pickable), is retained as `tools/ultimate/global_intake_priorities_20261109.json`. Intake statuses do not establish that a patch actually works in our 1.4.0 build.

## Equal missions, fixed meaning

**Mission A, playable Ultimate:** choose the best runtime from measured evidence, not by brand. Candidate paths are Yharnam Together/BBPort 1.4.0, independent original droogie/BBHost, an isolated Nightwatch/visy network design or legally compatible hybrids. Preserve YT's gameplay and co-op behavior if migrating; never assume BBHost, BBSC, visy, shadNet and YT speak the same wire protocol. All five player roles, DBNO, hot join, per-slot/owner world/rewards, matchmaking, friends, invitations, host toggles, PvP/invasions, transitions and saves need exact C++ and game tests.

**Mission B, actually native Windows Bloodborne.exe:** independently continue private reverse engineering, DS3 research and Win64 AOT/ABI conversion. Final **must not load or execute original PS4 ELF / eboot.bin at runtime**, cannot be accomplished merely by packaging BBPort/BBHost or renaming an EXE. Previously indexed ELF unwind entries and 7,702 selected native leaf-function translations are evidence of progress on a limited subset, not a native playable port. User-owned game assets and Dark Souls III are private build-time research inputs, not distributable repository content.

Canonical project charter: `ProhorovIlja/bloodborne_pc_windows_port/docs/SEAMLESS_HUNT_TWO_MISSIONS_MASTER_SPEC.md`. Google Drive READ FIRST document, historical handoffs and a 2026-11-01 co-op/mod incompatibility report were read through the authorized gungrain account; **no private Drive IDs, XML patches, player files or Discord logs were included in these public snapshots**.

## High-value discovery, not unreviewed copying

| Class | Concrete sources | Next validation |
|---|---|---|
| Runtime architecture | [droogie/bbhost](https://github.com/droogie/bbhost), [deadinside28/bloodborne_pc](https://github.com/deadinside28/bloodborne_pc), [visy/bloodborne_pc_windows_port](https://github.com/visy/bloodborne_pc_windows_port), [Supermedo/bloodborne_pc](https://github.com/Supermedo/bloodborne_pc) | same 1.09/scene/driver; p50/p95/p99 frametime, 1% lows, RAM/VRAM, shader warmup, online uptime and safe save isolation |
| Co-op and network | [Amanises/YT](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together), [CLSAMG22/BBSC](https://github.com/CLSAMG22/BBSC), [NightwatchCoop](https://github.com/vladtepes22/NightwatchCoop), [LanternEngine](https://github.com/Awakenchan/LanternEngine), [Wozzardman/shadnet-p2p](https://github.com/Wozzardman/shadnet-p2p) | client identity, authenticated direct UDP + safe relay fallback, NAT/STUN, consistency, remote actor lifecycle, 5-player traffic |
| New gameplay/bugs | [visy PR #13 hostile NPCs](https://github.com/visy/bloodborne_pc_windows_port/pull/13), [CLS #46 boss items](https://github.com/CLSAMG22/BBSC/pull/46), [CLS #47 stranded dead guests](https://github.com/CLSAMG22/BBSC/pull/47), [CLS #48 loader race](https://github.com/CLSAMG22/BBSC/pull/48) | compare B03/B04 rewards & B02/B05 world state; reproduce against 1.4.0 and game 1.09 before transplant |
| Network diagnostics | [visy #16 CGNAT detection](https://github.com/visy/bloodborne_pc_windows_port/pull/16), [LanternEngine #89 off-main signaling](https://github.com/Awakenchan/LanternEngine/pull/89), [droogie #217 signaling lifecycle](https://github.com/droogie/bbhost/pull/217) | robust WAN/CGNAT/double-NAT cases; server auth and packets, RTT p95/p99, no handshake/callback ABI breaks |
| Renderer | [deadinside #440 GPU submission](https://github.com/deadinside28/bloodborne_pc/pull/440), [#442 sampler lifetime](https://github.com/deadinside28/bloodborne_pc/pull/442), [shadPS4 #5280 buffer sync](https://github.com/shadps4-emu/shadPS4/pull/5280), [YT #543 null V#](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/543) | YT #543 already included in B01; do not duplicate; source API alignment, CPU stress then GPU hardware vendor tests |
| Rendering/QoL | [droogie #218 upscalers](https://github.com/droogie/bbhost/pull/218), [Nightwatch #10 HDR](https://github.com/vladtepes22/NightwatchCoop/pull/10), [Mrsuss60](https://github.com/Mrsuss60/bloodborne_pc_windows_port) | not all features can run simultaneously: color pipeline, driver versions, latency, UI settings and power budget |
| Launcher | [Supermedo #169 RecompLauncher](https://github.com/Supermedo/bloodborne_pc/pull/169), [YT #539 TLS truststore](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/539), [BB Launcher](https://github.com/rainmakerv3/BB_Launcher) | deduplicate existing #13/#27 TLS and #30 frozen launcher; signed update/rollback, localization, installation and save backup |
| Mods and Souls-family | [Smithbox](https://github.com/vawser/Smithbox), [DSLuaDecompiler](https://github.com/katalash/DSLuaDecompiler), Google Drive private Bloodborne 1.09/DS3/mod inventories | conflict by same file, event script, patch bytes and save schema; enable optional profiles only after test; no automatic mass-enable |
| Native port | [bloodborne-native](https://github.com/bloodborne-native/bloodborne-runtime), our [native PR #84](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/84), original Windows native loader research | clarify hosted-ELF vs true no-ELF Windows game; every function/codegen/ABI/asset subsystem must pass independent equivalence and gameplay |

## Non-negotiable promotion gates

1. **Source lineage:** canonical project, license and notices, author, exact commit, branch, PR state, dependencies, conflicts, C++/ABI version and deterministic source diff. A PR with 2,005 touched files (Nightwatch #10) cannot be grafted as if it were a focused HDR fix; a whole-release BBHost GPU PR cannot be adopted as a tiny workaround.
2. **Correctness:** compile the actual production functions, negative/failure tests, synchronization tests, memory safety and fuzzing for network parsers, Windows/Linux filesystem behavior; compare before/after against precise baseline. Do not make unverified source tests equal to real game results.
3. **Gameplay:** private 1.09 2/3/5-hunter playtest; guest/host world ownership, DBNO, party wipe/leave, hot join, Hunter's Dream ghost/HP, boss AI/rewards, NPC hostility, invasions/duels, late join, Chalice/DLC, save slot switch, crash/restart/rollback. Test host-controlled invasion settings, the intended total of five participants split across co-op/invaders, matchmaking/filters and friends.
4. **Performance and reliability:** equal GPU, driver, CPU, scene, resolution and cache state; median, p95, p99 frame/RTT, packet-loss and bandwidth, VRAM/RAM, load times, stutter, crash rate, 8 GB/4 GB memory, host/guest server load, NAT and relay percentages; reject a flashy patch that regresses latency or playability.
5. **Privacy/security:** actual TLS verification; authenticated P2P handshakes, sane server-trusted game state, rate limits, no account/game-secret exposure, signed/or hash-pinned packages, private map/profile opt-in, live-site rollback and save backup.
6. **Release:** first integrate all accepted fixes into a **single** client/runtime/launcher/server set, fix Windows build #31 and reconcile its newer CI diagnostics, then compile once at a gate with version/PE/DLL closures and real gaming. CI or a three-EXE file existence check is not a playable Ultimate.
7. **Native B:** independently validate real Win64 game code, original-ELF-free executable startup, all systems and game playthrough. Success on Mission A does not satisfy Mission B.

## Outstanding work, not implied completed

- Exhaustive global GitHub coverage is infeasible: query result caps, new/hidden/private repos, deleted branches and ongoing changes mean coverage is open-ended. This catalog is a **reproducible, expanding radar**, not a finish line.
- The 241 public results are metadata-only candidates. The 21 prioritized PR entries were reviewed at metadata/changed-file level; none is asserted integrated by this registry except YT #543 already source-imported as B01. No automatic merge.
- Latest source branch is B10 Draft #42; real B06–B09 Windows/Linux C++ save helper fixtures passed, but real private savedata and any full playable build are unverified. Windows #31 initial Ninja remains red, despite incremental linker success producing all three EXE paths.
- Drive private `CUSA03173`, `Dark Souls III`, MOAL and Jump mod folders are present in the correct account; no private proprietary bytes were fetched or published for B11. A separate mod-compatibility note documents observed XML collisions and a need for launcher conflict checks. Never enable a potentially conflicting mod by default.
- **Next source-level focus after B11:** compare YT 1.4.0 against the exact CLS #48 BBPort loader race, #47 dead-guest grey screen, visy #13 hostile NPC team corrections and B03/B04 deferred rewards, with an owned failing regression before moving code.

**Policy:** Fornex stays untouched, no auto publication, no false “all fixed”, no huge logs/dumps in chat. Update source snapshots/decision states as new evidence arrives and only perform full integrated binaries at measured milestones.

## Initial exact source-location review: no blind transplant

On the B11 head the targeted YT 1.4.0 source paths were queried directly through GitHub. The independent [CLS #48](https://github.com/CLSAMG22/BBSC/pull/48) diff modifies `emulator/mod/bbsc_mod.cpp`, but that file is **absent** from this YT branch. It therefore cannot be adopted as a direct two-line loader fix. First identify the relevant YT/BBPort loader initialization and test its image-patch ordering, including whether the CLS failure mode applies.

Similarly, [CLS #47](https://github.com/CLSAMG22/BBSC/pull/47) changes `TickBbscStrandedGuest` and `ReleaseBbscLeaveLocks` in the CLS `bloodborne_re.cpp`, but those functions are **absent** from our current `emulator/src/core/bloodborne_re.cpp`. The underlying dead-guest grey-screen scenario is a real *candidate test*, not a drop-in source patch. Investigate our own YT/DBNO end-session state and leave locks.

The merged [visy #13](https://github.com/visy/bloodborne_pc_windows_port/pull/13) adds hostile NPC team events to `gpu/shim/party/party_npcfight_rules.h`, also **absent** from our YT source tree. Translate the affected 1.09 event/team semantics only after locating YT's own world/event patcher, and prove with host and guest scripted fixtures.

These three rows are now designated **candidate_design_review**, not `candidate_diff_review`. This is exactly why the best-of process has a **source-location gate** and does not import entire PRs on title similarity.
