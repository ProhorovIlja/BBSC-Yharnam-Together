# Native Windows launcher preview

This preview uses Win32 controls and the system title bar. It can run beside the existing launcher
for a drag, resize, startup, and idle resource comparison. It is independent of the installer.

Build on Windows with Rust and a Windows linker:

```powershell
cargo build --release --locked --manifest-path bbport/launcher-native/Cargo.toml
```

Open `bbport/launcher-native/target/release/yharnam-launcher-preview.exe` for the window test.
The preview does not read game files, settings, or the network in this mode.

To enable the two buttons, run the preview with
`--launcher "C:\Games\Yharnam Together\BLauncher.exe"`, using the full path to your installed
launcher. **Open existing launcher** opens its UI. **Play with saved settings** calls its existing
`--play` entry point. These actions behave like running the installed launcher directly.
