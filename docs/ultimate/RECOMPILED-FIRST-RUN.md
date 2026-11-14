# Ultimate: automatic first-run native preparation

Status: requirements and acceptance criteria. No runtime, installer, protocol, or deployment changes in this commit.

## Player flow

- Select a clean personal game dump or supported PKG set. Resolve base, update 1.09 and applicable Old Hunters content for the edition. Inspect title ID and version; verify supported original executable and module hashes after extraction. Detect patched executables, inconsistent updates and missing content; never patch the source copy.
- The launcher owns the complete local preparation flow, including extraction for supported inputs, recompilation, linking, progress, cancellation and recovery. Bundle or provision pinned, verified host tools automatically with their notices. Do not require a manual Python, compiler or SDK installation.
- Do not assume all encrypted packages are extractable. Support only input types that can be processed locally with the necessary legitimately available prerequisites. Otherwise identify the unsupported input or missing prerequisite and accept a decrypted personal dump. Never distribute console keys, decrypted modules or generated game code.
- Use a versioned staging directory. Promote a verified local build only after preparation succeeds. Cache by verified inputs, target OS/architecture, recompiler/runtime version and hook ABI; do not recompile on each launch. A cancelled or failed build must not replace a working one.
- Play starts the host executable and host-native libraries (Windows EXE/DLL, Linux executable/SO, macOS app/dylib). Continue to read game assets from the player's files. In the recompiled mode, no PS4 EBOOT, ELF/SELF or PRX/SPRX may be opened or loaded at game runtime; no hidden fallback to the current loader, translation or interpreter. Host ELF on Linux is fine. Keep the current runtime as an explicitly separate option while this matures.

## Regional and runtime scope

Use known original hashes rather than hard-coding one folder name or assuming all regional builds differ. Share a code profile only where verified code and ABI match; verify edition/content compatibility separately. Start with a verified 1.09 reference build, then expand coverage with real regional fixtures. Unknown hashes fail with a clear reason. Windows x64 and Linux x64 first, macOS arm64 separate. A locally generated game library is not a clean-room rewrite or a permission to redistribute game code.

The existing bbcoop boundary is a starting point; replace original-address hooks with generated-code integration points. Preserve the current server and protocol unless compatibility evidence requires a change. Audit each PS4 module and system import: replace with a host implementation or prepare a host-native equivalent. Do not bundle original or transformed Sony game code, assets, firmware, or player saves.

## Release gates

From a clean machine without developer tools, prepare from supported inputs, then run offline with all original PS4 executable modules unavailable (without modifying the user's source). Trace file/module access, reject hidden fallback, enter a map, save, quit, relaunch and load. Verify restart reuses the prepared build, failed preparation leaves the previous build intact, and modified, mismatched or unsupported input is rejected safely. Then test Windows/Linux co-op with unchanged account, saves and reconnect behavior on a staging server. Passing on one region or OS does not certify another.
