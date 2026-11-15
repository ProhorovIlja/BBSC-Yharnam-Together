# Linux GPU build dependencies

The GPU library and the loader need a C++23 compiler, CMake 3.24 or newer,
Ninja, pkg-config, a C11 compiler and a matching host development SDK. Building
the library alone is not proof that the loader links or that a game boots.

Required host development packages provide a Vulkan loader, SDL3, X11,
xxHash, Abseil (with its CMake config), FFmpeg (avformat, avcodec, avutil,
swscale, swresample), protobuf and
protoc, nlohmann_json, OpenSSL and zlib. Use packages matching the host's ABI;
do not replace its libc or dynamic loader with an extracted SDK.

## Pinned CMake dependencies

From the repository root, initialize the recorded revisions:

```bash
git submodule update --init --recursive --jobs 3 \
  emulator/externals/fmt emulator/externals/ext-boost \
  emulator/externals/robin-map emulator/externals/zydis \
  emulator/externals/glslang bbport/gpu/third_party/vulkan-headers \
  emulator/externals/vma bbport/gpu/third_party/fsr-vulkan \
  bbport/gpu/third_party/imgui bbport/gpu/third_party/magic_enum \
  bbport/gpu/third_party/miniz bbport/gpu/third_party/xbyak \
  bbport/third_party/LibAtrac9
```

Then, from `bbport`, install the pinned compiled dependencies into a writable
prefix. The helper uses the existing submodule revisions and does not install
system packages. Static archives are built with PIC because they enter
`libbbgpu.so`. Zycore is installed separately: Zydis' installed package needs
its CMake configuration too.

```bash
bash tools/build-pinned-gpu-deps.sh /absolute/path/to/bb-deps
export CMAKE_PREFIX_PATH="/absolute/path/to/bb-deps${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
export PATH="/absolute/path/to/bb-deps/bin:$PATH"
BB_USE_BUNDLED_BOOST=ON BB_LTO=OFF bash build.sh
```

`BB_USE_BUNDLED_BOOST` defaults to `OFF`, retaining system Boost discovery.
When enabled it uses the pinned submodule's `Boost::headers` target, including
the nested library include directories; adding only its root include path is
insufficient. Initialize that submodule explicitly even if other GPU
submodules already exist.

The GPU has its own Vulkan-Headers pin, v1.4.347 at
`387259ecf4b0fe0cfac161b1d0b0a74e42796710`. The helper installs it into the
prefix. GPU configuration requires headers 1.4.347 or newer because the FSR
4.1.1 capability checks use `VK_VALVE_shader_mixed_float_dot_product`. The
emulator's separate 1.4.330 pin does not provide that C/Hpp declaration. Do not
silently remove that upscaler path to make old headers compile. This build-time
minimum does not require Vulkan 1.4.347 device support; runtime feature checks
still decide which paths a driver can execute.

The helper builds glslang without its optional SPIRV-Tools optimizer and HLSL
frontend. It still compiles the current GLSL host shaders to SPIR-V. This
configuration is for build validation, not evidence of optimal shader output
or runtime performance. A shader requiring optimizer flags needs a matching
optimizer-enabled toolchain.

`build.sh` applies the tracked FSR-Vulkan patches before configuring. When
calling CMake directly, apply those patches first, as described in
`gpu/patches/fsr-vulkan/README.md`, and provide host SDK search paths. Pinned
Vulkan/VMA headers can be selected with `Vulkan_INCLUDE_DIR` and
`VMA_INCLUDE_DIR`; the Vulkan loader must match the execution environment.

## Validate each stage separately

Record configure/build failures, exact dependency revisions and any changes
to compiler flags. First build `bbgpu`, then link `bb-probe` through `build.sh`.
Check dynamic dependency resolution and GPU capabilities before attempting a
game. Do not treat `--allow-shlib-undefined` on the shared library as a complete
loader link. The expected `runtime_*` imports must resolve against the loader.

A headless machine can validate compilation and CPU tests. It cannot establish
presentation correctness, gameplay, audio-device behavior, frame pacing,
upscaler quality or macOS/Windows compatibility. LTO/PGO-disabled build
validation is not a performance comparison.
