# Corrected native startup: first 90 constructor returns

Continuation: [first 98 returns and prepared-cache integration](NATIVE-STARTUP-98-EVIDENCE.md).

On 2026-11-14, the owner-provided decrypted 1.09 reference image and private V446
reproducer were checked locally. The image matched the reproducer's pinned hash
and the separate SFO identified CUSA03173 / 01.09. No retail profile was approved.

The existing reproducer independently passed the corrected ordered prefix 1–89
and its constructor-90 pool/registry checkpoint using GCC on Linux x86-64.
The historical claim of 1,088 constructor returns is not this corrected prefix.

An owner-only extension now executes through the return from constructor 90 in
the same process as constructors 1–89. It extends the translated registry
insertion routine, secondary registry initialization, four original phase-address
getters and the native sort body. It checks:

- The first registry's allocated 16 KiB storage and one complete 32-byte record:
  object, original key/name identities and key length.
- The second registry's allocated 8 KiB storage and four complete 16-byte records,
  sorted by phase address, all pointing to the original registration object.
- The parent singleton relationship, existing pool publication/vector state,
  mutex/rwlock lifecycle and allocation/free regression checks.
- The actual constructor return before the C verification boundary is called.

Ten fresh-process repetitions of each prefix passed. ASan/UBSan passed for the
C shim with LeakSanitizer disabled because this environment denies ptrace.
The translated assembly itself is not sanitizer-instrumented. A separate run
passed with an empty environment, a separate run directory and the preparation
image unavailable at its original path. The host executable's declared direct
dependencies were `libstdc++.so.6` and `libc.so.6`.

`strace` could not run: the cloud environment denied `PTRACE_TRACEME` and
`PTRACE_SETOPTIONS`. Therefore there is no successful OS file/module trace and
no claim of complete runtime access closure. A successful isolated run does not
establish that all possible execution paths avoid original console code.

The extension remains an image-pinned diagnostic reconstruction. Unsupported
imports, error paths, registry growth/free paths and the large-sort fallback
trap; they do not silently succeed. Earlier registration bodies still use
placeholder virtual methods and identity-preserving reconstructed tables from
V446. No game entry point, assets, menu, map, save, gameplay, Windows retail
execution, macOS retail execution or multiplayer was exercised. This is not a
playable native port, and it is not a production client integration.

Retail-derived assembly, original literals, image-specific bindings and game
bytes are kept out of this repository. The owner-only source reproducer and
verification evidence are retained privately with the project handoff.

Next native gate: preserve this corrected prefix, audit constructor 91 and its
dependencies, replace remaining diagnostic-only virtual methods as reached,
then obtain an OS file/module trace on a capable host. Do not turn the reviewed
retail registry into a supported-game list based on this result.
