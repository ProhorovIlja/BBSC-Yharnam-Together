# Corrected native startup: first 105 constructor returns

The owner-only Linux x86-64 diagnostic now returns from constructors 1–105 in
their corrected order, continuing the [1–98 result](NATIVE-STARTUP-98-EVIDENCE.md)
with the same pinned owner-provided CUSA03173 / 01.09 reference image.

Constructors 99–104 execute their exact matched registration bodies and preserve
the existing shared cells/table identities. Constructor 105 executes its compound
initialization body, inserts two additional class records and eight phase records,
then establishes a derived-class → base-class → root-parent chain. These two type
initializations are counted as one constructor ordinal, not two extra returns.

Checks cover every one of the five class records and twenty phase records,
including identity, key/name/length, ownership, sort order, guards, allocator
association and the new inheritance chain. Both new member vectors remain empty
as expected. The descriptor, aliases and mutex created by constructor 98 remain
intact, and the previous pool/alignment/allocation/free/lock regressions still run.
Uncalled virtual methods and the description factory remain fail-fast placeholders.

The prepared-entry integration builds the actual prefix-105 executable once,
verifies cache reuse and failed-replacement preservation, removes temporary build
inputs and launches that verified executable directly. Its writable-user output
contains a strict return journal with ordinals 1–105 exactly once and in order.
The owner's source image stays unchanged. This private diagnostic selection is
not a reviewed playable profile; the public retail registry remains empty.

The launch API also now rejects equal or nested cache, asset and writable-user
roots before creating user data or starting a process. A regression test first
reproduced writes being directed into the prepared bundle and source asset tree.
The fix checks resolved paths and filesystem identities, including case aliases
on case-insensitive volumes. This is configuration validation, not a write sandbox
for arbitrary native machine code.

Native validation: ten fresh-process repetitions of each supported prefix
(1–89, 1–90, 1–94, 1–98 and 1–105), C-shim ASan/UBSan with LeakSanitizer disabled
because ptrace is denied, and the actual prepared-cache integration. Translated
assembly is not sanitizer-instrumented. No successful OS file/module trace or
complete provisioned SDK/transitive-library closure is available.

There is still no game entry point, asset loading, menu, map, saving, gameplay,
multiplayer, Windows retail or macOS retail proof. Unsupported imports/error
paths, registry growth/free and large-sort fallback remain terminal. No game
performance claim follows from these diagnostics. Image-specific bindings and
retail-derived assembly/literals stay out of GitHub.
