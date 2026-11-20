# Comparing ShadNet relay builds locally

Run on one idle Linux machine with Python 3.11+, using the same current bbload
binary and equivalent build flags/libraries for both servers. Use a baseline
that accepts the simulator's protocol and checked local build fingerprint.

    python3 server/loadtest/compare_relay.py --base /path/to/base/shadnet \
        --candidate /path/to/candidate/shadnet --bbload /path/to/bbload > relay-ab.json

The runner starts fresh local servers, runs the strict two- and five-hunter
workloads serially, and reverses the A/B order each trial. It records the
binary hashes, raw workload summaries, and median paired candidate-minus-base
differences. A missing directed teammate route, refusal, or socket write
failure invalidates a run. The relay percentiles are maxima of worker
percentiles, not pooled percentiles. Compare paired raw runs as well as the
medians; there is no automatic performance pass.

For instrumented builds, use run_load.py with --collect-admin-timing and
the same hosted settings for both servers. This reads only allowlisted
counters from a private socket after the workload. Use fresh processes:
tick gap maxima cannot be subtracted to produce an interval maximum.
A candidate with timing instrumentation cannot be compared on those metrics
against an uninstrumented baseline. Keep clean-loopback results separate
from packet-impairment results. Do not change production interfaces or run
these synthetic clients against production. These are not retail game tests.

Strict runs require every simulated hunter in play continuously for the requested
duration, in each worker. The join allowance is separate from that duration.
The report records the shortest completed all-playing window across workers.
Latency and CPU aggregates still include some startup observations; do not
interpret those aggregates as precisely timestamp-aligned steady-state metrics.

Use `compare_relay.py --hosted-timing` to collect the same private timing
schema from both sides. In this mode both binaries must have timing
instrumentation. Fresh local test configurations disable signup proof-of-work
so it does not dominate comparisons; this is not a production setting.
The hosted container test also requires real observed link and world ticks
after a full five-hunter loopback run. Timing maxima include startup.

Strict smoke also requires a usable packet from each directed teammate route
in the final two seconds. Startup traffic alone cannot hide a route that
goes silent later. This is a liveness check, not a latency target.

The isolated relay comparison workflow builds the PR base and head with the
same Docker build recipe and separate compile caches, then runs both with one
simulator in a container without external networking. It records Git revisions,
binary hashes, raw trials and paired deltas in the Actions artifact. Its two
repetitions are a CI comparison, not a release threshold. The baseline has no
private timing instrumentation, so this workflow does not compare admin tick
counters; use two instrumented binaries for that comparison.
