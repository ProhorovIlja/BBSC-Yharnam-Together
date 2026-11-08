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
