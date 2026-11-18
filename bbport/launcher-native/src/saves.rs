use std::fs::{self, File};
use std::io::{self, Read};
use std::os::windows::fs::MetadataExt;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, Instant};
use windows_sys::Win32::Foundation::SYSTEMTIME;
use windows_sys::Win32::Storage::FileSystem::{MoveFileW, FILE_ATTRIBUTE_REPARSE_POINT};
use windows_sys::Win32::System::SystemInformation::GetLocalTime;

const BACKUPS: &str = "save-backups";
const NOTE: &str = "launcher.txt";
static NEXT_STAGE: AtomicUsize = AtomicUsize::new(0);

#[derive(Debug, PartialEq, Eq)]
pub enum Backup {
    Empty,
    Unchanged,
    Created(PathBuf),
}

fn entries(path: &Path) -> io::Result<Vec<fs::DirEntry>> {
    match fs::read_dir(path) {
        Ok(entries) => entries.collect(),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(Vec::new()),
        Err(error) => Err(error),
    }
}

fn check_link(path: &Path, metadata: &fs::Metadata) -> io::Result<()> {
    if metadata.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT != 0 {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!("Save backup stopped at a link: {}", path.display()),
        ));
    }
    Ok(())
}

fn collect_tree(user: &Path, relative: &Path, files: &mut Vec<PathBuf>) -> io::Result<()> {
    let path = user.join(relative);
    match fs::symlink_metadata(&path) {
        Ok(metadata) => check_link(&path, &metadata)?,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(()),
        Err(error) => return Err(error),
    }
    for entry in entries(&path)? {
        let metadata = fs::symlink_metadata(entry.path())?;
        check_link(&entry.path(), &metadata)?;
        let child = relative.join(entry.file_name());
        if metadata.is_dir() {
            collect_tree(user, &child, files)?;
        } else if metadata.is_file() {
            files.push(child);
        }
    }
    Ok(())
}

fn save_files(user: &Path) -> io::Result<Vec<PathBuf>> {
    let mut files = Vec::new();
    collect_tree(user, Path::new("savedata"), &mut files)?;
    let home = user.join("home");
    match fs::symlink_metadata(&home) {
        Ok(metadata) => check_link(&home, &metadata)?,
        Err(error) if error.kind() == io::ErrorKind::NotFound => {}
        Err(error) => return Err(error),
    }
    for profile in entries(&home)? {
        let metadata = fs::symlink_metadata(profile.path())?;
        if metadata.is_dir() {
            check_link(&profile.path(), &metadata)?;
            collect_tree(user, &Path::new("home").join(profile.file_name()).join("savedata"), &mut files)?;
        }
    }
    for entry in entries(user)? {
        let name = entry.file_name();
        if name.to_str().is_some_and(|name| name.starts_with("bloodborne_party_") && name.ends_with(".txt")) {
            let metadata = fs::symlink_metadata(entry.path())?;
            check_link(&entry.path(), &metadata)?;
            if metadata.is_file() {
                files.push(name.into());
            }
        }
    }
    files.sort();
    Ok(files)
}

fn same_contents(left: &Path, right: &Path) -> io::Result<bool> {
    let (mut left, mut right) = (File::open(left)?, File::open(right)?);
    let mut remaining = left.metadata()?.len();
    if remaining != right.metadata()?.len() {
        return Ok(false);
    }
    let (mut a, mut b) = ([0u8; 32768], [0u8; 32768]);
    while remaining != 0 {
        let chunk = remaining.min(a.len() as u64) as usize;
        left.read_exact(&mut a[..chunk])?;
        right.read_exact(&mut b[..chunk])?;
        if a[..chunk] != b[..chunk] {
            return Ok(false);
        }
        remaining -= chunk as u64;
    }
    Ok(left.read(&mut a[..1])? == 0 && right.read(&mut b[..1])? == 0)
}

fn matches_snapshot(user: &Path, snapshot: &Path, files: &[PathBuf]) -> io::Result<bool> {
    if save_files(snapshot)? != files {
        return Ok(false);
    }
    for relative in files {
        if !same_contents(&user.join(relative), &snapshot.join(relative))? {
            return Ok(false);
        }
    }
    Ok(save_files(user)? == files)
}

fn latest_backup(root: &Path) -> io::Result<Option<PathBuf>> {
    let mut latest = None;
    for entry in entries(root)? {
        let name = entry.file_name();
        let Some(name) = name.to_str() else { continue };
        if name.len() != 15 || !name.bytes().enumerate().all(|(i, b)| {
            if i == 8 { b == b'-' } else { b.is_ascii_digit() }
        }) {
            continue;
        }
        let metadata = fs::symlink_metadata(entry.path())?;
        if metadata.is_dir() && metadata.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT == 0 {
            latest = latest.max(Some(entry.path()));
        }
    }
    Ok(latest)
}

struct Stage(Option<PathBuf>);

impl Drop for Stage {
    fn drop(&mut self) {
        if let Some(path) = &self.0 {
            let _ = fs::remove_dir_all(path);
        }
    }
}

fn timestamp() -> String {
    let mut now = SYSTEMTIME::default();
    unsafe { GetLocalTime(&mut now) };
    format!("{:04}{:02}{:02}-{:02}{:02}{:02}", now.wYear, now.wMonth, now.wDay,
            now.wHour, now.wMinute, now.wSecond)
}

pub fn backup(install: &Path) -> io::Result<Backup> {
    let user = install.join("user");
    let files = save_files(&user)?;
    if files.is_empty() {
        return Ok(Backup::Empty);
    }
    let root = user.join(BACKUPS);
    fs::create_dir_all(&root)?;
    check_link(&root, &fs::symlink_metadata(&root)?)?;
    if let Some(latest) = latest_backup(&root)? {
        match matches_snapshot(&user, &latest, &files) {
            Ok(true) => return Ok(Backup::Unchanged),
            Ok(false) => {}
            Err(error) if error.kind() == io::ErrorKind::NotFound => {}
            Err(error) => return Err(error),
        }
    }
    let stage = loop {
        let number = NEXT_STAGE.fetch_add(1, Ordering::Relaxed);
        let candidate = root.join(format!(".launcher-stage-{}-{number}", std::process::id()));
        match fs::create_dir(&candidate) {
            Ok(()) => break candidate,
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(error),
        }
    };
    let mut cleanup = Stage(Some(stage.clone()));
    for relative in &files {
        let target = stage.join(relative);
        fs::create_dir_all(target.parent().expect("Save path has a parent"))?;
        fs::copy(user.join(relative), target)?;
    }
    fs::write(stage.join(NOTE), "manual backup from the native launcher\n")?;
    if !matches_snapshot(&user, &stage, &files)? {
        return Err(io::Error::other("Saves changed during the backup. Close the game and try again."));
    }

    let retry_until = Instant::now() + Duration::from_secs(3);
    loop {
        let target = root.join(timestamp());
        let from = super::preview::wide(stage.as_os_str());
        let to = super::preview::wide(target.as_os_str());
        if unsafe { MoveFileW(from.as_ptr(), to.as_ptr()) } != 0 {
            cleanup.0 = None;
            return Ok(Backup::Created(target));
        }
        let error = io::Error::last_os_error();
        if !target.exists() || Instant::now() >= retry_until {
            return Err(error);
        }
        std::thread::sleep(Duration::from_millis(100));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn backup_copies_save_trees_and_party_state_without_the_profile_config() {
        let root = std::env::temp_dir().join(format!(
            "yt-native-save-test-{}-{}", std::process::id(), NEXT_STAGE.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        let scratch = Stage(Some(root.clone()));
        assert_eq!(backup(&root).unwrap(), Backup::Empty);
        let user = root.join("user");
        fs::create_dir_all(user.join("savedata")).unwrap();
        fs::create_dir_all(user.join("home/test/savedata")).unwrap();
        for (relative, bytes) in [
            ("savedata/slot", "save"),
            ("home/test/savedata/slot", "another save"),
            ("bloodborne_party_test.txt", "party data"),
            ("coop.json", "private settings"),
        ] {
            fs::write(user.join(relative), bytes).unwrap();
        }
        let Backup::Created(snapshot) = backup(&root).unwrap() else {
            panic!("expected a new snapshot");
        };
        assert_eq!(snapshot.parent().unwrap(), user.join(BACKUPS));
        assert_eq!(snapshot.file_name().unwrap().len(), 15);
        assert!(snapshot.join(NOTE).is_file());
        assert_eq!(fs::read(snapshot.join("savedata/slot")).unwrap(), b"save");
        assert_eq!(fs::read(snapshot.join("home/test/savedata/slot")).unwrap(), b"another save");
        assert_eq!(fs::read(snapshot.join("bloodborne_party_test.txt")).unwrap(), b"party data");
        assert!(!snapshot.join("coop.json").exists());
        assert_eq!(backup(&root).unwrap(), Backup::Unchanged);
        assert_eq!(entries(&user.join(BACKUPS)).unwrap().len(), 1);
        drop(scratch);
    }
}
