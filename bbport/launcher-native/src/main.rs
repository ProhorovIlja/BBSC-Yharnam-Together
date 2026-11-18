#![cfg_attr(windows, windows_subsystem = "windows")]

#[cfg(windows)]
mod theme;

#[cfg(windows)]
mod game;

#[cfg(windows)]
mod saves;

#[cfg(windows)]
mod profile;

#[cfg(windows)]
mod preview {
    use std::env;
    use std::ffi::{OsStr, OsString};
    use std::io;
    use std::os::windows::ffi::{OsStrExt, OsStringExt};
    use std::path::PathBuf;
    use std::process::Command;
    use std::ptr::null_mut;
    use std::sync::Mutex;
    use windows_sys::Win32::Foundation::{HWND, LPARAM, LRESULT, WPARAM};
    use windows_sys::Win32::Graphics::Gdi::InvalidateRect;
    use windows_sys::Win32::System::LibraryLoader::GetModuleHandleW;
    use windows_sys::Win32::UI::Controls::{DRAWITEMSTRUCT, EM_SETLIMITTEXT};
    use windows_sys::Win32::UI::Controls::Dialogs::*;
    use windows_sys::Win32::UI::Input::KeyboardAndMouse::EnableWindow;
    use windows_sys::Win32::UI::WindowsAndMessaging::*;

    const OPEN: usize = 100;
    const PLAY: usize = 101;
    const BROWSE: usize = 102;
    const BACKUP: usize = 103;
    const ATTACH: usize = 104;
    const SAVE: usize = 105;
    const HOST: usize = 106;
    const GAME_CHECKED: u32 = WM_APP + 1;
    static LAUNCHER: Mutex<Option<PathBuf>> = Mutex::new(None);
    static SELECTED_GAME: Mutex<Option<PathBuf>> = Mutex::new(None);
    static LOADED_HOST: Mutex<Option<String>> = Mutex::new(None);
    static GAME_STATUS: Mutex<(bool, String)> = Mutex::new((false, String::new()));

    fn attached_launcher() -> Option<PathBuf> {
        LAUNCHER.lock().unwrap().clone()
    }

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

    fn start_launcher(path: &std::path::Path, play: bool) -> io::Result<()> {
        let mut command = Command::new(path);
        if let Some(parent) = path.parent() {
            command.current_dir(parent);
        }
        if play {
            command.arg("--play");
        }
        command.spawn().map(|_| ())
    }

    unsafe fn choose_file(hwnd: HWND, filter: &str, prompt: &str) -> Option<PathBuf> {
        let mut selected = vec![0u16; 32768];
        let filter = wide(filter);
        let prompt = wide(prompt);
        let mut dialog = OPENFILENAMEW {
            lStructSize: std::mem::size_of::<OPENFILENAMEW>() as u32,
            hwndOwner: hwnd,
            lpstrFile: selected.as_mut_ptr(),
            nMaxFile: selected.len() as u32,
            lpstrFilter: filter.as_ptr(),
            lpstrTitle: prompt.as_ptr(),
            Flags: OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR | OFN_EXPLORER,
            ..OPENFILENAMEW::default()
        };
        if GetOpenFileNameW(&mut dialog) == 0 {
            return None;
        }
        let length = selected.iter().position(|&unit| unit == 0).unwrap_or(selected.len());
        Some(PathBuf::from(OsString::from_wide(&selected[..length])))
    }

    unsafe fn browse_game(hwnd: HWND) {
        let Some(eboot) = choose_file(
            hwnd, "Bloodborne executable\0eboot.bin\0", "Choose eboot.bin in your Bloodborne folder",
        ) else { return };
        run_operation(hwnd, "Checking game files…", move || {
            *SELECTED_GAME.lock().unwrap() = None;
            let game = super::game::Game::inspect(&eboot)?;
            *SELECTED_GAME.lock().unwrap() = eboot.parent().map(std::path::Path::to_path_buf);
            Ok(format!("{}  ·  Save setup to use this folder.", game.summary()))
        });
    }

    unsafe fn attach(hwnd: HWND, path: PathBuf) {
        run_operation(hwnd, "Loading co-op settings…", move || {
            if !path.is_file() || !path.file_name().is_some_and(|n| n.eq_ignore_ascii_case("BLauncher.exe")) {
                return Err(io::Error::other("Choose BLauncher.exe from an existing Yharnam Together installation."));
            }
            let existing = super::profile::host(path.parent().unwrap());
            *LAUNCHER.lock().unwrap() = Some(path);
            *SELECTED_GAME.lock().unwrap() = None;
            // A broken or old profile must never leave the previous installation's address in the editor.
            *LOADED_HOST.lock().unwrap() = Some(existing.as_ref().cloned().unwrap_or_default());
            existing.map(|_| "Installation attached. You can edit and save co-op setup below.".into())
        });
    }

    unsafe fn refresh_controls(hwnd: HWND) {
        let busy = GAME_STATUS.lock().unwrap().0;
        let attached = attached_launcher().is_some();
        for id in [OPEN, PLAY, BROWSE, BACKUP, ATTACH, SAVE, HOST] {
            let enabled = !busy && (attached || matches!(id, BROWSE | ATTACH));
            EnableWindow(GetDlgItem(hwnd, id as i32), i32::from(enabled));
        }
    }

    unsafe fn run_operation(hwnd: HWND, pending: &str, work: impl FnOnce() -> io::Result<String> + Send + 'static) {
        let mut state = GAME_STATUS.lock().unwrap();
        if state.0 {
            return;
        }
        state.0 = true;
        state.1 = pending.into();
        drop(state);
        refresh_controls(hwnd);
        InvalidateRect(hwnd, std::ptr::null(), 0);

        let target = hwnd as usize;
        if let Err(error) = std::thread::Builder::new().spawn(move || {
            let summary = work().unwrap_or_else(|error| error.to_string());
            let mut state = GAME_STATUS.lock().unwrap();
            *state = (false, summary);
            PostMessageW(target as HWND, GAME_CHECKED, 0, 0);
        }) {
            *GAME_STATUS.lock().unwrap() = (false, error.to_string());
            refresh_controls(hwnd);
            InvalidateRect(hwnd, std::ptr::null(), 0);
        }
    }

    unsafe extern "system" fn window_proc(
        hwnd: HWND, message: u32, wparam: WPARAM, lparam: LPARAM,
    ) -> LRESULT {
        match message {
            WM_PAINT => {
                let summary = GAME_STATUS.lock().unwrap().1.clone();
                super::theme::paint(hwnd, attached_launcher().is_some(), &summary);
                0
            }
            GAME_CHECKED => {
                if let Some(host) = LOADED_HOST.lock().unwrap().take() {
                    SetWindowTextW(GetDlgItem(hwnd, HOST as i32), wide(host).as_ptr());
                }
                refresh_controls(hwnd);
                InvalidateRect(hwnd, std::ptr::null(), 0);
                0
            }
            WM_SIZE => {
                InvalidateRect(hwnd, std::ptr::null(), 0);
                0
            }
            WM_GETMINMAXINFO => {
                let bounds = &mut *(lparam as *mut MINMAXINFO);
                bounds.ptMinTrackSize.x = 740;
                bounds.ptMinTrackSize.y = 610;
                0
            }
            WM_DRAWITEM if matches!(wparam, OPEN | PLAY | BROWSE | BACKUP | ATTACH | SAVE) => {
                let label = match wparam {
                    PLAY => "PLAY",
                    BROWSE => "Browse game files…",
                    BACKUP => "Back up saves",
                    ATTACH => "Attach installation…",
                    SAVE => "Save setup",
                    _ => "Open legacy settings",
                };
                super::theme::paint_button(&*(lparam as *const DRAWITEMSTRUCT), label, wparam == PLAY);
                1
            }
            WM_COMMAND if wparam == ATTACH => {
                if let Some(path) = choose_file(
                    hwnd, "Yharnam Together launcher\0BLauncher.exe\0", "Choose your installed BLauncher.exe",
                ) {
                    attach(hwnd, path);
                }
                0
            }
            WM_COMMAND if wparam == BROWSE => {
                browse_game(hwnd);
                0
            }
            WM_COMMAND if matches!(wparam, OPEN | PLAY | SAVE | BACKUP) => {
                if let Some(path) = attached_launcher() {
                    let install = path.parent().unwrap().to_owned();
                    match wparam {
                        BACKUP => run_operation(hwnd, "Backing up saves…", move || {
                            use super::saves::Backup;
                            match super::saves::backup(&install)? {
                                Backup::Empty => Ok("No saves found in the attached installation.".into()),
                                Backup::Unchanged => Ok("The latest backup already matches these saves.".into()),
                                Backup::Created(path) => Ok(format!("Save backup created: {}", path.display())),
                            }
                        }),
                        SAVE => {
                            let mut buffer = [0u16; 2048];
                            let count = GetWindowTextW(GetDlgItem(hwnd, HOST as i32), buffer.as_mut_ptr(), buffer.len() as i32);
                            let host = String::from_utf16_lossy(&buffer[..count as usize]);
                            let game = SELECTED_GAME.lock().unwrap().clone();
                            run_operation(hwnd, "Saving co-op setup…", move || {
                                super::profile::save(&install, game.as_deref(), &host)?;
                                *SELECTED_GAME.lock().unwrap() = None;
                                Ok("Co-op setup saved.".into())
                            });
                        }
                        _ => run_operation(hwnd, "Starting existing launcher…", move || {
                            start_launcher(&path, wparam == PLAY)?;
                            Ok("Handed off to the existing launcher.".into())
                        }),
                    }
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
        let initial_launcher = if smoke { None } else { launcher_path()? };
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
                WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN, CW_USEDEFAULT, CW_USEDEFAULT, 957, 632,
                null_mut(), null_mut(), instance, std::ptr::null(),
            );
            if hwnd.is_null() {
                return Err(io::Error::last_os_error());
            }
            for (text, id, x, y, width) in [
                ("Settings (existing launcher)", OPEN, 15, 193, 203),
                ("Back up saves", BACKUP, 15, 243, 203),
                ("Attach installation", ATTACH, 15, 293, 203),
                ("Play with saved settings", PLAY, 264, 352, 160),
                ("Browse game files", BROWSE, 440, 352, 184),
                ("Save setup", SAVE, 565, 463, 118),
            ] {
                let button_style = if matches!(id, BROWSE | ATTACH) {
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
            let host = CreateWindowExW(
                WS_EX_CLIENTEDGE, wide("EDIT").as_ptr(), wide("").as_ptr(),
                WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_DISABLED | ES_AUTOHSCROLL as u32,
                264, 469, 282, 30, hwnd, HOST as _, instance, std::ptr::null(),
            );
            if host.is_null() {
                return Err(io::Error::last_os_error());
            }
            SendMessageW(host, EM_SETLIMITTEXT, 2047, 0);
            if smoke {
                if DestroyWindow(hwnd) == 0 {
                    return Err(io::Error::last_os_error());
                }
                return Ok(());
            }
            ShowWindow(hwnd, SW_SHOW);
            if let Some(path) = initial_launcher {
                attach(hwnd, path);
            }
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
