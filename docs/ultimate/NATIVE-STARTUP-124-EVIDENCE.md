# Corrected native startup: first 124 constructor returns

The private owner-only Linux x86-64 diagnostic extends prefix 120 through constructor 121 and
three exact-pattern registration bodies. Constructor 121 creates the ninth class and initializes
another distinct parent through its translated getter. All nine classes and 36 phase rows are
checked for identity, key/name, ownership and order, including the new class's reversed phase
getter order. Every reachable ancestor is checked against audited host objects and for cycles.
The class and its parent share the existing allocator; the new parent has an empty parent link
and no metadata fields. Metadata objects/mutexes remain two. Registrations 122–124 reuse ready
cells; they do not create three extra classes. Constructor 125 is next unaudited.

Ten fresh processes per prefix 1–89/90/94/98/105/108/109/112/116/120/124 pass (110 process runs).
C-shim ASan/UBSan passes with LeakSanitizer disabled; translated assembly is not instrumented.
Prepared-cache integration compiles once, reuses, preserves the current pointer after failed
replacement, removes temporary preparation inputs and directly starts the host entry. The
writable-user journal contains exactly 124 ordered return rows, without duplicates. The original
source image remains unchanged. Sorting is checked at 36 phase records; this does not certify
unreached large-sort/growth fallback paths.

No approved retail profile or game main/menu/assets/map/save/gameplay/multiplayer is established.
Windows/macOS retail, complete SDK/library closure and OS file/module tracing remain unproved.
Uncalled factories/virtuals, cold/error paths, growth/free and large-sort fallback stay explicit
traps. The startup diagnostic does not execute HTTP, GX LOD or copy-shader code. Private bindings,
source image, generated assembly and executable remain outside public GitHub.
