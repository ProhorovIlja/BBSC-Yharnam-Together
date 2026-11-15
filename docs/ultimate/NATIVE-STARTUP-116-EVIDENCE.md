# Corrected native startup: first 116 constructor returns

The private owner-only Linux x86-64 diagnostic extends prefix 112 through constructor 113 and
three following exact-pattern registration bodies. Constructor 113 creates the seventh class
record, links it to a distinct parent through translated getter/base initialization and registers
a second metadata object with its own allocation, alias list and mutex. Its description contains
an integer tag, not an invoked factory. Constructors 114–116 reuse registration cells.

All seven class records and 28 phase rows are checked for identity, key/name, ownership and order.
Both metadata objects, distinct parents, allocator ownership and mutexes are checked; duplicate
metadata insertion appends an alias without allocating another object. Prior allocator, lock,
inheritance and warm-getter checks remain active. Constructor 117 is the next unaudited body.

Ten fresh processes per prefix 1–89/90/94/98/105/108/109/112/116 pass (90 processes). C-shim
ASan/UBSan passes with LeakSanitizer disabled; translated assembly is not instrumented. Prepared
cache integration compiles once, reuses the result, preserves the current pointer after failed
replacement, removes temporary preparation inputs and directly starts the host entry. Its journal
contains exactly 116 ordered return rows. The owner's original image remains unchanged.

The approved retail-profile registry stays empty. No game main, menu, assets, map, save, gameplay,
multiplayer, Windows retail or macOS retail execution is established. Unsupported factories,
virtual methods, cold/error paths, registry growth/free and large-sort fallback remain explicit
traps. Complete SDK/import/library closure and OS file/module tracing are unproved. This private
startup diagnostic does not execute the GX LOD guard or the copy-shader HLE path. Game-derived
bindings, original image, generated assembly and executables remain outside public GitHub.
