# Ultimate B10: keep a failed native build observable without another full rebuild

**Build tooling fix on top of B09 / PR #41. No game client source, network code or gameplay semantics changed.**

## Verified shell defect

The 1.4.0-derived `bbport/build.sh` uses `set -euo pipefail`. In *both* Windows three-EXE and Linux `bbgpu` Ninja failure branches, it ran:

`grep -v '^\\[' out/gpu-build.log | tail -40 >&2`

When Ninja prints only progress lines (for example `[432/433] Linking ...` without the expected `FAILED:`), `grep` returns 1. Under `pipefail` this stops the script **before** its explicit `Build failed` message. This explains why the wrapper can give a silent failure, not *why* Ninja returned nonzero in the first place.

## B10 change

One `report_bbport_build_failure` function records an explicit failed component, the first eight matching compiler/linker diagnostics, the last twelve nonprogress log lines with a 600-character cap per line, or a clear message when no compiler diagnostic exists. All reporting pipelines are guarded and return successfully so that the calling Windows/Linux Ninja failure block **always** exits 1 with its own marker.

`tools/ultimate/test_batch_10_build_failure.py` executes the production shell function extracted from the actual `bbport/build.sh`. Synthetic logs test progress-only output with pipefail, a failed Ninja command, an absent log file and more than eight huge linker error lines. The dedicated source workflow checks the **five-file** scope and pins the actual source/test Git blobs before running tests. No full Windows game build is launched by B10.

## Related independent Windows compilation work

[Draft #31](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/31) remains a separate **full Windows compiler** gate. Its most recent run is the direct Ninja `-j 2` investigation; its CI changes have not yet been integrated into this cumulative B10 branch. The older [successful YT1.3 original Windows CI 41051781140](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41051781140) used `-j 2`, `-O2 -g0` and bounded CCache and is an evidence-backed low-RAM recipe for possible comparison, **not proof of the current root cause**.

B10 protects diagnostic fidelity. It cannot establish actual native Windows 1.4.0 build success, real 2/3/5-player Link4, the integrity of private Bloodborne saves, performance gains, game physics or Fornex deployment. The entire Ultimate B01–B10 branch remains Draft-only, no public launcher/installer created.
