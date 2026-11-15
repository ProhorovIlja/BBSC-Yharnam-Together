# Corrected native startup: first 132 constructor returns

The owner-only Linux x86-64 diagnostic extends prefix 128 with one newly translated
original constructor and three exact-pattern registration bodies. It verifies eleven
class records, 44 phase rows and five independent metadata objects with their alias
lists and mutexes. The new constructor creates two metadata descriptors, links its
class to an existing parent and reuses that parent's warm global storage. All known
ancestry remains checked and acyclic. Stored factory pointers are not invoked;
unsupported virtual, allocation-growth and free paths remain explicit traps.

The original full sort continuation established at prefix 128 remains byte-pinned
and translated; no host sorting replacement was introduced. Original constructor
and registration bytes are verified before translation.

Thirteen prefix modes (1-89/90/94/98/105/108/109/112/116/120/124/128/132) pass ten
fresh processes each: 130 runs. C-shim ASan/UBSan passes with leak checking disabled;
generated assembly itself is not sanitizer-instrumented. Prepared-cache integration
compiles once, reuses the result, preserves the current pointer after an intentionally
failed replacement, removes preparation copies and directly starts the native host
entry. Its writable-user journal contains exactly 132 ordered return rows with no
duplicates. The original input image is unchanged. Constructor 133 is next unaudited.

This is a startup diagnostic, not a playable game. Game main/menu/assets/maps/saves,
gameplay/multiplayer, native Windows/macOS/ARM64 retail execution, full SDK/library
closure and an OS file/module trace remain unproven. The diagnostic does not exercise
NGX, HTTP or the GPU renderer. Private game bytes, address bindings, generated assembly
and executables remain outside public GitHub; the owner reproducer is stored privately.
