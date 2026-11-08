# Ultimate Playable: ecosystem source audit

> 2026-11-08. Working register for a **Windows playable fork**. This is not the
> future eboot-free native AOT port. The current live Fornex server remains
> untouched. This register is **not an exhaustive index of GitHub**; expand it by
> searching relevant code, forks, branches, PRs and dependency history before
> selecting each component.

## No premature runtime choice

The **original [droogie/bbhost](https://github.com/droogie/bbhost)** is a complete
and independent *candidate foundation*, not merely a code donor and **not**
identical to CLS's experimental bbhost-packaged Yharnam Together release.
The other primary candidate is **[deadinside28/bloodborne_pc](https://github.com/deadinside28/bloodborne_pc)**
and its Windows bbport descendants. **No winner has been selected.**

| Project | Track | Checked branches and concrete PR evidence | Integration boundary |
| --- | --- | --- | --- |
| [droogie/bbhost](https://github.com/droogie/bbhost) | Independent competing runtime (CPU, HLE, Vulkan, private online, P2P/NAT, mods, plugins) | `decomp/*`, `fix/*`; merged [#201](https://github.com/droogie/bbhost/pull/201) (CPU + bloodstains/online timing), merged [#204](https://github.com/droogie/bbhost/pull/204) (CPU/memory), open [#223](https://github.com/droogie/bbhost/pull/223) and draft [#218](https://github.com/droogie/bbhost/pull/218) (graphics). | Compare **entire engine** against bbport on same scenes, equipment and five-hunter network workload; don't directly replace YT's encrypted wire protocol with THD server. |
| [deadinside28/bloodborne_pc](https://github.com/deadinside28/bloodborne_pc) | Original bbport alternative runtime | `master`, `testing`; open [#440](https://github.com/deadinside28/bloodborne_pc/pull/440) (submission queue race) and [#442](https://github.com/deadinside28/bloodborne_pc/pull/442) (sampler lifetime). | Benchmark Vulkan/render thread fixes only with same GPU, version and tests. |
| [Supermedo/bloodborne_pc](https://github.com/Supermedo/bloodborne_pc) | Windows port, graphical and timing fixes | `windows`, `perf-latency`, `freeze-fixes`, `pr-perf-locks`; open [#155](https://github.com/Supermedo/bloodborne_pc/pull/155) (crashes), [#156](https://github.com/Supermedo/bloodborne_pc/pull/156) (frame timing). | Compare exact changes to current imported bbport; verify high-FPS co-op timing before adopting. |
| [Mrsuss60/bloodborne_pc_windows_port](https://github.com/Mrsuss60/bloodborne_pc_windows_port) | Independent Windows port and input/graphics changes | `master`; merged [#170](https://github.com/Mrsuss60/bloodborne_pc_windows_port/pull/170) (mouse/menu) and [#190](https://github.com/Mrsuss60/bloodborne_pc_windows_port/pull/190) (UI stencil). | Check input accuracy, Vulkan UI and licence; **not proven** to be the same project as the user's name “Massus”. |
| [visy/bloodborne_pc_windows_port](https://github.com/visy/bloodborne_pc_windows_port) | Party co-op, game travel, GPU presentation and UX | `master`, `agent/parfin3`; merged [#7](https://github.com/visy/bloodborne_pc_windows_port/pull/7) (VPN mapping), [#14](https://github.com/visy/bloodborne_pc_windows_port/pull/14) (independent travel), [#6](https://github.com/visy/bloodborne_pc_windows_port/pull/6) (boss death). | Co-op implementation is **not assumed YT 1.4.0 compatible**. Compare and adapt semantics + dedicated tests, not copy its networking wholesale. |
| [Awakenchan/LanternEngine](https://github.com/Awakenchan/LanternEngine) | Alternative renderer and launcher architecture | `main`, `online-shadps4-0.20`; merged [#90](https://github.com/Awakenchan/LanternEngine/pull/90) (fog flicker); old unmerged [#87](https://github.com/Awakenchan/LanternEngine/pull/87), [#82](https://github.com/Awakenchan/LanternEngine/pull/82) are **not** production-ready patches. | Benchmark shader/render timing; GPL-3.0-or-later **additional terms** in NOTICE must be reviewed. |
| [vladtepes22/NightwatchCoop](https://github.com/vladtepes22/NightwatchCoop) | Alternate multiplayer client/launcher, isolated saves and VPN workflow | `main`, `port-0.2.7`; [related handler](https://github.com/framilano/BloodborneNucleusCoopHandler). | Review connection experience, session recovery, save isolation, multi-instance tests; avoid assuming it interoperates with YT. |
| [Wozzardman/shadnet-p2p](https://github.com/Wozzardman/shadnet-p2p) / [shadp2p](https://github.com/Wozzardman/shadp2p) | Signaling, NAT traversal/STUN and gameplay P2P reference | `main`, `dev/bloodborne-seamless-co-op`. | Source warns TCP 31313 is not independently encrypted: do not directly substitute for current production encrypted-link service. |
| [shadps4-emu/shadPS4](https://github.com/shadps4-emu/shadPS4) | GPU, GNM, HLE and graphics references | `main`; check component-specific commits/PRs when patching. | Renderer ideas require integration and validation; the emulator is not a drop-in BBPort replacement. |
| [CLSAMG22/BBSC](https://github.com/CLSAMG22/BBSC) | Downstream YT 1.4.0 BBPort/BBHost release comparison | [v1.4.0](https://github.com/CLSAMG22/BBSC/releases/tag/v1.4.0) portable variants. | **NOT** the source for original droogie BBHost; use as experimental compatibility benchmark only. |
| [Amanises-Yharnam-Together/BBSC-Yharnam-Together](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together) | Authoritative YT 1.4.0 protocol/client/launcher baseline | `main`, test rigs, network/server regressions. | Preserve five-hunter handshake and state until explicit coordinated protocol migration. |
| [ProhorovIlja/bloodborne_pc_windows_port](https://github.com/ProhorovIlja/bloodborne_pc_windows_port) | Earlier playable-track research and prototypes | `master`, own branches, PR history and Google Drive handoffs. | Re-evaluate previous work without merging no-eboot AOT experiments into production. |

## What the next source audit must do

For each candidate component, record: repository + branch + immutable commit, PR
state/CI, relevant files/functions, build dependencies, licence and notices,
architecture differences, conflicts, expected gains and reproducible acceptance
tests. Inspect sibling forks and PR alternatives before any import.

**Runtime bake-off:** run the same Bloodborne 1.09 build and equivalent scenes
under droogie BBHost and bbport (and relevant forks), recording GPU/CPU frame
times p50/p95/p99, VRAM/RAM, crashes, visual/audio defects, input latency,
shader compilation and session/network costs. Co-op gameplay must cover 5
players, joining after the leader has loaded, boss-fight death, independent map
travel, Hunter's Dream and chalices. No performance or compatibility claim
without results.

**Mod compatibility:** Bloodborne 1.09 XML patch overlaps, MOAL, Jump L3,
Doll Rebirth, event scripts and conflicting animation/script replacements.
Default off until their game hooks and co-op state are independently verified.

**Release:** distinct TEST launcher/settings and installer AppId; isolated
GitHub release channel; portable ZIP and setup EXE must carry identical client
components, verified manifests/checksums, no game dumps, no account keys and no
production server data. Store original copyrighted game/DS3 files **privately
on Google Drive**, not in public GitHub Actions or releases.

**Stop conditions:** contradictory licences/NOTICE, unproven ABI or net
compatibility, save corruption, reconnect regression, incomplete testing, or
unexplained frame-time regression. Prefer no change to a risky change.

## Observations vs conclusions

These are **verified source/PR locations and candidate capabilities**, not proof
that all proposed changes have been ported or tested. Other repositories,
branches and forks may be discovered and appended. Distinct executable
architecture, renderer and network protocols prevent a simplistic “merge
everything from GitHub” operation. Treat the best *verified* implementations as
building blocks, preserving their provenance and original licences.

## November 8: expanded GitHub source intake (bounded discovery)

This pass searches project names, active forks, branches and open PRs across the
original [droogie/bbhost](https://github.com/droogie/bbhost) (not CLS BBHost),
deadinside28, Supermedo, Mrsuss60, visy, LanternEngine, Nightwatch,
shadNet, shadPS4 and other related repositories. The searched result pages are
NOT all of GitHub. Every import needs a matched base, revision/PR, license, tests,
and a quantified benefit on the final client/server.

| Verified candidate | Integration judgment |
| --- | --- |
| [YT upstream PR #539](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/539), open | Launcher password sign-in uses Python CA store while updates use Windows truststore. Stacked TEST candidate: import exact auth/localization/tests files only after matching their base SHA; surgically adapt `bbport_coop.py` to preserve our independent updater. No TLS bypass. |
| [YT upstream PR #524](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/524), open | Travel Together lock inversion: inspect lock-order proofs and test before game-client integration. |
| [YT upstream PR #537](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/537), open | Launcher 3D map does not refresh selected game folder. Small Windows UI/test candidate. |
| [YT upstream PR #540](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/540), open | Compare ban fix to our existing PR #1/#7 before any duplicate server patch. |
| [droogie BBHost PR #217](https://github.com/droogie/bbhost/pull/217), open | Original BBHost networking lifecycle; author explicitly warns of coordinated client/server changes, not a YT drop-in. |
| [droogie BBHost PR #223](https://github.com/droogie/bbhost/pull/223) and [#218](https://github.com/droogie/bbhost/pull/218), open/draft | Upscaling/multimonitor, input and draw path; compare against master on the same Windows hardware. |
| [Supermedo PR #169](https://github.com/Supermedo/bloodborne_pc/pull/169), [#168](https://github.com/Supermedo/bloodborne_pc/pull/168), [#161](https://github.com/Supermedo/bloodborne_pc/pull/161), open | Launcher integration, offline chalice glyphs, offsite saves. Validate game-folder and server-data safety first. |
| [deadinside28 PR #440](https://github.com/deadinside28/bloodborne_pc/pull/440) and [#442](https://github.com/deadinside28/bloodborne_pc/pull/442), open | GPU queue concurrency and Vulkan lifetime risks; renderer benchmark and ABI review required. |
| [shadPS4 PR #5562](https://github.com/shadps4-emu/shadPS4/pull/5562) and [#5589](https://github.com/shadps4-emu/shadPS4/pull/5589), open | GPU/renderer implementation references, not drop-in commits. |
| [Nightwatch PR #10](https://github.com/vladtepes22/NightwatchCoop/pull/10), open | HDR experiment; test independently before transfer. |
| [MaSieS4Fun ARM port](https://github.com/MaSieS4Fun/ARM_bloodborne_pc) | ARM/FEX portability reference, NOT a Windows x64 candidate. |
| [visy Windows port](https://github.com/visy/bloodborne_pc_windows_port) | P2P four-player party and UX: not protocol-compatible by assumption with dedicated YT five-player network. |

New repository-search leads, **not yet code-reviewed**:
`bloodborne-native/bloodborne-recomp`, `bloodborne-native/bloodborne-runtime`,
`theitsnschool/bloodborne-windows-native-loader`, `LRF17/NightwatchCoop-NativePlusHDR`.
Revisit full fork and branch pagination before selecting each new subsystem.

No new candidate is released or deployed to Fornex by this intake.

## November 8: repository-family and source-level runtime comparison

Scope: this intake cross-checks the **original** runtime repository READMEs, repo
parent/fork and license metadata, active branches, and source PR deltas. It is
not a benchmark, proof of five-player compatibility, or a release recommendation.
Source file blob SHA-1s are included to make future drift visible.

| Runtime / feature | Actual source and provenance | Technical conclusion / gate |
| --- | --- | --- |
| [Original droogie/bbhost](https://github.com/droogie/bbhost) | Independent upstream, GPL-3.0; `master/README.md` blob `f983da7bd321978d6bf570c23b89e9cf35843f36`, active as of 2026-11-08; [#217](https://github.com/droogie/bbhost/pull/217), [#223](https://github.com/droogie/bbhost/pull/223), and [#218](https://github.com/droogie/bbhost/pull/218) | Full alternate x86-64 loader, PC PS4-HLE implementations and Vulkan rendering. **Not CLS's prepackaged YT BBHost**. PR #217 rewrites signaling/lifecycle and calls for a coordinated server/client upgrade. Keep this as an independent runtime bake-off candidate with a protocol bridge/reimplementation study, NOT an assumed replacement for YT 1.4.0's encrypted link. |
| [deadinside28/bloodborne_pc](https://github.com/deadinside28/bloodborne_pc) | Independent bbport, GitHub GPL-2.0 metadata; `master/README.md` blob `febde4a33feff8ce1a6f1e02f9867966b76dd1a7`; [#440](https://github.com/deadinside28/bloodborne_pc/pull/440), [#442](https://github.com/deadinside28/bloodborne_pc/pull/442) | Alternative existing native x86-64 runtime with Vulkan. Check GPU submission counts and sampler destruction against current YT baseline. Reproduce race in code-level tests before importing. |
| [Supermedo/bloodborne_pc](https://github.com/Supermedo/bloodborne_pc) | Fork of deadinside28, default `windows`, GPL-2.0 metadata, README blob `a3fb9dd6fcfd40c61f27736fa27abc287e7c133b` | Candidate Windows UX/launcher and robust save management. [PR #161](https://github.com/Supermedo/bloodborne_pc/pull/161) proposes external backup copies under `%APPDATA%/bbport-launcher/save_backups` and includes six synthetic backup regressions. **Not a direct import:** YT currently lacks `bbport/launcher/bbport_saves.py` and `bbport/tests/test_launcher_saves.py`. Adapt only with explicit save-layout mapping, distinct TEST app namespace, atomic writes, quota/retention, permissions, backups preserving existing characters, restore and rollback tests. No live save overwrite. |
| [Mrsuss60/bloodborne_pc_windows_port](https://github.com/Mrsuss60/bloodborne_pc_windows_port) | Fork of deadinside28, GPL-2.0 metadata, default `master` | Compare Windows loader, UI, mouse input and Vulkan changes independently; neither the name nor the metadata proves it is the separate user-described "Massus". |
| [visy/bloodborne_pc_windows_port](https://github.com/visy/bloodborne_pc_windows_port) | Fork of Mrsuss60, GPL-3.0 metadata; `master/README.md` blob `c3cc6f337156532222ed0e35e4bdf799c4645b63`, README version **0.7.9** on 2026-11-08 | Claims direct party co-op for host + up to 3 friends (**four**, not our required five), no server. Different protocol and lifecycle; mine UI/travel/boss-death ideas with clean integration tests, not blind code reuse. |
| [bloodborne-native/bloodborne-recomp](https://github.com/bloodborne-native/bloodborne-recomp) + [bloodborne-runtime](https://github.com/bloodborne-native/bloodborne-runtime) | Independent GPL-2.0 repos, README blobs `a6f1eb854d8faec5f1d7837ef9c74fbebda6cc67` and `d30942a6d7d18d63092c14aa4ef64f8f1047cc5b` | An actual static-recompiler **candidate** for the *separate* native-port track: turns owner-supplied game executable functions into C and a native library, but still relies on runtime translation/fallback for non-recompiled functionality. Not a completed PS4-free Windows port; do not conflate generated game logic with original independent PC game source. |
| [LRF17/bbhost-NativePlusHDR](https://github.com/LRF17/bbhost-NativePlusHDR) | Fork of original droogie/bbhost, GPL-3.0, `master/README.md` identical blob to original `master` above at this audit | Clone-like README **does not show any HDR advantage**. Diff branch commits/source before treating HDR in repository name as a feature. |
| [ambientmf/bbhost-restock-plugin](https://github.com/ambientmf/bbhost-restock-plugin) | Standalone GPL-3.0 BBHost plugin; `main/README.md` blob `90150bf94d366cb33fe669e20ff2edade5e88dde`; author reports gameplay with BBHost 0.2.20/21 | Interesting QoL restocking existing storage (does not spawn free items); validate in YT five-player/invasion world state or reimplement behavior, never load the incompatible BBHost plugin into YT runtime by default. |
| [ypcat/bbhost-savebak-plugin](https://github.com/ypcat/bbhost-savebak-plugin) | Linux BBHost plugin, GPL-3.0; README blob `f8dae4e4dcfe3c091c2b20684dc6a71ab31f6950` | Save safety inspiration only. Reads Linux `/dev/input` and has a separate data layout; not a Windows YT drop-in. Restore needs backups, validation and explicit player control. |
| [shadps4-emu/shadNet](https://github.com/shadps4-emu/shadNet) | Separate shadNet C++/Qt source, GitHub repo metadata did not expose a license identifier | Primary network reference, but source-level license, dependencies, and YT protocol must be established before importing any code. No assumptions from project name. |
| [theitsnschool/bloodborne-windows-native-loader](https://github.com/theitsnschool/bloodborne-windows-native-loader) | Standalone repo, GitHub metadata lacks license id; README advertises remote PowerShell install | **Unverified / no import.** Do not execute scripts downloaded from unrelated project sites or include untrusted binaries in official releases; first review exact source, package provenance, licensing and supply chain. |

### Server overlap audit: upstream #540 vs our existing #1/#7

Per-file patch text was compared directly between
[upstream #540](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/540)
and [our #1](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/1) /
[our #7](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/7).
The patches for **five files** are exactly equal: `docs/HOSTED_SERVER.md`,
`server/src/admission.cpp`, `server/src/admission.h`,
`server/src/link_server.cpp` and `server/src/link_server.h`.
`server/src/admin.cpp`, `server/tests/test_admin.cpp`, and
`server/tests/test_admission.cpp` are NOT byte-identical patches: ours
contain other changes/tests and must be compared semantically. This means the
core flooding-link no-automatic-IP-ban fix was already ingested in the TEST
server candidate; blindly importing upstream #540 would duplicate it and could
revert newer admin/stat changes. Preserve explicit operator `banned.txt` bans.

### Expanded discovery coverage and stop rules

GitHub search sampled `bbhost fork:true in:name sort:updated-desc`
(68 returned), `bloodborne_pc fork:true in:name sort:updated-desc`
(70 on page 1, 70 on page 2), `LanternEngine` (47),
`NightwatchCoop` (6), `shadNet` (32), and other runtime/network/mod
queries. These are search-page counts, NOT a global unique total or proof every
fork was checked. Individual candidates must be followed into branches, PRs,
commits, source and relevant tests. Use pagination and repeat on each subsystem
decision, not a first-result shortcut.

Critical hard stop: never deploy a new client+server pair with a changed wire
protocol, auto-replace saves, copy copyrighted game data to CI, silently switch
the TEST updater's origin, or promote a performance claim without matched
hardware/scene measurement. Source README statements are *project claims*, not
independent reproduction.
