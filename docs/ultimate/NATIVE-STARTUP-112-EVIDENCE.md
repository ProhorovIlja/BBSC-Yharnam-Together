# Corrected native startup: first 112 constructor returns

The owner-only Linux x86-64 diagnostic extends prefix 108 through constructor 109
and the exact-pattern registration bodies 110–112 in their original order.
Constructor 109 creates the sixth class record and four further phase rows: all
six class and twenty-four phase records are checked for identity, names/keys,
ownership and ordering. It links to a distinct parent object initialized through
the translated parent/base initializer; its allocator and empty fields are checked.

The global getter previously represented by an uninvoked aborting placeholder
now has its actual translated body. The newly reached warm path returns the
existing shared global object, and the parent getter reuses its existing instance.
This does not certify every cold/error path of that getter. The three following
registration bodies reuse ready cells; they are three returns, not three more
class records. The prior inheritance, metadata/aliases/mutex and pool/lock checks
remain active. Constructor 113 is the next unaudited body.

Ten fresh-process repetitions of each prefix 1–89/90/94/98/105/108/109/112 pass.
C-shim ASan/UBSan passes with LeakSanitizer disabled; translated assembly is not
instrumented. The prepared-cache integration compiles once, verifies reuse and
failed-replacement preservation, removes temporary preparation inputs and starts
the compiled host entry directly. Its writable-user journal contains exactly
112 ordered return records. The owner-provided source image remains unchanged.

The registry of approved retail profiles remains empty. No game main, menu,
assets, map, save, gameplay, multiplayer, Windows retail or macOS retail execution
is established. Uncalled virtual methods/factories, unsupported error paths,
registry growth/free and large-sort fallback still fail explicitly. There is no
successful OS file/module trace or complete SDK/transitive-library closure.
Private bindings and retail-derived material remain outside GitHub. This is a
startup diagnostic, not a playable port or an integration of the LOD guard into
the strict prepared-native backend.
