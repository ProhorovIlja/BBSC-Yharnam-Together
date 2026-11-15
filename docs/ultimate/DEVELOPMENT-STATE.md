# Development continuation

Latest work: branch `development/ultimate-aot-native136-20261115`, stacked on
[PR 261](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/261).
Read [recompiler intake](RECOMPILER-INTAKE-20261115.md) and the current branch diff.
Earlier [source intake](SOURCE-INTAKE-20261115.md) retains the C++ stream and rig
changes; its infrastructure/image CI43725362583 has now succeeded too.

This checkpoint adds a pinned Linux external-recompiler probe using 20 synthetic
instructions and 1,000 randomized states each, separate from the owner startup test.
The source watchlist expands to 39 repositories; full snapshots and exact test logs
are in the private research/diagnostics folders, without game assets in GitHub.
The private Drive handoff is `Bloodborne_Recompiler_Native136_Handoff_EN_20261115.txt`.

The native startup diagnostic reaches **136 original constructor returns**,
twelve classes/48 phase rows/six metadata objects. Continue at constructor 137;
see [evidence](NATIVE-STARTUP-136-EVIDENCE.md). The owner-only reproducer archive
`Bloodborne_Private_Native136_Owner_Reproducer_20261115.zip` is in private Drive.
No approved playable no-eboot profile, game-main/assets/gameplay proof, native
Windows/macOS retail execution or complete toolchain/SDK closure is established.

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
