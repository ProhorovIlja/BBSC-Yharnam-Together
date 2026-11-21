# Defer guest world application when its backup cannot be written

Follow-up to PR #250, based on `9ab747587569ebaa11a947090650e2ae9d617163`.

A Linux fault-injection process limited only its own regular-file writes to zero
bytes (`RLIMIT_FSIZE`, with `SIGXFSZ` ignored). The actual production load function
still applied the visited world's flags, published a zero-byte personal backup
and marked the team world taken. This is an additional failure beyond upstream
PR #592's normal-load ordering fix.

`WriteWholeFile` now reports success only after open, write, flush, close and
rename succeed. A failed write is not renamed over an existing complete backup.
`KeepOwnWorldAside` propagates failures, rejects an existing unreadable/malformed
backup, and checks creation of the home-world list. Both guest entry paths return
before changing team lamps or world flags when their personal backup is not ready.
The state remains eligible for a later retry. A read failure returns unreadable
data to the parser instead of throwing out of the load function.

The production-source fixture now has ten scenarios. Four additional scenarios
test failed initial backup followed by recovery/retry, failure before an uncreated
world, malformed/unreadable backup paths, and a failed extension preserving the
previous complete backup. They use real temporary paths and file operations, with
no real save or game bytes. The previous six world scenarios, four shared-link
scenarios and twelve existing GameLink tests remain in the suite.

The local zero-byte-write injection is repeated against the corrected production
functions. This covers a real stream write/flush failure, separately from the
portable fixture's blocked-open paths. These checks are narrower than power-loss
durability or full save transactional acceptance. `flush`/`close` do not provide
filesystem directory/file fsync guarantees. Other callers that ignore the writer's
result and restore/home-world metadata failure handling need further work. No
general save-loss-prevention or real-game acceptance claim follows from this patch.

The upstream source files were byte-identical at PR #250. This follow-up intentionally
extends that implementation locally; it must not be described as unmodified upstream.

Integration: independently backported onto current playable `main` in PR #307; this is the same runtime source blob as the 2026-11-15 candidate, not a retail save test.
