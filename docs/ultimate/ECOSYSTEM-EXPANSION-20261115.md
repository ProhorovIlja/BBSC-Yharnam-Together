# Ultimate ecosystem expansion: requirements and integration gates

Date: 2026-11-15. Owner-requested scope. This register extends the timing/platform
contract and the original bug catalogue. Only the input fixes explicitly marked
below are implemented by this checkpoint; the other rows remain requirements.
They must not become enabled settings or release claims merely because listed.

## Performance, compatibility and presentation

| ID | Required behavior | Acceptance |
|---|---|---|
| E01 | Native Windows/Linux/macOS port using owner-supplied assets, with prepared native code and no PS4 executable at Play time | Preserve the separate no-eboot profile, import and file/module-trace gates; current native diagnostic remains before game main |
| E02 | Optimize client, server, launcher and game code without losing behavior | Profile first; compare equivalent workloads and correctness; language/function rewrites require differential tests and measured gains |
| E03 | Bound CPU work, worker counts, RAM/VRAM use, disk I/O, network queues and background polling | Report p50/p95/p99 times, peak memory, bandwidth and idle load; reject resource leaks and unbounded caches |
| E04 | Video, audio, cutscenes, animation and gameplay keep correct independent clocks | Use the fixed-simulation/variable-render contract; check device changes, audio underruns and AV sync under stalls |
| E05 | Latest usable DLSS/FSR/XeSS, latency features including Reflex, and older-hardware fallbacks | Pin SDK/API/OS/driver/model requirements; measure quality, latency and cost; preserve native/TAA and compatible older analytical paths |
| E06 | Shader/pipeline and map/resource pre-warming | Bound memory/time/disk budgets, cancellation and startup delay; cache keys include relevant source/driver/device versions; never require loading every map into RAM |
| E07 | Robust devices and accessible controls | Hotplug, focus loss, controller calibration, keyboard layouts, mouse raw input and configurable bindings; test device switching and stuck-input recovery |
| E08 | Every option has a useful explanation and coherent launcher/game behavior | One persisted format, defaults/reset, unsupported reasons, migration and preservation of unrelated settings; no decorative unimplemented toggles |
| E09 | Release notes and diagnostics in the launcher | Versioned changes, known issues, save/protocol compatibility, rollback and bounded/redacted reports; do not call build tests gameplay validation |

Latest SDK check, not integration: NVIDIA's public DLSS repository lists 310.9.16;
NVIDIA staff state on 9 November that the DLSS 5 SDK is not publicly available.
DLSS 5 neural rendering is distinct from the public SR/RR/frame-generation SDK.
Community Vulkan/D3D12 bridges, an independent Vulkan network implementation and
UE editor integrations now provide concrete research routes. Track these alongside
official SDK access: see [pinned candidates](NEURAL-RENDERING-CANDIDATES-20261115.md).
Their source licenses, external runtimes/weights, GPU requirements and measured
game integration are separate checks. No neural-rendering backend is enabled yet.
AMD lists FSR SDK 2.4, Upscaling 4.1.2 and analytical 3.1.6, including a Windows
Vulkan loader/effect-DLL path. That is not proof of native Linux/macOS support.
Intel's public XeSS SDK is 3.0.2. Each effect and latency component needs its own
capability and license checks; a new SDK number alone does not update this port.
Newer paths may cost more or alter image quality. Default selection must follow
measured profiles and provide fallbacks rather than promise universal improvement.

## Input and gameplay quality of life

| ID | Required behavior | Current treatment |
|---|---|---|
| E10 | Shift/Ctrl/Alt combinations, multiple alternatives, keyboard/mouse/gamepad remapping in launcher and game | This checkpoint fixes keyboard-modifier loss in Windows and SDL capture; adds delimiter-safe `Comma` through all naming boundaries |
| E11 | Dedicated jump binding, independent of dodge/sprint where requested | Pending audited gameplay action hook and state/context checks; synthesizing a Circle press is not a complete jump action |
| E12 | Useful new code-driven mechanics using existing assets/animations | Optional, versioned rulesets; compatibility and reference-playthrough tests before enabling |
| E13 | Healing on ladders and selected animation-cancel/QoL changes | Audit ladder/climb/death/fall/network states, animation availability and resource costs; no arbitrary cancel-any-action default |
| E14 | Full intro skip and configurable FOV/camera | Distinguish skippable logos from required initialization/cutscenes; bound competitive camera/FOV rules and preserve event completion |
| E15 | Phantom effects, cosmetics and other FromSoftware-inspired features | Use compatible existing Bloodborne assets; inspect original-source rights and hook/rig compatibility; do not redistribute another game's assets |

Input validation includes the actual launcher capture methods, the actual SDL
capture utility and production runtime parser/serializer/precedence logic. The
new `Comma` spelling leaves commas available as alternative separators and keeps
old bindings compatible. Some menu/capture keys remain reserved; arbitrary-key
support and user-configurable menu hotkeys are still broader acceptance work.

## Mods, online integrity and hybrid networking

| ID | Required behavior | Acceptance |
|---|---|---|
| E16 | Offline mods, patches, trainers and explicit cheat tools remain usable | Separate offline profile and provenance; online eligibility must not be inferred solely from an edited offline save |
| E17 | Standard online sessions permit approved compatible modifications but reject gameplay cheats | Versioned mod manifests, content/patch hashes, declared effects and admission rules; server validates authoritative state transitions |
| E18 | Detect impossible health/stamina, damage, item grants, teleports and malformed packets | Server-owned invariants, replay/event IDs, bounded rate/delta checks and legitimate teleport/cutscene exceptions; verified evidence and false-positive handling |
| E19 | Approved FOV, camera, visuals and built-in QoL coexist with fair online play | Separate local cosmetic/accessibility options from visibility, collision, timing and balance changes; competitive sessions may require tighter limits |
| E20 | Public fair-play, compatible private modded sessions and unrestricted offline play are distinguishable | Participants negotiate the same gameplay rules/content schema; presentation-only differences allowed by explicit policy |
| E21 | Fast encrypted direct peer traffic with safe server authority and relay fallback | Keep the existing hybrid transport gates, 2/3/5-client tests, NAT/reconnect/loss/jitter coverage and progress/save integrity |

The current `server/coop/cheat_watch.h` is an observation/reporting component,
not proof that cheats are prevented. Client declarations and launcher hashes do
not establish that a process remains untampered after launch. Blocking process
names or every unknown DLL is insufficient and would also break legitimate
drivers, overlays and SDKs. Approved modules need scoped capabilities and exact
provenance; consequential online actions need independent server validation.
Do not import another game's player blocklist as a Bloodborne verdict.

## Website, maps and knowledge

| ID | Required behavior | Acceptance |
|---|---|---|
| E22 | Existing website receives useful client/server data | Authenticated, versioned, bounded snapshots/events; server-confirmed versus client-reported fields identified; no direct process-memory exposure |
| E23 | Accounts, profiles, player statistics and permitted profile actions | Account ownership, field-level access, audit and revocation; never expose tokens, credentials or private save data |
| E24 | Website and in-game live 3D map | Compatible coordinate transforms/map versions, bounded update cadence and authorized location visibility; no hidden-enemy/PvP location leakage |
| E25 | Collectibles, bosses, achievements and completion/progression views | Separate personal/team-world progress, NG cycles, DLC/region/version and spoilers; distinguish unknown from incomplete |
| E26 | In-game wiki, guides, builds and complete item-location guidance | Versioned, sourced content with offline cache and review; do not execute scraped instructions or reproduce unlicensed articles wholesale |
| E27 | Chalice guide, glyphs, item farming and dungeon completion | Distinguish fixed/story/root/generated dungeons, seeds and online glyph availability; validate exact conditions and dates rather than claim enumeration of every possible dungeon |
| E28 | Updates keep the website, launcher and in-game knowledge consistent | Schema/content versions, cache invalidation, migration and visible source freshness; no unreviewed live gameplay changes from wiki edits |

## Optional expanded remaster rules

| ID | Owner-requested feature | Required design gate |
|---|---|---|
| E29 | Friendship and romance with eligible NPCs/boss-derived NPCs | Explicit optional narrative routes, suitable adult characters, player choices and existing-animation feasibility; do not claim new authored scenes or voice content already exists |
| E30 | Offer to spare eligible low-HP bosses and make them available as NPCs | Audited per-boss eligibility, synchronized decision, safe relocation/idle behavior, quest/arena and save consistency; unsupported bosses need an explicit reason |
| E31 | Appropriate gifts increase affinity and unlock existing-item rewards | Curated character-specific gift/reward tables, inventory consumption, authority, caps and repeat/NG rules; prevent duplicate rewards and farming exploits |
| E32 | Normal boss kill retains normal items; sparing has a coherent alternate route | Exactly-once outcomes/rewards and recoverable quest transitions, including disconnect, reload, shared worlds and later completion |
| E33 | More Insight-dependent visuals/discoveries using existing assets, such as skies | Audit original Insight consumers and map resources; avoid changing quest/time-of-day flags merely to select a sky; separate cosmetic and gameplay effects |
| E34 | Opt-in invasions controlling an eligible boss during another player's boss fight | Matchmaking consent/rules, constrained moves, existing rig support, authority, host migration and exactly-once win rewards; no arbitrary client actor takeover |
| E35 | Additional combat, balance, boss and area enhancements inspired by other games | Per-feature prototype, measured behavior and explicit compatibility; no blanket animation/asset feasibility claim |

These are requested expansion mechanics, not assertions about canonical lore or
current gameplay. Preserve the full request, then implement compatible subsets
with clear acceptance. The owner's term "Dusk Blades" is retained as an
unresolved inspiration reference; do not select files or assume a title from it.
The initial relationship proposal is male-player/female-NPC and female-player/
male-NPC romance, alongside friendship routes; record eligibility per character.
Offline-edited characters need an explicit online import/eligibility policy and
separate profiles where necessary; do not silently overwrite their saves.

## Yui source intake

Enumerated all 21 public repositories returned for the currently accessible
`yuiamoroll` account; page 2 was empty. Old LukeYui release references now point
to this ecosystem. [The inventory](YUI-SOURCE-INVENTORY-20261115.json) records
exact default-branch heads and tree counts. Seven trees contain C/C++/header/
ASM/Lua/CS source files, including libraries; this is not seven complete co-op
implementations. The six named SeamlessCoopRelease trees are release/version/
blocklist metadata, without such source files in their checked default trees.
Release assets, other branches, forks and full histories are separate work.

Useful research leads: Blue Sentinel's documented invalid-item/stat/exploit
protection and save backups; randomizers' progression exclusions and seed
compatibility; HKS data exposure and debug tooling. The HKS example explicitly
warns that invalid pointer traversal can crash. Use validated typed data access,
not raw arbitrary-pointer scripting, for the site/wiki/game interface. Root
license files were recorded; absence does not certify permissions or preclude
per-file licenses. No Yui code or blocklist is imported in this checkpoint.

## Primary references checked

- https://forums.developer.nvidia.com/t/official-dlss-5-neural-rendering-plugin-access-for-unreal-engine-5-8-2/382731
- https://github.com/NVIDIA/DLSS/releases
- https://gpuopen.com/amd-fsr-sdk/
- https://github.com/intel/xess/releases
- https://github.com/yuiamoroll
- https://github.com/yuiamoroll/Blue-Sentinel-Release
- https://github.com/yuiamoroll/Scripts-Data-Exposer-FS
