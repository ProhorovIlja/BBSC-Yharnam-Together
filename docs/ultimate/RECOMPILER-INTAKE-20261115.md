# Static recompiler intake and native136

## Sources and actual scope

Pin [bloodborne-native/bloodborne-recomp](https://github.com/bloodborne-native/bloodborne-recomp)
at `c60ccf8be752b8690f2813505c4daf9eafdb136b` and
[bbcpu](https://github.com/bloodborne-native/bbcpu) at
`3f9b6c1a11d5a443ee2e556a0d1f3aec4a73f0ca`. Their generator, interpreter and
differential fuzzer are GPL-2.0-or-later external source; built on bbport and
shadPS4 as their project credits describe. No donor source is vendored/modified
and no game code or runtime backend is imported by this checkpoint.

This is a concrete candidate beyond translating each startup function manually:
its generator emits C and its scanner follows unwind/control-flow/pointer data.
The donor runtime still handles guest memory, system calls and fallback execution.
Its published game coverage/performance figures are donor claims, not our results,
and do not satisfy our complete no-eboot/native-runtime acceptance contract.

## Implemented Linux tool probe

`tools/ultimate/recompiler_probe.py` verifies clean, exact source revisions and
matching recompiler API 4, then builds the external scanner, generator and bbcpu.
It uses 20 synthetic integer/memory encodings authored for this probe, with no game
image. The generator emits C for all 20; a native Linux shared library is compiled
and the donor's differential fuzzer checks it against the interpreter for 1,000
randomized states per encoding. Local result: 20 tested, 0 failed, 0 crashed, 0 skipped.
The example host also reports `guest returned 42`. This is 20,000 synthetic states,
not game instruction coverage, full function replays, floating-point validation,
ARM64/JIT testing or production integration.

The actual adapter requirements were established by building:

* The provided build defaults to clang, unavailable in this environment. Use GCC
  through `recompiler-linux-gcc.sh`, scoped explicitly to Linux x86-64 research.
* bbcpu's public header otherwise exposes non-Apple stubs; explicitly request the
  real implementation with `BB_HAVE_BBCPU`, without pretending to be Apple.
* Use isolated Zydis v4.1.1, source
  `a2278f1d254e492f6a6b39f6cb5d1f5d515659dc`, and its pinned Zycore submodule
  `0b2432ced0884fd152b471d97ecf0258ff4d859f`. The renderer's existing decoder prefix
  lacks the displacement field expected by this donor; do not change the renderer
  dependency to force compatibility. The probe pins actual header bytes because
  the v4.1.1 public version macro still encodes4.1.0.
* Link Linux math/dynamic-loader/pthread/atomic support; libatomic supplies the
  16-byte compare-exchange helper. Keep strict-aliasing disabled as in donor fuzz
  builds. The adapter downgrades GCC's sign-compare diagnostic from the donor's
  blanket Werror; other warnings remain visible in the build log.

A dedicated Ubuntu CI job builds all three source pins and runs this same probe.
It does not require game files, a GPU, proprietary SDKs or an installed launcher.
Example invocation, after installing the pinned decoder into a separate prefix:

```
python tools/ultimate/recompiler_probe.py --recompiler /path/to/bloodborne-recomp \
  --bbcpu /path/to/bbcpu --deps /path/to/isolated-decoder-prefix \
  --output /path/to/synthetic-results --trials 1000
```

Do not point this probe
at game-derived encodings; its checked-in fixture defines the tested scope.
Evidence records source/API/fixture identities and explicit untested boundaries.

## Independent owner startup work

The existing owner-specific diagnostic advances from 132 to 136 original ordered
constructor returns, with 12 classes/48 phase rows/6 metadata objects and 140 fresh
process runs. See [native 136 evidence](NATIVE-STARTUP-136-EVIDENCE.md). This work is
independent of the donor tool probe: success in either does not prove the other
can launch the full game. The private owner recipe remains in private Drive.

## Source freshness and next engineering boundary

The 34-source repeat scan found no external ref changes since the prior snapshot;
only our new branch/PR 261 appeared. Explicit Internet/GitHub research identified
the CPU/recompiler and related app repositories, expanding the watchlist to 39.
The expanded scan completes with 2,214 branch heads and 5,879 advertised PR heads.
These remain inventories, not semantic review of all refs or of the Internet.

PR 261's formerly pending infrastructure/image workflow 43725362583 now succeeds,
including container build and startup smoke; its PR path does not publish images.
Preserve that evidence rather than retaining an obsolete pending status.

Next, evaluate guest memory layout, TLS/import/guard and callback ABIs, self-modifying
code exclusions, stable function identification and strict fallback accounting for
an isolated AOT adapter. Unsupported instructions must not disappear into a claimed
fully native profile. Broaden differential tests and real function replays before
touching production game execution; keep game-derived generated code private.
