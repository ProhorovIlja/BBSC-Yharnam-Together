# Source intake and actual optimizations, 15 November 2026

The current inventory spans **34 configured public repositories, 2,208 branch heads
and 5,853 advertised PR heads**. Yharnam Together alone advertises 603 branches and
593 PR heads. All configured Git queries completed. A ref inventory identifies
versions; it does not establish that the source at every ref was read or tested.
This is not complete coverage of GitHub, the Internet, Drive or every renamed fork.

The [configured sources](../../tools/ultimate/source-watch.json) are maintained in
`tools/ultimate/source-watch.json`; counts and ref-map hashes are in
[SOURCE-INTAKE-20261115.json](SOURCE-INTAKE-20261115.json). The full SHA/ref snapshot
is in the private Drive validation archive named
`Bloodborne_Upstream_Intake_Validation_EN_20261115.zip`. An initial scan exposed two
incorrect repository names; resolve them to `Mrsuss60/bloodborne_pc_windows_port`
and `NVIDIA-RTX/NRD`, retaining the initial partial scan as evidence. Failed scans
never count as a complete inventory or as deletion of all old branches.

## Reproducible continuation

```
python tools/ultimate/source_watch.py --sources tools/ultimate/source-watch.json \
  --output new-source-refs.json --previous previous-source-refs.json
```

The scanner records exact public heads and PR heads, atomic snapshots and explicit
added/changed/removed ref deltas. It neither merges nor executes donor code. Tests
cover invalid/empty responses, conflicting refs, malformed repository names, failed
queries, deltas and failed snapshot publication. The existing three-OS preparation
workflow discovers these tests. No unattended schedule or background job is implied.
Tags/releases, private/unadvertised refs, issue discussions and semantic source
review need separate intake. GitHub's connector rejected the fork-list endpoint;
repository-name search found eight other related copies, including the Linux-named
fork, but cannot certify the complete fork network. Discover more candidates as
research proceeds and add verified names to the configuration.

## Yharnam Together comparison

Fetched upstream main `5cef8e0c3577d17c6a933feb21f55101038e51a6` separately from our
development branch. Do not wholesale replace our source: it includes extra world
backup I/O failure handling and earlier Ultimate work that upstream main lacks.

| Inspected change | Source identity | Current disposition |
| --- | --- | --- |
| Travel Together receive/send lock inversion | [PR524](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/524), `b0fbd76b2a1aad8a8f8567ed9f55fadfe20fb047` | Already present: separate bounded inbox mutex; retain production-source regression. |
| Guest lamps and personal progress | [PR592](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/592), `2d287f9c906fa41469408c1c3483477a2fd73920` | Present; retain our additional failure-aware backup writes/joins. |
| Restart greeting preservation | [PR596](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/596), `acb3c6f457dbeadeb8ea6ce88f74af0df2a6a1ec` | Present with our additional stale-target/sequence tests. |
| Null vertex input and launcher error spam | [PR590](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/590), `8794076f3e09df95047207eb8c2ae26fd70710f4` | Reviewed PR evidence and overlap; no new copy imported. |
| Supermedo crash-fix intake | [PR593](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/593), `26b9f1608fd70bf014648cd85ef9e65e23e1acf6` | Reviewed upstream intake; do not replace our later GPU/copy/NGX fixes. |
| Crash-suite pickup drifts into another map | [PR599](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/599), source commit `bb4d7e92951063f1becc0307e66f5b2f6d9e2a46` | Adapted the missing `LEAVE_ITEM_SPOT` teleport in `tools/rig/suites.py`, GPL-2.0-or-later attribution retained. Host pickup now starts at the intended item's location. |

The rig change fixes a test's precondition, not a gameplay pickup or host-migration
bug. Upstream's game observations are not our own game validation.

## Actual C++ client/server work

`GameLinkPeer::Flush` copied every queued unreliable packet into a second vector
immediately before destroying the original. Move its existing payload allocation
into the outgoing frame instead and reserve the fresh entry count. Reliable
packets still keep their own stored payload for retries. No packet is folded by
channel and no wire format, stream epoch, ACK or routing rule changed.

A production-header allocation test observes one fewer payload allocation/copy per
unreliable packet: zero payload allocations during Flush instead of one, with the
same buffer identity and bytes. Reliable first-send copy, retry and ACK retirement
remain checked. Six standalone CTest programs, including the existing GoogleTest
stream suite, pass locally; ASan/UBSan passes for the allocation case. The unchanged
wire transcript hash is `9003454785029844084` (FNV1a64). These are deterministic
ownership/correctness observations, not game/server CPU or Internet-latency measurements.

## Rig regressions resolved during validation

The first full rig run exposed three failures from interpreting captured Windows
paths with the host's separator, plus a TCP proxy port left bound on Linux. Compare
process-list paths with one separator representation on every OS. No process-kill
command or production endpoint is invoked by these unit tests.

For the delay proxy, shutdown sockets before closing to wake blocked accept/recv,
join the accept worker with a bounded wait, reject connections completing after
stop and interrupt delayed writes when stopping. Replace list pop(0) with deque
popleft for its FIFO. Real localhost tests verify byte delivery/delay, outage and
port rebinding after stop, including an active connection during a long outage.
The fixed full rig run discovers 190 tests: 188 pass and two skip on this Linux
host. The 37 preparation/source-watch tests also pass. Windows/macOS CI verifies
the shared C++ and rig tests separately; consult the run, not this local result.

The first Windows CI run also exposed game-view cleanup following junctions on
Python3.11: `os.path.isjunction` did not exist, so its fallback falsely treated a
junction as a real directory and the second synthetic merge removed an original
fixture file. Inspect links/reparse points with lstat before descending. The
existing repeated-merge test checks original game/update preservation; do not
skip it or merely raise the CI Python version to conceal this defect.

## Rendering/performance candidates still under evaluation

* Supermedo SSR shading-rate commit
  [`6085365d14c179612d7fffe91a989806e031aed8`](https://github.com/Supermedo/bloodborne_pc/commit/6085365d14c179612d7fffe91a989806e031aed8)
  is a concrete optional optimization, using coarse fragment shading for one known
  reflection shader. It changes sampling/image quality. Before adoption, query the
  supported fragment sizes/sample counts, handle resolution and pipeline caches,
  and measure visual/temporal regressions on our renderer. Donor timings are not ours.
* LanternEngine [PR96](https://github.com/Awakenchan/LanternEngine/pull/96),
  `ce36515b1fe21cc7e6d43a886844512ce60d8848`, proposes screen-probe indirect lighting
  and GT7 tonemapping. Reviewed PR description; not integrated or GPU-tested here.
* `bloodborne-native/bloodborne-runtime` main is
  `234006761712f8621966c1a5e9f97b3b789a3d09` in this snapshot. [PR7](https://github.com/bloodborne-native/bloodborne-runtime/pull/7)
  (`643b0616354b3cdd8c7f991aa0814652df0d73b8`, merged) provides host math/wide-string
  imports; its own measurements reduce translator entries without measurable FPS
  gain at the tested scene. [PR12](https://github.com/bloodborne-native/bloodborne-runtime/pull/12)
  (`872ee9bd337656c78aae928830e3c93c1d108777`, closed/unmerged as inspected) is a
  Metal synchronization/copy lead. Compare current ancestry and ABI before adaptation;
  these PR descriptions do not establish native Metal integration in our branch.

## Ray/path tracing direction

Our renderer already contains optional Vulkan ray-query ambient occlusion in
`vk_ray_occlusion.cpp`, acceleration-structure capability checks in `vk_instance.cpp`
and screen-lighting integration. It builds from available map mesh data; that is
not a complete rendered-scene material/light/animated-geometry representation or
a full path tracer. This checkpoint does not add or GPU-certify that existing code.

| Candidate | Pinned main/master | Useful boundary |
| --- | --- | --- |
| [RTXPT](https://github.com/NVIDIA-RTX/RTXPT) | `303b408ab81790a5051abd7573830b7a4112eb8e` | Path-tracer reference and incremental deferred-renderer sample; D3D12/Vulkan, substantial device/scene/denoising dependencies. Root license is NVIDIA RTX SDK terms, not generic MIT. No code imported. |
| [dxvk-remix](https://github.com/NVIDIAGameWorks/dxvk-remix) | `2b46bed0c2c1f2416c902c468baf837389869cbe` | Runtime/API route requiring explicit geometry/material/light/camera submission or compatible interception; not an automatic modern Vulkan-game switch. |
| [NRD](https://github.com/NVIDIA-RTX/NRD) | `90dea8bd91ec6b58d0f90cb6adf53c7da613b82c` | Denoiser, not a ray/path tracer; needs correct motion/depth/normals/hit distances/history inputs. |

The watchlist also inventories AMD FidelityFX/Brixelizer, Radeon Rays and Embree
refs; those inventories are not source audits or integrations. Any RT/PT mode
must remain optional and retain raster/older-hardware fallbacks. Establish scene
representation and bounded GPU resource lifetime before selecting a denoiser.

## Language choices

Hot stream/render/runtime work is already C/C++. Remove unnecessary work and
allocations first, then profile CPU time, frame percentiles, memory, I/O and waits.
Use Rust where a measured workload and ownership/FFI boundary justify it. A language
rewrite alone does not establish lower load or preserve behavior; do not add an
extra framework/runtime solely for a claim of optimization. The packet fix above
is an observed ownership improvement with the existing language and protocol.
