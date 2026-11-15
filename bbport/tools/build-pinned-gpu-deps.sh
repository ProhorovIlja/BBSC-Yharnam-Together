#!/usr/bin/env bash
# Build the repository-pinned CMake dependencies into a user-writable prefix.
# SDL3, Abseil, FFmpeg, protobuf, X11, OpenSSL, zlib and xxHash remain host dependencies.
set -euo pipefail
if [[ $# != 1 ]]; then
    echo "Usage: bash tools/build-pinned-gpu-deps.sh /absolute/install/prefix" >&2
    exit 2
fi
case $1 in /*) ;; *) echo 'The install prefix must be absolute.' >&2; exit 2 ;; esac
prefix=$1
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
build_root=${BB_DEP_BUILD_DIR:-"$prefix/build"}
jobs=${CMAKE_BUILD_PARALLEL_LEVEL:-2}
if [[ ! $jobs =~ ^[1-9][0-9]*$ ]]; then
    echo 'CMAKE_BUILD_PARALLEL_LEVEL must be a positive integer.' >&2
    exit 2
fi
for source in emulator/externals/fmt emulator/externals/robin-map \
    emulator/externals/zydis emulator/externals/zydis/dependencies/zycore \
    emulator/externals/glslang emulator/externals/ext-boost \
    bbport/gpu/third_party/vulkan-headers; do
    if [[ ! -f "$repo/$source/CMakeLists.txt" ]]; then
        echo "Missing $source; initialize the pinned submodules first (see docs/BUILD-LINUX.md)." >&2
        exit 1
    fi
done
build_dependency() {
    local name=$1 source=$2
    shift 2
    cmake -S "$repo/$source" -B "$build_root/$name" \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
        -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_PREFIX_PATH="$prefix" "$@"
    cmake --build "$build_root/$name" --parallel "$jobs"
    cmake --install "$build_root/$name"
}
build_dependency vulkan-headers bbport/gpu/third_party/vulkan-headers \
    -DVULKAN_HEADERS_ENABLE_TESTS=OFF -DVULKAN_HEADERS_ENABLE_MODULE=OFF
build_dependency fmt emulator/externals/fmt -DFMT_TEST=OFF -DFMT_DOC=OFF -DFMT_INSTALL=ON
build_dependency robin-map emulator/externals/robin-map
# Zydis' installed config needs Zycore's package config as well as its archive.
build_dependency zycore emulator/externals/zydis/dependencies/zycore \
    -DZYCORE_BUILD_TESTS=OFF -DZYCORE_BUILD_EXAMPLES=OFF
build_dependency zydis emulator/externals/zydis \
    -DZYDIS_BUILD_TOOLS=OFF -DZYDIS_BUILD_EXAMPLES=OFF \
    -DZYDIS_BUILD_DOXYGEN=OFF -DZYDIS_BUILD_MAN=OFF
# Current host shaders do not request glslang's optional SPIRV-Tools optimizer.
# This builds the real GLSL/SPIR-V compiler, without fetching another toolchain.
build_dependency glslang emulator/externals/glslang \
    -DENABLE_OPT=OFF -DENABLE_HLSL=OFF -DGLSLANG_TESTS=OFF -DENABLE_GLSLANG_BINARIES=ON
echo "Pinned GPU dependencies installed in $prefix"
echo 'Use this prefix in CMAKE_PREFIX_PATH and its bin directory in PATH.'
echo 'Select the pinned header-only Boost with BB_USE_BUNDLED_BOOST=ON.'
