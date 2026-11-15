# Compare the candidate to the baseline

Run from a Linux test host, not the public shard. Build two shadNet executables
with the same compiler/options, and use one bbload binary for both. The runner
uses loopback and creates a fresh server home per sample.

```sh
python3 server/loadtest/compare_load.py \
  --baseline /path/to/upstream/shadnet --candidate /path/to/candidate/shadnet \
  --bbload /path/to/bbload --output /path/to/new-results-dir \
  --players 60 --team-size 3 --seconds 30 --pairs 3
```

Keep the raw outputs and both exact source SHAs. The tool records binary hashes,
alternates A/B then B/A, and rejects failed workers, missing traffic, missing resource
samples and runs where not all scheduled players played. It records RSS peak per run,
main-thread and process CPU, and latency/loss. The relay p99 from run_load is the
worst worker's p99, not a percentile pooled across workers. UDP buffer drops are
host-wide; keep other traffic and jobs off the test host. Shared runner variance is
not a game performance result.

Separately run client captures on identical hardware, resolution, graphics settings,
save clones, and scene. Record cold cache and warm cache separately; don't mix
capture lengths or title/menu frames into an area benchmark. `bbport/tools/bench.sh`
is the existing Linux scene harness; it now keeps each run's CSV and log together.
Windows build logs are build evidence only, not a runtime benchmark or installer.

The PR server image build additionally runs a six-player loopback smoke, using the
same built shadNet and bbload binaries. It is a functional join/traffic gate, not an
A/B benchmark or retail-game validation. No ports are published and the image is
not pushed from a pull request.
