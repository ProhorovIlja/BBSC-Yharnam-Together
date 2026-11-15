# Development continuation

Latest work: branch `development/ultimate-aot-abi140-20261115`, stacked on
[PR262](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/262).
Read [whole-function AOT boundary](AOT-ABI-20261115.md),
[source intake](AOT-SOURCES-20261115.json) and the current branch diff.

The new synthetic test uses the real pinned full-function C generator and tests
calls, returns, tail calls, TCB loads and host callbacks/reentry in 14,000 cases.
Normal paths never reach the interpreter; unsupported instructions and unknown
call targets are terminal. Local ASan/UBSan also passes, leak checks disabled.
This is an independent test host, not a production AOT dispatcher or Win64 bridge.

The source watchlist now targets45 repositories:44 inventory successfully,
2,398 branch heads and6,070 advertised PR heads. The historical
lud-berthe/Bloodborne-Recompiled source is inaccessible and explicitly unreviewed.
Existing external tracked refs did not change during the repeat scans. These
counts are inventories, not a review of all refs, forks, GitHub or the Internet.
Selected V395/V401 and V392 work in the owner's other repo informed the new
boundary tests; Android/Niels/other Windows variants remain scoped references.

The private startup diagnostic now reaches **140 original ordered constructor
returns**, thirteen classes/52 phase rows/six metadata objects. Fifteen prefix
modes each pass ten fresh processes. See [evidence](NATIVE-STARTUP-140-EVIDENCE.md).
The owner reproducer and exact validation snapshots/logs are in private Drive;
English handoff: `Bloodborne_AOT_ABI_Native140_Handoff_EN_20261115.txt`.
Continue at constructor141. No approved playable no-eboot profile, game-main,
assets/gameplay, native Windows/macOS retail execution or complete SDK/toolchain
closure has been established.

Community neural rendering remains a candidate track, not an enabled backend:
[pinned investigation](NEURAL-RENDERING-CANDIDATES-20261115.md). RT/PT candidates,
existing ray-query AO and language choices are documented in the source intake.

Next: inspect changed refs against the saved snapshot, verify actual source/ABI
and licensing for a selected candidate, reproduce the current defect, adapt in an
isolated development branch and record tests and outstanding game/device checks.
Retain the extra personal-world write-failure protections when comparing upstream.
Do not describe a ref inventory, a donor's measurements or a CPU build as our own
game acceptance. Current source coverage is scoped, and all remaining bugs and
improvement requests have not been certified resolved.
