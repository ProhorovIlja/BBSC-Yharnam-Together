#![cfg_attr(windows, windows_subsystem = "windows")]

#[cfg(windows)]
mod preview {
    use std::env;
    use std::ffi::OsStr;
    use std::io;
    use std::os::windows::ffi::OsStrExt;
    use std::path::PathBuf;
    use std::process::Command;
    use std::ptr::null_mut;
    use std::sync::OnceLock;
    use windows_sys::Win32::Foundation::{HWND, LPARAM, LRESULT, WPARAM};
    use windows_sys::Win32::System::LibraryLoader::GetModuleHandleW;
    use windows_sys::Win32::UI::WindowsAndMessaging::*;

    const OPEN: usize = 100;
    const PLAY: usize = 101;
    static LAUNCHER: OnceLock<PathBuf> = OnceLock::new();

    fn wide(text: impl AsRef<OsStr>) -> Vec<u16> {
        text.as_ref().encode_wide().chain(Some(0)).collect()
    }

    fn launcher_path() -> io::Result<Option<PathBuf>> {
        let mut args = env::args_os().skip(1);
        let Some(flag) = args.next() else {
            return Ok(None);
        };
        if flag != "--launcher" {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "Expected --launcher followed by a full path to BLauncher.exe."));
        }
        match (args.next(), args.next()) {
            (Some(path), None) if PathBuf::from(&path).is_absolute() => Ok(Some(path.into())),
            _ => Err(io::Error::new(io::ErrorKind::InvalidInput, "Supply a full path to BLauncher.exe.")),
        }
    }

    fn start_launcher(play: bool) -> io::Result<()> {
        let path = LAUNCHER.get().expect("Play and Open require a launcher path");
        let mut command = Command::new(path);
        if let Some(parent) = path.parent() {
            command.current_dir(parent);
        }
        if play {
            command.arg("--play");
        }
        command.spawn().map(|_| ())
    }

    unsafe extern "system" fn window_proc(
        hwnd: HWND, message: u32, wparam: WPARAM, lparam: LPARAM,
    ) -> LRESULT {
        match message {
            WM_COMMAND if matches!(wparam, OPEN | PLAY) && LAUNCHER.get().is_some() => {
                if let Err(error) = start_launcher(wparam == PLAY) {
                    MessageBoxW(hwnd, wide(error.to_string()).as_ptr(),
                                wide("Could not open the existing launcher").as_ptr(), MB_ICONERROR);
                }
                0
            }
            WM_DESTROY => {
                PostQuitMessage(0);
                0
            }
            _ => DefWindowProcW(hwnd, message, wparam, lparam),
        }
    }

    pub fn run(smoke: bool) -> io::Result<()> {
        if !smoke {
            if let Some(path) = launcher_path()? {
                let _ = LAUNCHER.set(path);
            }
        }
        let class = wide("YharnamLauncherPreview");
        unsafe {
            let instance = GetModuleHandleW(std::ptr::null());
            if instance.is_null() {
                return Err(io::Error::last_os_error());
            }
            let wc = WNDCLASSW {
                lpfnWndProc: Some(window_proc),
                hInstance: instance,
                hCursor: LoadCursorW(null_mut(), IDC_ARROW),
                hbrBackground: (windows_sys::Win32::Graphics::Gdi::COLOR_WINDOW + 1) as _,
                lpszClassName: class.as_ptr(),
                ..std::mem::zeroed()
            };
            if RegisterClassW(&wc) == 0 {
                return Err(io::Error::last_os_error());
            }
            let hwnd = CreateWindowExW(
                0, class.as_ptr(), wide("Yharnam Together - Native Launcher Preview").as_ptr(),
                WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 620, 360,
                null_mut(), null_mut(), instance, std::ptr::null(),
            );
            if hwnd.is_null() {
                return Err(io::Error::last_os_error());
            }
            let detail = if LAUNCHER.get().is_some() {
                "The buttons use the existing launcher and its saved settings."
            } else {
                "Window test only. Pass --launcher with a full path to enable the buttons."
            };
            for (class, label, id, x, y, width) in [
                ("STATIC", "Drag the title bar or resize the window to compare responsiveness.", 0, 20, 24, 560),
                ("STATIC", detail, 0, 20, 68, 560),
                ("BUTTON", "Open existing launcher", OPEN, 20, 112, 195),
                ("BUTTON", "Play with saved settings", PLAY, 230, 112, 195),
            ] {
                let button_style = if id == 0 {
                    0
                } else if LAUNCHER.get().is_some() {
                    WS_TABSTOP
                } else {
                    WS_DISABLED
                };
                let control = CreateWindowExW(
                    0, wide(class).as_ptr(), wide(label).as_ptr(), WS_CHILD | WS_VISIBLE | button_style,
                    x, y, width, 32, hwnd, id as _, instance, std::ptr::null(),
                );
                if control.is_null() {
                    return Err(io::Error::last_os_error());
                }
            }
            if smoke {
                if DestroyWindow(hwnd) == 0 {
                    return Err(io::Error::last_os_error());
                }
                return Ok(());
            }
            ShowWindow(hwnd, SW_SHOW);
            let mut message = MSG::default();
            loop {
                match GetMessageW(&mut message, null_mut(), 0, 0) {
                    -1 => return Err(io::Error::last_os_error()),
                    0 => return Ok(()),
                    _ => {
                        if IsDialogMessageW(hwnd, &mut message) == 0 {
                            TranslateMessage(&message);
                            DispatchMessageW(&message);
                        }
                    }
                }
            }
        }
    }

    pub fn show_error(error: io::Error) {
        unsafe {
            MessageBoxW(null_mut(), wide(error.to_string()).as_ptr(),
                        wide("Yharnam Together - Native Launcher Preview").as_ptr(), MB_ICONERROR);
        }
    }
}

#[cfg(windows)]
fn main() {
    let smoke = std::env::args_os().len() == 2 && std::env::args_os().nth(1).is_some_and(|arg| arg == "--smoke");
    if let Err(error) = preview::run(smoke) {
        if !smoke {
            preview::show_error(error);
        }
        std::process::exit(1);
    }
}

#[cfg(not(windows))]
fn main() {
    eprintln!("This native launcher preview runs on Windows.");
}
