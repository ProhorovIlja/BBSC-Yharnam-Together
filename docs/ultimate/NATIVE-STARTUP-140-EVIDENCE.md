# Corrected native startup: first 140 constructor returns

The private Linux x86-64 owner diagnostic extends the previous prefix136 with one
original class constructor and three exact-pattern registration bodies. It also
executes that class's independent root getter. The root stays unregistered: the
correct totals are thirteen class records, 52 phase rows and six metadata objects.

The new checks verify class/root storage and vtable identities, cached allocator,
guard state, empty metadata vectors and repeated warm-root getter returns. The
ancestry walk accepts the new root only after the corresponding prefix exists;
it still rejects foreign pointers and cycles. All earlier phase/metadata/alias
and allocator checks remain. The new class adds no metadata allocation, so the
previous expected allocation/lock counts are retained rather than increased.

Fifteen prefix modes each pass ten fresh processes: 150 runs. C-shim ASan/UBSan
also passes with leak checking disabled; translated assembly is not instrumented.
The prepared-native API compiles once, reuses the cache, and keeps its current
pointer after an intentional replacement failure. Temporary preparation copies
are removed before launch. The host entry writes exactly 140 ordered return rows
without duplicates, and the owner's input remains unchanged. Constructor141 is
the next unaudited boundary. The private reproducer remains outside public GitHub.

Game main/assets/maps/save/gameplay, multiplayer, complete SDK/toolchain closure,
OS file/module tracing and native Windows/macOS/ARM64 retail execution remain
unproven. This diagnostic is not an approved playable no-eboot profile and does
not execute the renderer or the separate whole-function recompiler probe.
