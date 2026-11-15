# Development continuation

Latest work: branch `development/ultimate-upstream-state-20261115`, stacked on
[PR260](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/260).
Read [source intake](SOURCE-INTAKE-20261115.md), its JSON inventory and the current
branch diff before starting another intake or implementation pass.

Implemented in this checkpoint: shared C++ stream unreliable-payload ownership,
upstream crash-suite placement correction, portable rig process-list path checks,
delay-proxy teardown/FIFO improvements and a reproducible public-ref scanner.
The private Drive report is named
`Bloodborne_Upstream_Intake_Handoff_EN_20261115.txt`; its accompanying validation
ZIP includes full ref snapshots and reproduction/test logs. These files are in
the existing private research/diagnostics folders. They contain no game assets.

The native startup diagnostic remains at **132 original constructor returns**,
eleven classes/44 phase rows/five metadata objects. Continue at constructor133;
see [evidence](NATIVE-STARTUP-132-EVIDENCE.md). The owner-only reproducer archive
`Bloodborne_Private_Native132_Owner_Reproducer_20261115.zip` is in private Drive.
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
