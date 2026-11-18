# Native Windows launcher preview

This preview uses Win32 controls, the system title bar, and the existing launcher's street artwork
and palette. It can run beside the existing launcher
for a drag, resize, startup, and idle resource comparison. It is independent of the installer.

Build on Windows with Rust and a Windows linker:

```powershell
cargo build --release --locked --manifest-path bbport/launcher-native/Cargo.toml
```

Open `bbport/launcher-native/target/release/yharnam-launcher-preview.exe` for the window test.
**Browse game files** checks the selected `eboot.bin`, edition metadata, and any adjacent 1.09
update on a worker thread. This preview does not save the selection or change your installation.

To enable the two buttons, run the preview with
`--launcher "C:\Games\Yharnam Together\BLauncher.exe"`, using the full path to your installed
launcher. **Settings** opens its UI. **PLAY** calls its existing
`--play` entry point. These actions behave like running the installed launcher directly.
