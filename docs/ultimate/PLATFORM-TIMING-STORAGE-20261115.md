# Ultimate timing, graphics, storage and audio contract

Date: 2026-11-15. User-requested product direction. This document specifies required behavior;
it does not enable a binary patch or claim a playable native port, fixed-step simulation,
DirectStorage integration, a D3D12/Metal backend or measured performance gains.

## Independent clocks

| Work | Target clock | Required behavior |
|---|---|---|
| Gameplay, collision, authoritative animation events/root motion, AI and scripts | Fixed 60 Hz target | Exactly-once transitions; reference movement, hit/parry windows and game speed |
| Rendered poses, camera, visual-only particles and UI | Actual render/presentation time | Interpolate audited snapshots; no additional gameplay events from extra frames |
| Audio mixing/playback | Audio device/sample clock | Bounded real-time work, stable buffering, no dependency on GPU frame completion |
| Network transport/control | Protocol and measured path budgets | Tick-stamped state; queue/authority guarantees independent of display FPS |
| Video/cutscene streams | Media timestamps | Preserve playback speed and audio synchronization |

Render caps include 60/90/120/144/165/240/custom/uncapped where supported. Display FPS must not
change movement, physics, animation events, cooldowns, damage, AI, scripts or network authority.
Visual pose interpolation is required for smooth rendering above the simulation rate. Sample
input continuously and apply timestamped gameplay actions on ticks; evaluate late camera/UI
input separately where it cannot alter authoritative outcomes. Interpolation/prediction has
latency and correction costs that must be measured, not described as zero latency.

The fixed 60 Hz target is conditional on a complete consumer audit. Existing 30 Hz semantics,
fixed substeps, baked animation/events, Havok and per-frame factors must be calibrated against
the reference game. Preserve subsystem substeps where needed. Never force every literal to
1/60 or merely cap the existing coupled main loop at 60. Audit double ownership and overlapping
timing patches before integration. Pause/loading/resume and bounded catch-up need explicit
behavior; overload must not silently discard authoritative hits, rewards or world transitions.

Frame generation is an optional presentation feature. It must not advance simulation, gameplay
events or network ticks. Report simulated ticks, real rendered frames and generated frames
separately. Frame pacing uses a monotonic clock, appropriate presentation/VRR support and bounded
frames in flight; avoid presenting a deeper queue as lower latency. Cap/unlimited and power
policies remain user-selectable. Uniform frame times are a measured target, not a guarantee for
all hardware, shaders, storage stalls and drivers.

## Platform strategy

| Target | Primary development direction | Additional candidate paths |
|---|---|---|
| Windows | Native client; retain the existing Vulkan renderer as the integration baseline | D3D12 backend if representative benchmarks justify its maintenance; capability-gated DirectStorage |
| Linux | Native Linux executable and Vulkan | Proton for testing/compatibility of the Windows build; portable asynchronous I/O plus measured native optimizations |
| macOS | Native host/CPU target; Metal-compatible graphics path | Native Metal or Vulkan-on-Metal selected by required features, hardware and SDK validation |

Vulkan and D3D12 are separate renderer implementations, not additive speed switches. Do not
introduce multiple API translation layers merely to list more technologies. Backend selection
must preserve rendering correctness, feature coverage, cache ownership and fallback behavior.
Proton runs Windows games on Linux; it is not evidence of a native Linux build. Apple's porting
tools are evaluation/conversion aids, not evidence of a finished native macOS game. Apple Silicon
also needs an audited native ARM64 CPU/AOT path; a Metal surface alone does not solve that.

For Vulkan-on-Metal, inspect the current SDK/driver and portability feature subset instead of
assuming parity with desktop Vulkan. The current MoltenVK project points Apple Silicon users
toward KosmicKrisp and retains separate guidance for Intel Macs; pin and validate the selected
implementation before making it a dependency. A macOS helper-test pass is not game acceptance.

## Resource streaming and storage

DirectStorage is a resource-read/streaming API, not a renderer or automatic FPS improvement.
Evaluate it as an optional Windows I/O/decompression backend with ordinary asynchronous reads
as a fallback. Supported compression, staging-memory budgets, cancellation, priorities, cache
integrity and CPU/GPU contention require measurement. Existing game archives do not become
GPU-decompressible by adding a flag. An owner-side preparation/cache format may be needed;
preserve original data and verify decoded bytes. Saves keep their separately tested atomic
write/recovery path. Linux/macOS use platform-appropriate I/O behind the same resource contract.

Measure cold/warm startup, scene transitions, small-read CPU cost, stutter during streaming,
peak RAM/VRAM and rendering contention. A storage optimization must not starve rendering,
audio or the authoritative network path. No GPU decompression claim without real codec and
device tests. Avoid mandatory dependence on a particular disk class for correctness.

## Audio, launcher and server

Audio: independent sample clock, bounded/preallocated callback work, measured stable buffer
sizes, resampling/drift handling and device-change recovery. Measure underruns, end-to-end
latency and CPU load under streaming/network/GPU stress; do not tie sound speed to FPS.

Launcher: bounded background work, responsive UI and idle/minimized power behavior; no full
game-rate polling. Expose supported settings coherently in launcher/game and persist them
without overwriting concurrent user changes. Unsupported options must be unavailable with a
clear reason; do not show an implemented status for this target contract.

Server: preserve admission/world/reward authority and hybrid-path invariants. Simulation tick,
snapshot/send cadence and control/heartbeat cadence are separate choices. Presentation FPS must
not multiply network traffic or backend CPU use. Tune rates by measured update age, loss,
jitter and bandwidth, with reconnect/fallback tests; do not promise zero network delay.

## Acceptance and current evidence

Compare identical scenes/input traces at 30/60/90/120/144/240/uncapped render, with frame
generation off/on, forced stalls, CPU/GPU bottlenecks and co-op loss/jitter. Check game speed,
movement/jumps/rolls, gravity, hit/parry windows, root motion, animation events, boss transitions,
scripts, cutscenes, saves and peer consistency. Track tick debt, p50/p95/p99 frame time, frame
time variance, input latency, shader/streaming stalls, RAM/VRAM, audio underruns and bytes/player.
Report hardware, OS, backend, real/generated FPS and capability/fallback paths for every result.

Current timing patches in scripts/cloth*.py, foliage_time.py, air_drag.py and effect_time.py are
per-subsystem fixes, not proof of the clock split above. Inspected Supermedo/bloodborne_pc PR156,
head 630472865482c8175cbfdabc741df047b4fcdf60, adjusts per-frame values to the main loop's step;
that is not a global fixed-60 simulation implementation or measured gameplay equivalence here.
The private native startup diagnostic currently reaches 128 constructors, not game main. GPU
configuration progressed through Vulkan discovery/fmt and currently stops at missing Boost.

## Primary references checked for this requirement update

- https://partner.steamgames.com/doc/store/application/platforms/linux/proton
- https://learn.microsoft.com/en-us/windows/win32/dstorage/dstorage-portal
- https://github.com/microsoft/DirectStorage/blob/main/Docs/DeveloperGuidance.md
- https://developer.apple.com/metal/
- https://github.com/KhronosGroup/MoltenVK
- https://github.com/Supermedo/bloodborne_pc/pull/156
