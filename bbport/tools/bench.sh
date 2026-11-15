#!/usr/bin/env bash
# tools/bench.sh NAME [ENV=VALUE...]: starts the game through tools/restart.sh (title: cross,
# cross; waits for the level), stands still there for ${HOLD:-60} s, then closes it. The log is
# a unique out/bench_NAME_*/ directory with capture.log and capture.frames.csv.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
name=${1:?usage: tools/bench.sh NAME [ENV=VALUE...]}
shift
[[ $name =~ ^[A-Za-z0-9_-]+$ ]] || { echo 'Invalid benchmark name' >&2; exit 2; }
[[ ${HOLD:-60} =~ ^[1-9][0-9]*$ ]] || { echo 'HOLD must be positive seconds' >&2; exit 2; }
mkdir -p out
run_dir=$(mktemp -d "out/bench_${name}_$(date +%Y%m%d_%H%M%S).XXXXXX")
base=$run_dir/capture
env BB_GAME_DIR="${BB_GAME_DIR:-$PWD/../game_files/CUSA03173}" "$@" FORCE_RESTART=0 BB_FRAME_LOG="$PWD/$base.frames.csv" \
    tools/restart.sh > /dev/null || exit 1
finish() {
    tools/stop_own.sh || true
    cp out/session.log "$base.log" || true
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
sleep "${HOLD:-60}"
if [[ ! -s "$base.frames.csv" ]]; then
    echo "No frame CSV collected; diagnostic log: $base.log" >&2
    exit 1
fi
printf '%s\n' "$base.frames.csv" "$base.log"
