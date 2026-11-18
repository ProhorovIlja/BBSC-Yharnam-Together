# Native Windows launcher preview

This preview uses Win32 controls, the system title bar, and the existing launcher's street artwork
and palette. It can run beside the existing launcher
for a drag, resize, startup, and idle resource comparison. It is independent of the installer.

Build on Windows with Rust and a Windows linker:

```powershell
cargo build --release --locked --manifest-path bbport/launcher-native/Cargo.toml
```

Open `bbport/launcher-native/target/release/yharnam-launcher-preview.exe` for the window test.
**Attach installation** lets you choose your existing `BLauncher.exe` from the window.
**Browse game files** checks the selected `eboot.bin`, edition metadata, and any adjacent 1.09
update on a worker thread. **Save setup** applies the selected game and host address to the attached
installation's `user/coop.json`. Existing fields such as server keys and sign-in data are preserved.
Use **Open legacy settings** for account sign-in, server mode, and settings that are still handled there.

To enable the two buttons, run the preview with
`--launcher "C:\Games\Yharnam Together\BLauncher.exe"`, using the full path to your installed
launcher. **Open legacy settings** opens its UI. **PLAY** calls its existing
`--play` entry point. These actions behave like running the installed launcher directly.

**Back up saves** snapshots the attached installation's `user/savedata`, per-profile saves,
and party records on a worker thread. The backup uses the existing launcher's timestamped
`user/save-backups` layout and can be selected in its restore UI. Close the game before backing
up. The preview does not restore or prune backups.
