# Community neural-rendering candidates, 15 November 2026

Community DLSS 5 projects exist and are concrete integration research candidates.
An unavailable general-release neural SDK does not mean that every community route
is unavailable. None of the candidates below is currently an enabled port backend.
This is a scoped source investigation, not an audit of every fork, branch or PR.

## Pinned source snapshots

| Repository | Commit | Route and observed boundary |
| --- | --- | --- |
| [AlanBacker/dlss5-vk-bridge](https://github.com/AlanBacker/dlss5-vk-bridge) | `522ea19dda2e835f603e1412ea7cd2f096dc0904` | Windows Vulkan NGX to D3D12 interop; requires a separate neural add-on and runtime. The bridge alone does not add neural rendering. |
| [NIGos/dlss5-bridge](https://github.com/NIGos/dlss5-bridge) | `d1cc508a7097534c5c0e01a868ebe3b6657b932b` | ReShade bridge for DX11/Vulkan; separate add-on/runtime, per-route compatibility. Proton reports do not prove native Linux or macOS support. |
| [maanHimself/OpenDLSS-NR](https://github.com/maanHimself/OpenDLSS-NR) | `9d08f4184bbcb9d858e2fb7a7834ec0837a9d2f1` | Independent Vulkan network implementation; user-supplied model. Current native execution requirements include NVIDIA-specific extensions. |
| [praveenkumarappu/DLSS5ForUE5](https://github.com/praveenkumarappu/DLSS5ForUE5) | `651c060f0240787ce4494ca1866cc5f010562701` | UE editor/D3D12 integration; packaged Development/Shipping is explicitly unsupported in the checked README. This port is not a UE project. |
| [al4xdev/dlss5-enabler](https://github.com/al4xdev/dlss5-enabler) | `9eaf9a1fa71950de2f3ae7a9d3cd7e43a8a4808e` | Installation/orchestration of other tools, including Proton paths; not a native render backend. |

The five root source licenses were read and are MIT. Preserve each applicable
notice when adapting code. OpenDLSS-NR's NOTICE excludes NVIDIA software/weights
and grants no NVIDIA rights; the UE project's third-party notice separately
documents unresolved redistribution of its modified neural DLL. Do not infer
runtime/model distribution permission from a source license. No neural runtime,
weights or donor release binaries were imported into this repository.

## What was examined and tested

Read the candidates' READMEs and licenses, OpenDLSS-NR's NOTICE, numeric helpers,
reference declarations, frame/execution/weight documentation and the UE project's
third-party notice. Inspect the Vulkan bridge's cross-API synchronization code;
its imported D3D12 fences/timeline semaphores show why this is more than copying
an upscaler DLL. These observations are source review, not local GPU validation.

An independent CPU probe checks the pinned OpenDLSS-NR `src/numeric.h`:
65,536 binary16 decodes and FP8 E4M3 publications, and 1,255,994 float32-to-binary16
comparisons against compiler IEEE half conversion. All pass, including adjacent
halfway samples and deterministic random float bit patterns. This establishes
only those arithmetic helpers; it does not validate network inference, weights,
GPU shader parity, image quality, speed or compatibility with this port.

## Integration direction

Keep independent Vulkan inference as a candidate for an in-renderer experimental
backend, while treating the Windows cross-API bridge as an optional external
compatibility route. OpenDLSS-NR's current native device path asks for cooperative
matrix/float8/NVIDIA CUDA-kernel-launch extensions and targets NVIDIA arithmetic;
Vulkan in the project name does not imply AMD/Intel/Apple compatibility. Its
separate browser WebGPU port is not proof of native Metal integration.

A usable backend must adopt our live device/queue and define resource ownership,
motion/depth/proxy conventions, per-view history, resets, HUD ordering and resize
retirement. Model provenance/hash checking and feature-specific capability probes
remain necessary. Measure inference time, VRAM, latency and temporal artifacts on
actual game frames before exposing an enabled setting. Preserve native/TAA and
existing compatible upscalers. Neural image synthesis is a separate effect from
super resolution and frame generation; all three need independent controls.

## Implemented render correctness fix

The existing NGX Frame Generation bridge inverted supplied camera matrices with a
shortcut valid only for symmetric perspective. It now inverts the supplied 4x4
projection with scaled pivoting, checks the float inverse in both multiplication
orders, and rejects singular/non-finite matrices before NGX evaluation. Camera
history transforms are also checked for finite entries. This fixes the matrix
contract for off-centre/jittered, orthographic and reversed/infinite-far projections;
it is not a claim that neural rendering was added or gameplay artifacts were tested.

The SDK-free CPU test covers five projection/alias cases and five rejection cases.
Linux Release and ASan/UBSan pass. A three-OS Actions workflow checks this helper.
The actual optional Linux NGX shared bridge also builds/links against public
NVIDIA/DLSS commit `9981c6350dc58c0ce21f024fd65e31e851c31689`; that SDK build does
not provide or validate any of the external neural candidates above.
