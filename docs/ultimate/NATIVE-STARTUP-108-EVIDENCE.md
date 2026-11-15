# Corrected native startup: first 108 constructor returns

The owner-only Linux x86-64 diagnostic now returns from constructors 1–108 in
their exact pinned-image order, extending the previous prefix-105 result.
The three added bodies match the validated registration template. They operate
on shared cells already initialized earlier in the prefix: this adds three
ordered returns, not three new objects, allocations or class records.

The guard behavior is checked by calling each new body again with its published
table temporarily cleared: the ready cell is not initialized a second time.
The table identity is restored before the inherited state checks. The complete
five-class/twenty-phase registry, derived/base/root chain, metadata/alias/mutex
state and previous pool/lock regressions remain checked.

Ten fresh-process repetitions of prefixes 1–89, 1–90, 1–94, 1–98, 1–105 and
1–108 pass. C-shim ASan/UBSan passes with LeakSanitizer disabled. The translated
assembly is not sanitizer-instrumented. The actual prepared-cache integration
compiles once, reuses the artifact, preserves the previous pointer after a
failed replacement, removes temporary preparation inputs and directly launches
the compiled prefix-108 executable. Its writable-user journal contains each
ordinal 1–108 exactly once, in order. The source image remains unchanged.

The reviewed retail-profile registry remains empty. No game main, menu, map,
assets, save, gameplay, multiplayer, Windows retail or macOS retail execution is
established. Uncalled virtual methods/factories and unsupported paths still fail
explicitly. There is no successful OS file/module trace or complete host SDK/
transitive-library closure. This remains a startup diagnostic, not a playable
native port. Private image-specific bindings and retail-derived material stay
outside GitHub. Constructor 109 is the next unaudited body.
