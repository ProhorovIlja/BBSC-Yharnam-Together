# Prepared native artifacts and expiring peer paths

The experimental preparation API now preserves a previously published native
artifact while a replacement is built. It verifies every runtime file before
reuse and starts only the prepared host entry. This is infrastructure for a
trusted AOT backend, not that backend or a playable Bloodborne port.

## Preparation contract

`tools/ultimate/prepared_native.py` accepts the exact selection returned by
`retail_profiles.select`, three SHA-256 dependency identities, and a trusted
developer-owned `build(stage, cancelled)` callback. The callback returns the
relative host entry path. Game files and their manifests cannot provide commands.

The three dependency identities cover the complete toolchain, host runtime ABI,
and executable modules actually consumed by the recipe. The integration must
derive these digests from those inputs; merely trusting a dump's claimed hash
does not establish identity. Selection already includes the executable/region/
version and recipe identity. Changing any dependency invalidates reuse.

The API stages a fresh build, inventories and hashes its files, checks the selected
host executable's header, flushes the files and directories, renames the completed
generation and atomically replaces `current.json`. Before that pointer replacement,
builder failure or cancellation preserves the previous pointer. A failure after
the pointer replacement can report an error even though publication happened;
call `current` to inspect the verified result. Power-loss guarantees depend on the
filesystem; POSIX directory fsync is used, Windows directory fsync is unavailable.

The kernel advisory lock serializes preparation and launch within this API and
is released when a process dies. A cancelled build removes its own staging
directory. A completed generation left unreferenced by cancellation/publication
failure remains available for diagnosis. Automatic cache garbage collection and
disk-space reservation are not implemented. An already running game holds no
cache lock; old generations must not be deleted while they may still be in use.

Before reuse or launch, file digests and the complete inventory must match.
Symlinks, hardlinks, traversal, ambiguous case names, Windows device names,
console module extensions and intermediate code are rejected. Limits bound file
count, manifest size and total payload bytes. These checks establish local
consistency, not publisher authenticity. They are not a sandbox against a process
that can concurrently modify the same user's cache. The header check alone also
cannot prove native ABI/import closure or reject a renamed console dependency.

`launch` verifies the host OS/architecture, passes an asset root and writable user
directory, and starts the entry directly without a shell, preparation fallback,
`bb-probe`, EBOOT or ELF argument. It removes inherited legacy loader environment
variables. The caller must provide the expected selection and dependencies in
production. The native executable's subsequent file/module access still needs
an OS trace and an ABI audit. Assets remain required. Runtime writes belong in
`BB_NATIVE_USER_DIR`, never the immutable build generation.

The resolved cache, asset and writable-user directories must be disjoint. Equal
or nested roots are rejected before the user directory is created or a process
is started. This prevents a configuration from directing runtime writes into
prepared artifacts or source assets. It is a path-configuration check, not an OS
write sandbox; trusted native code must still honor the writable-user directory.

The reviewed retail profile registry intentionally remains empty. This API is
not exposed as a working game launch option, and does not change today's loader
path. Windows/macOS game execution and first-run GUI integration remain unproven.

## Hybrid transport contract

`hybrid_path_lease.h` replaces the acceptance model's permanent direct-path boolean
with a reusable C++ policy. The policy binds a probe to room, session, both
connection generations, epoch and canonical endpoint digest. A fresh nonce and
increasing serial require an authenticated challenge/reply within one second.
Proof expires after two seconds. Duplicate or expired replies cannot renew it.
Endpoint rebinding, disconnect or disabling direct traffic revokes the proof.
Clock regression permanently disables direct traffic for that policy instance.

Only pose snapshots and visual emotes may select direct transport. Membership,
world commits, boss outcomes, rewards, travel and invasion admission stay on the
authority connection; loss of authority does not route them through a peer.
Unknown traffic is unavailable. Authenticated visual sequence windows are shared
across relay/direct, retained on endpoint rebinding and reset only for a newly
authenticated session/epoch/connection. Each visual stream has its own sequence.

The replay scope survives invalid binding attempts and transport disconnects.
Rebinding the same authenticated scope cannot reset its sequence window. Those
failures revoke direct permission; a different authenticated peer also starts
relay-only until fresh consent. The wire layer must reject rollback to a retired
scope and renegotiate an epoch before recreating a policy object for a stream.

The wire layer must perform authentication, supply CSPRNG nonces and canonical
endpoints, ensure replies arrived over the tested endpoint, and serialize calls.
No encryption, socket negotiation, NAT traversal or production packet routing is
provided by this header. It is not enabled in the live client/server. Integration
requires authenticated wire negotiation, relay failover and adversarial network
tests before a server-load or latency claim can be made.

## Validation

Run without retail files:

```sh
python -m unittest discover -s tools/ultimate -p 'test_*.py' -v
python tools/ultimate/ultimate_hybrid_policy.py
c++ -std=c++20 -Wall -Wextra -Werror -pedantic tools/ultimate/test_hybrid_path_lease.cpp -o /tmp/path-policy
/tmp/path-policy
```

Preparation tests include an actually compiled, developer-owned C executable,
reused builds, dependency invalidation, corrupt bundles, cancellation, publication
failure, cross-process exclusion and lock recovery after process termination.
Synthetic PE/ELF/Mach-O headers test rejection logic; they do not prove those
platforms can run the game. The workflow runs host tests on Linux, Windows and
macOS, but a workflow definition is not evidence that those jobs have passed.
