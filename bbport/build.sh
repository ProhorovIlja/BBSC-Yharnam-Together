#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
mkdir -p out
# Keep failed Ninja jobs diagnosable even when their log has only "[N/M]"
# progress lines (e.g. a linker killed by Windows memory pressure). With
# set -euo pipefail, an unguarded grep returning 1 used to abort this script
# *before* it could print the build-failed marker.
report_bbport_build_failure() {
    local description="$1" logfile="$2"
    echo "BBPORT_NATIVE_BUILD_FAILURE: $description" >&2
    if [[ -f "$logfile" ]]; then
        echo 'FIRST_COMPILER_OR_LINKER_ERRORS_MAX_8:' >&2
        awk '
            /(^FAILED:|error:|fatal error:|undefined symbol|undefined reference|ninja: build stopped|[Kk]illed|out of memory|[Ss]ignal [0-9])/ && matched < 8 {
                matched++
                print substr($0, 1, 600)
            }
            END { if (matched == 0) print "NO_COMPILER_DIAGNOSTIC_IN_LOG" }
        ' "$logfile" >&2 || true
        echo 'NONPROGRESS_LOG_TAIL_MAX_12:' >&2
        grep -v '^\[' "$logfile" | tail -n 12 | cut -c 1-600 >&2 || true
    else
        echo 'BUILD_LOG_MISSING' >&2
    fi
    echo "Full local runner log: $logfile" >&2
    return 0
}

# Kaniel 2026-11-04: BB_PRODUCTION=1 (make-release.ps1) builds a release: no cheats, save editor,
# debug menu or camera, or autoplay (CMake BB_PRODUCTION). Always passed, so a dev build after a
# release build is a dev build again. out/build-mode.txt says which this is (make-release checks it).
if [[ ${BB_PRODUCTION:-0} == 1 ]]; then production=ON; build_mode=production; else production=OFF; build_mode=dev; fi
# Windows: MSYS2 CLANG64 (packages in packaging/windows/README.md). The GPU library is static
# there and CMake links bb-probe.exe as well; no PGO (GCC-only flags), LTO off by default.
case $(uname -s) in
MINGW*|MSYS*)
    # On Windows a linker may finish before the executable can be copied, or
    # a later shell operation can fail under set -e without a useful message.
    # Record the *actual* finalization phase on every nonzero shell exit.
    bbsc_win_phase=environment
    trap 'bbsc_win_rc=$?; if (( bbsc_win_rc != 0 )); then echo "WINDOWS_NATIVE_EXIT_PHASE: ${bbsc_win_phase} rc=${bbsc_win_rc}" >&2; fi' EXIT
    # shellcheck source=msys2-env.sh
    source ./msys2-env.sh
    for tool in clang cmake ninja pkg-config; do
        command -v "$tool" >/dev/null || { echo "Need $tool from MSYS2 CLANG64 (packaging/windows/README.md)." >&2; exit 1; }
    done
    if [[ ! -f gpu/third_party/fsr-vulkan/CMakeLists.txt || ! -f gpu/third_party/imgui/imgui.h ||
          ! -f gpu/third_party/xbyak/xbyak/xbyak.h ]]; then
        git submodule update --init --recursive
    fi
    for patch in gpu/patches/fsr-vulkan/*.patch; do
        if ! git -C gpu/third_party/fsr-vulkan apply --reverse --check "$PWD/$patch" 2>/dev/null; then
            git -C gpu/third_party/fsr-vulkan apply "$PWD/$patch"
        fi
    done
    # CI / RAM-limited Windows runners can avoid generating huge DWARF/PDB inputs.
    # Keep the same -O2 optimization as RelWithDebInfo; opt-in leaves ordinary
    # developers' debuggable builds unchanged. Proven in the older YT 1.3 CI.
    windows_cmake_flags=()
    if [[ ${BB_WINDOWS_NO_DEBUG_SYMBOLS:-0} == 1 ]]; then
        windows_cmake_flags=(
            '-DCMAKE_C_FLAGS_RELWITHDEBINFO=-O2 -g0 -DNDEBUG'
            '-DCMAKE_CXX_FLAGS_RELWITHDEBINFO=-O2 -g0 -DNDEBUG'
        )
        echo 'Windows low-memory build: RelWithDebInfo optimization -O2, debug symbols disabled'
    fi
    # CMAKE_BUILD_PARALLEL_LEVEL does NOT affect direct Ninja invocation.
    # Require an explicit, bounded positive job count when one is configured.
    windows_ninja_args=()
    if [[ -n ${BB_BUILD_JOBS:-} ]]; then
        if [[ ! ${BB_BUILD_JOBS} =~ ^[1-9][0-9]?$ ]] || (( BB_BUILD_JOBS > 32 )); then
            echo 'BB_BUILD_JOBS must be an integer from 1 to 32' >&2
            exit 2
        fi
        windows_ninja_args=(-j "$BB_BUILD_JOBS")
    fi
    cmake -S gpu -B out/gpu -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBB_PGO=off \
        -DBB_LTO="${BB_LTO:-OFF}" -DBB_PRODUCTION="$production" -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ "${windows_cmake_flags[@]}" >/dev/null
    echo "GPU library and loader: LTO ${BB_LTO:-OFF}"
    # CLANG64 CI has repeatedly stopped silently near the last bbnet/archive/link
    # work of a 433-task mixed build, while the remaining five jobs linked on a
    # second Ninja invocation. Separating net, GPU and EXE stages prevents both
    # heavyweight library build and final links from competing for runner memory.
    # Opt-in: normal developer builds retain their original single Ninja call.
    if [[ ${BB_WINDOWS_STAGED_LINK:-0} == 1 ]]; then
        : > out/gpu-build.log
        for stage in net gpu final; do
            case "$stage" in
                net)   windows_targets=(bbnet) ;;
                gpu)   windows_targets=(bbgpu) ;;
                final) windows_targets=(bb-probe bb-gpu-capabilities bb-play) ;;
            esac
            bbsc_win_phase="ninja-$stage"
            echo "WINDOWS_NINJA_STAGE_BEGIN: $stage"
            if ninja "${windows_ninja_args[@]}" -C out/gpu "${windows_targets[@]}" >> out/gpu-build.log 2>&1; then
                echo "WINDOWS_NINJA_STAGE_PASS: $stage"
            else
                windows_ninja_rc=$?
                echo "WINDOWS_NINJA_STAGE_FAILED: $stage rc=$windows_ninja_rc" >&2
                report_bbport_build_failure "Windows $stage stage" out/gpu-build.log
                exit "$windows_ninja_rc"
            fi
        done
    else
        if ! ninja "${windows_ninja_args[@]}" -C out/gpu bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1; then
            report_bbport_build_failure 'Windows client/GPU/play targets' out/gpu-build.log
            exit 1
        fi
    fi
    bbsc_win_phase=validate-native-outputs
    echo 'WINDOWS_NATIVE_FINALIZATION_BEGIN'
    for exe in bb-probe.exe bb-gpu-capabilities.exe bb-play.exe; do
        if [[ ! -s "out/gpu/$exe" ]]; then
            echo "WINDOWS_NATIVE_TARGET_MISSING_OR_EMPTY: $exe" >&2
            exit 46
        fi
        printf 'WINDOWS_NATIVE_TARGET_READY: %s (nonempty)\n' "$exe"
    done
    bbsc_win_phase=copy-native-outputs
    echo 'WINDOWS_NATIVE_COPY_BEGIN'
    # MSYS2 CLANG64 does not guarantee coreutils cp/wc/cmp on minimal runners.
    # CMake is mandatory earlier in this *same* build and its -E commands
    # work identically on Windows and Linux. Avoid an undeclared dependency.
    if cmake -E copy_if_different \
        out/gpu/bb-probe.exe out/gpu/bb-gpu-capabilities.exe \
        out/gpu/bb-play.exe out/; then
        echo 'WINDOWS_NATIVE_COPY_COMMAND_PASS'
    else
        windows_copy_rc=$?
        echo "WINDOWS_NATIVE_COPY_FAILED: rc=$windows_copy_rc" >&2
        exit "$windows_copy_rc"
    fi
    bbsc_win_phase=verify-copied-outputs
    for exe in bb-probe.exe bb-gpu-capabilities.exe bb-play.exe; do
        if ! cmake -E compare_files "out/gpu/$exe" "out/$exe"; then
            echo "WINDOWS_NATIVE_COPIED_OUTPUT_MISMATCH: $exe" >&2
            exit 47
        fi
    done
    echo 'WINDOWS_NATIVE_COPY_IDENTITY_PASS'
    bbsc_win_phase=write-build-mode
    echo "$build_mode" > out/build-mode.txt
    echo "WINDOWS_NATIVE_BUILD_MODE: $build_mode"
    echo "Built $PWD/out/bb-probe.exe ($build_mode build)"
    bbsc_win_phase=complete
    exit 0
    ;;
esac
if [[ -z ${CC:-} ]]; then
    CC=$(command -v cc || command -v gcc || true)
    if [[ -z $CC ]]; then
        for candidate in /nix/store/*-gcc-wrapper-*/bin/gcc; do
            if [[ -x $candidate ]]; then CC=$candidate; break; fi
        done
    fi
fi
if [[ -z ${CC:-} ]]; then echo 'Install GCC/Clang or set CC.' >&2; exit 1; fi
# Dependencies come from pkg-config (Vulkan loader/headers, SDL3). On NixOS the
# environment is provided by shell.nix; re-enter it automatically if needed.
if ! { command -v pkg-config >/dev/null && pkg-config --exists vulkan sdl3 && command -v cmake >/dev/null && command -v ninja >/dev/null; }; then
    if [[ -z ${BB_IN_NIX_SHELL:-} ]] && command -v nix-shell >/dev/null; then
        exec env BB_IN_NIX_SHELL=1 nix-shell shell.nix --run "bash build.sh $*"
    fi
    echo 'Need pkg-config with vulkan and sdl3, cmake and ninja (see shell.nix).' >&2; exit 1
fi
read -r -a includes <<< "$(pkg-config --cflags vulkan sdl3)"
read -r -a libraries <<< "$(pkg-config --libs vulkan sdl3)"
# GPU library (shadPS4 video core + drivers), built by CMake into out/gpu/libbbgpu.so.
# BB_PGO: generate (instrumented build that writes pgo/ while the game runs), use, off.
# Default: use the profile in pgo/ when there is one. BB_LTO=OFF disables link-time optimization.
pgo=${BB_PGO:-}
if [[ -z $pgo ]]; then
    if [[ -n $(find pgo -name '*.gcda' -print -quit 2>/dev/null) ]]; then pgo=use; else pgo=off; fi
fi
mkdir -p pgo
# Submodules (git clone --recursive, or: git submodule update --init) and this port's changes
# to FSR-Vulkan (gpu/patches/fsr-vulkan), applied to its working tree once.
if [[ ! -f gpu/third_party/fsr-vulkan/CMakeLists.txt || ! -f gpu/third_party/imgui/imgui.h ]]; then
    git submodule update --init --recursive
fi
for patch in gpu/patches/fsr-vulkan/*.patch; do
    if ! git -C gpu/third_party/fsr-vulkan apply --reverse --check "$PWD/$patch" 2>/dev/null; then
        git -C gpu/third_party/fsr-vulkan apply "$PWD/$patch"
    fi
done
cmake -S gpu -B out/gpu -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBB_PGO="$pgo" \
    -DBB_LTO="${BB_LTO:-ON}" -DBB_PGO_DIR="$PWD/pgo" -DBB_PRODUCTION="$production" >/dev/null
echo "GPU library: PGO $pgo, LTO ${BB_LTO:-ON}"
# A failed GPU build must stop here: an older libbbgpu.so would otherwise be used silently.
if ! ninja -C out/gpu bbgpu > out/gpu-build.log 2>&1; then
    report_bbport_build_failure 'Linux GPU library' out/gpu-build.log
    exit 1
fi
# Optional DLSS (NVIDIA RTX): DLSS_SDK_ROOT=<github.com/NVIDIA/DLSS checkout> builds the bridge
# (gpu/dlss_bridge, the only code using NVIDIA's SDK) and puts it next to bb-probe with NVIDIA's
# libnvidia-ngx-dlss.so. Without them the DLSS upscaler is listed as unavailable.
if [[ -n ${DLSS_SDK_ROOT:-} ]]; then
    cmake -S gpu/dlss_bridge -B out/dlss-bridge -G Ninja -DCMAKE_BUILD_TYPE=Release \
        -DDLSS_SDK_ROOT="$DLSS_SDK_ROOT" >/dev/null
    ninja -C out/dlss-bridge >/dev/null
    rm -f out/libnvidia-ngx-dlss.so.*
    cp out/dlss-bridge/libbbport_dlss.so "$DLSS_SDK_ROOT"/lib/Linux_x86_64/rel/libnvidia-ngx-dlss.so.* out/
    cp "$DLSS_SDK_ROOT/LICENSE.txt" out/NVIDIA-DLSS-LICENSE.txt
    echo "DLSS bridge: out/libbbport_dlss.so"
fi
# $ORIGIN/gpu: packaged copies keep the library next to the binary without patching it.
gpu=(-Lout/gpu -lbbgpu -Wl,-rpath,'$ORIGIN/gpu' -Wl,-rpath,"$PWD/out/gpu" -rdynamic)
runtime=(src/runtime*.c)
# Third-party decoders: compiled once, without this project's -Werror policy.
atrac9=(third_party/LibAtrac9/C/src/*.c)
if [[ ! -f out/libatrac9.a || -n $(find third_party/LibAtrac9/C/src -newer out/libatrac9.a -name '*.c') ]]; then
    rm -rf out/atrac9 && mkdir -p out/atrac9
    for source in "${atrac9[@]}"; do "$CC" -std=c99 -O2 -g -w -c "$source" -o "out/atrac9/$(basename "${source%.c}").o"; done
    ar rcs out/libatrac9.a out/atrac9/*.o
fi
"$CC" -std=c11 -O2 -g -Wall -Wextra -Werror -pthread -no-pie "${includes[@]}" -I. -Isrc src/probe.c "${runtime[@]}" src/vulkan_smoke.c out/libatrac9.a -lm "${gpu[@]}" "${libraries[@]}" -o out/bb-probe
echo "$build_mode" > out/build-mode.txt
echo "Built $PWD/out/bb-probe ($build_mode build)"
# GPU check for run.sh (live_resolution=auto) and the launcher's gamepad list (--gamepads).
"$CC" -std=c11 -O2 -Wall -Wextra -Werror "${includes[@]}" tools/gpu_capabilities.c "${libraries[@]}" -o out/bb-gpu-capabilities
if [[ ${1:-} == --test ]]; then
    "$CC" -std=c11 -O2 -g -Wall -Wextra -Werror -pthread "${includes[@]}" -I. -Isrc tests/test_pad.c -lm "${libraries[@]}" -o out/pad-test
    out/pad-test
    "$CC" -std=c11 -O2 -g -Wall -Wextra -Werror -UNDEBUG -pthread "${includes[@]}" -I. -Isrc tests/test_mouse_camera.c -lm "${libraries[@]}" -o out/mouse-camera-test
    out/mouse-camera-test
    "$CC" -std=c11 -O2 -g -Wall -Wextra -Werror -pthread -I. -Isrc tests/test_runtime.c "${runtime[@]}" out/libatrac9.a -lm "${gpu[@]}" "${libraries[@]}" -o out/runtime-test
    out/runtime-test
    "$CC" -std=c11 -O2 -g -Wall -Wextra -Werror -pthread -I. -Isrc tests/test_file_mods.c -o out/file-mods-test
    out/file-mods-test
    "$CC" -std=c11 -O2 -g -Wall -Wextra -Werror -pthread -I. -Isrc tests/test_sema.c "${runtime[@]}" out/libatrac9.a -lm "${gpu[@]}" "${libraries[@]}" -o out/sema-test
    out/sema-test
    "$CC" -std=c11 -D_GNU_SOURCE -O2 -g -Wall -Wextra -Werror -I. -Isrc tests/test_content.c src/runtime_content.c -o out/content-test
    out/content-test
fi
