#![cfg_attr(windows, windows_subsystem = "windows")]

#[cfg(windows)]
mod theme;

#[cfg(windows)]
mod game;

#[cfg(windows)]
mod saves;

#[cfg(windows)]
mod preview {
    use std::env;
    use std::ffi::{OsStr, OsString};
    use std::io;
    use std::os::windows::ffi::{OsStrExt, OsStringExt};
    use std::path::PathBuf;
    use std::process::Command;
    use std::ptr::null_mut;
    use std::sync::{Mutex, OnceLock};
    use windows_sys::Win32::Foundation::{HWND, LPARAM, LRESULT, WPARAM};
    use windows_sys::Win32::Graphics::Gdi::InvalidateRect;
    use windows_sys::Win32::System::LibraryLoader::GetModuleHandleW;
    use windows_sys::Win32::UI::Controls::DRAWITEMSTRUCT;
    use windows_sys::Win32::UI::Controls::Dialogs::*;
    use windows_sys::Win32::UI::WindowsAndMessaging::*;

    const OPEN: usize = 100;
    const PLAY: usize = 101;
    const BROWSE: usize = 102;
    const BACKUP: usize = 103;
    const GAME_CHECKED: u32 = WM_APP + 1;
    static LAUNCHER: OnceLock<PathBuf> = OnceLock::new();
    static GAME_STATUS: Mutex<(u64, String)> = Mutex::new((0, String::new()));

    pub(super) fn wide(text: impl AsRef<OsStr>) -> Vec<u16> {
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
            (Some(path), None)
                if std::path::Path::new(&path).is_absolute()
                    && std::path::Path::new(&path).file_name().is_some() =>
            {
                Ok(Some(path.into()))
            }
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

    unsafe fn browse_game(hwnd: HWND) {
        let mut selected = vec![0u16; 32768];
        let filter = wide("Bloodborne executable\0eboot.bin\0");
        let prompt = wide("Choose eboot.bin in your Bloodborne folder");
        let mut dialog = OPENFILENAMEW {
            lStructSize: std::mem::size_of::<OPENFILENAMEW>() as u32,
            hwndOwner: hwnd,
            lpstrFile: selected.as_mut_ptr(),
            nMaxFile: selected.len() as u32,
            lpstrFilter: filter.as_ptr(),
            lpstrTitle: prompt.as_ptr(),
            Flags: OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR,
            ..OPENFILENAMEW::default()
        };
        if GetOpenFileNameW(&mut dialog) == 0 {
            return;
        }
        let length = selected.iter().position(|&unit| unit == 0).unwrap_or(selected.len());
        let eboot = PathBuf::from(OsString::from_wide(&selected[..length]));
        run_operation(hwnd, "Checking game files…", move || {
            super::game::Game::inspect(&eboot).map(|game| game.summary())
        });
    }

    unsafe fn run_operation(hwnd: HWND, pending: &str, work: impl FnOnce() -> io::Result<String> + Send + 'static) {
        let mut state = GAME_STATUS.lock().unwrap();
        state.0 += 1;
        state.1 = pending.into();
        let request = state.0;
        drop(state);
        InvalidateRect(hwnd, std::ptr::null(), 0);

        let target = hwnd as usize;
        std::thread::spawn(move || {
            let summary = work().unwrap_or_else(|error| error.to_string());
            let mut state = GAME_STATUS.lock().unwrap();
            if state.0 == request {
                state.1 = summary;
                PostMessageW(target as HWND, GAME_CHECKED, 0, 0);
            }
        });
    }

    unsafe extern "system" fn window_proc(
        hwnd: HWND, message: u32, wparam: WPARAM, lparam: LPARAM,
    ) -> LRESULT {
        match message {
            WM_PAINT => {
                let state = GAME_STATUS.lock().unwrap();
                super::theme::paint(hwnd, LAUNCHER.get().is_some(), &state.1);
                0
            }
            WM_SIZE | GAME_CHECKED => {
                InvalidateRect(hwnd, std::ptr::null(), 0);
                0
            }
            WM_GETMINMAXINFO => {
                let bounds = &mut *(lparam as *mut MINMAXINFO);
                bounds.ptMinTrackSize.x = 740;
                bounds.ptMinTrackSize.y = 515;
                0
            }
            WM_DRAWITEM if matches!(wparam, OPEN | PLAY | BROWSE | BACKUP) => {
                let label = match wparam {
                    PLAY => "PLAY",
                    BROWSE => "Browse game files…",
                    BACKUP => "Back up saves",
                    _ => "Settings",
                };
                super::theme::paint_button(&*(lparam as *const DRAWITEMSTRUCT), label, wparam == PLAY);
                1
            }
            WM_COMMAND if wparam == BROWSE => {
                browse_game(hwnd);
                0
            }
            WM_COMMAND if wparam == BACKUP && LAUNCHER.get().is_some() => {
                let install = LAUNCHER.get().unwrap().parent().unwrap();
                run_operation(hwnd, "Backing up saves…", move || {
                    use super::saves::Backup;
                    match super::saves::backup(install)? {
                        Backup::Empty => Ok("No saves found in the attached installation.".into()),
                        Backup::Unchanged => Ok("The latest backup already matches these saves.".into()),
                        Backup::Created(path) => Ok(format!("Save backup created: {}", path.display())),
                    }
                });
                0
            }
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
        super::theme::load_street_art()?;
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
                lpszClassName: class.as_ptr(),
                ..std::mem::zeroed()
            };
            if RegisterClassW(&wc) == 0 {
                return Err(io::Error::last_os_error());
            }
            let hwnd = CreateWindowExW(
                0, class.as_ptr(), wide("Yharnam Together - Native Launcher Preview").as_ptr(),
                WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN, CW_USEDEFAULT, CW_USEDEFAULT, 957, 520,
                null_mut(), null_mut(), instance, std::ptr::null(),
            );
            if hwnd.is_null() {
                return Err(io::Error::last_os_error());
            }
            for (text, id, x, y, width) in [
                ("Settings (existing launcher)", OPEN, 15, 193, 203),
                ("Back up saves", BACKUP, 15, 243, 203),
                ("Play with saved settings", PLAY, 264, 352, 160),
                ("Browse game files", BROWSE, 440, 352, 184),
            ] {
                let button_style = if id == BROWSE || LAUNCHER.get().is_some() {
                    WS_TABSTOP
                } else {
                    WS_DISABLED
                };
                let control = CreateWindowExW(
                    0, wide("BUTTON").as_ptr(), wide(text).as_ptr(),
                    WS_CHILD | WS_VISIBLE | BS_OWNERDRAW as u32 | button_style,
                    x, y, width, 42, hwnd, id as _, instance, std::ptr::null(),
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
