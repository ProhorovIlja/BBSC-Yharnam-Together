# Corrected native startup: first 98 constructor returns

Continuation: [first 105 returns and class inheritance](NATIVE-STARTUP-105-EVIDENCE.md).

The owner-only Linux x86-64 continuation now returns from constructors 1–98 in
their corrected order. This extends the [1–90 evidence](NATIVE-STARTUP-90-EVIDENCE.md)
using the same pinned owner-supplied decrypted CUSA03173 / 01.09 image. It is an
isolated native startup diagnostic, not an approved retail profile or game boot.

## New execution and state checks

- Registration-pattern constructors 91–93 and 95–97 execute between the existing
  constructor 90 and newly translated constructors 94 and 98. Their ordinal
  positions, original shared registration cells and table identities are retained.
- Constructor 94 inserts the second class record and four further phase records.
  Constructor 98 inserts the third class record and four further phase records.
  The complete three-record class index and twelve-record phase index are checked
  for identity, ownership and sort order; existing entries must remain intact.
- Constructor 98 lazily initializes another parent singleton and performs its
  original tail call into metadata insertion. The new native path allocates a
  128-byte member-record vector, a 136-byte metadata descriptor and a 32-byte
  alias vector, then constructs the descriptor's mutex through the existing host
  pthread adapters. The original metadata initialization/readiness bodies execute.
- Descriptor owner/key/name/length, vector bounds, parent linkage and mutex
  pointer/readiness are checked. Registering the same member again reuses the
  descriptor and owner row and appends the alias, without another allocation or
  mutex initialization. The added comparison import is verified as `memcmp`
  against the pinned image's import identifier before mapping it to the host.
- The original pool, lock, alignment, non-overlap, repeated allocation/free and
  large-allocation regressions continue to run after the new state is verified.

Ten fresh-process repetitions of prefixes 1–89, 1–90, 1–94 and 1–98 passed.
C-shim ASan/UBSan passed with LeakSanitizer disabled due to the environment's
ptrace restriction. Translated assembly is not sanitizer-instrumented.

## Integration with the prepared artifact API

An owner-only developer callback now builds this actual native diagnostic through
`prepared_native.prepare`, rather than using only the developer-owned C fixture:

1. The first request compiles into staging and publishes one host executable.
2. The same selection/dependencies reuse it; the compiler runs once in total.
3. An intentionally failing replacement with a different dependency identity
   leaves the previous current pointer byte-identical.
4. Temporary preparation input, assembly and other build files are deleted before
   `prepared_native.launch` starts that verified executable directly.
5. The executable reaches the 1–98 verification boundary and writes its proof in
   the provided writable user directory. The owner's source image stays unchanged.

This uses an explicit private diagnostic selection, not the reviewed retail
registry, which stays empty. The diagnostic fingerprints its compiler tools and
recipe but does not establish a fully provisioned SDK, header/startup-object or
transitive host-library closure. The asset directory is empty: no assets are
loaded by this startup prefix. This is not a launcher UI or game backend release.

## Limits

The description's factory callback and uncalled virtual methods remain explicit
fail-fast placeholders. Error paths, registry growth/free paths and the large-sort
fallback remain unsupported. A return from these constructors does not certify
those callbacks or any later use of their objects. No unsupported call is changed
into an empty successful return.

OS file/module tracing remains unavailable because ptrace is denied. Removal of
temporary preparation files is narrower evidence than complete runtime access
closure. There is no game entry point, menu, map, asset, gameplay, save, multiplayer,
Windows retail or macOS retail validation and no performance claim. Private
bindings, literal strings and generated retail-derived code remain outside GitHub.
