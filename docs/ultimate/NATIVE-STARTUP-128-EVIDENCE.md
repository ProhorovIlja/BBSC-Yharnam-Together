# Corrected native startup: first 128 constructor returns

The private owner-only Linux x86-64 diagnostic extends prefix 124 through constructor 125 and
three exact-pattern registration bodies. It now checks ten class records, 40 phase records and
three independent metadata allocations/alias lists/mutexes. Constructor 125 links its class to
the already registered parent-98 object; all reachable ancestry remains known and acyclic.
Duplicate metadata insertion appends an alias without another object allocation. The factory
pointer is registered but not invoked; unimplemented virtual/factory paths remain terminal.

The first attempt stopped at an explicit unsupported branch before constructor 125 returned.
The sort function's translated range had excluded its final 13 bytes, including a 12-byte cold
continuation back to the existing body. Complete the original pinned function range, validating
the continuation bytes before translation. This is the game's own continued sort, not a host
sorting replacement. The earlier description of this site as an unimplemented large-sort
fallback was imprecise: it is a continuation of the same original function. The new 40-phase
case reaches it; other unreached growth/free/sort paths remain unverified.

Twelve prefix modes (1–89/90/94/98/105/108/109/112/116/120/124/128) each pass ten fresh processes:
120 runs. C-shim ASan/UBSan passes with LeakSanitizer disabled; translated assembly is not
instrumented. Prepared-cache integration compiles once, reuses, preserves the current pointer
after failed replacement, removes temporary preparation inputs and directly starts the host
entry. The writable-user journal has exactly 128 ordered return rows; the original image remains
unchanged. Constructor 129 is next unaudited.

There is no approved playable retail profile, game main/menu/assets/map/save/gameplay/multiplayer,
Windows/macOS retail execution, complete SDK/library closure or OS file/module trace. This
diagnostic does not execute the HTTP/GX/copy-shader/NGX paths. Private image bindings, image,
generated assembly and executable remain outside public GitHub.
