# Corrected native startup: first 120 constructor returns

The private owner-only Linux x86-64 diagnostic extends prefix 116 through constructor 117 and
three following exact-pattern registration bodies. Constructor 117 registers the existing parent
object first reached by constructor 98 as the eighth class. It fills key/name and four phase rows,
and its translated parent getter links it to the existing class-105a object. It does not allocate
a second copy of the parent-98 object. The getter's reached path reuses an existing object.

All eight class records and 32 phase rows are checked for identity, names/keys, ownership and order.
This class's four phase addresses are reversed in memory; their actual vtable getter order is
checked rather than assuming increasing addresses. The original child -> late parent -> class105a
-> root chain is verified. Every reachable ancestor must be an audited host object; repeated
objects/cycles and unexpected pointers fail the diagnostic. Prior metadata objects, aliases,
mutexes, pool/free and warm-getter checks remain active. Metadata object count stays two.

Ten fresh processes per prefix 1–89/90/94/98/105/108/109/112/116/120 pass (100 process runs).
C-shim ASan/UBSan passes with LeakSanitizer disabled; translated assembly is not instrumented.
Prepared-cache integration compiles once, reuses the result, preserves the current pointer after
failed replacement, removes temporary preparation inputs and directly starts the compiled host
entry. The writable-user journal contains exactly 120 ordered returned rows with no duplicates;
the owner's source image is unchanged. Constructor 121 is the next unaudited startup body.

No approved playable retail profile, game main/menu/assets/map/save/gameplay/multiplayer,
Windows/macOS retail execution, complete SDK/library closure or OS file/module trace exists.
Uncalled factories/virtual methods, cold/error paths, registry growth/free and large-sort fallback
remain explicit traps. This diagnostic does not execute the HTTP, copy-shader or GX LOD paths.
Private image bindings, source image, generated assembly and executables stay outside GitHub.
