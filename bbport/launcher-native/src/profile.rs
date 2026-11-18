use serde_json::{Map, Value};
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::net::Ipv4Addr;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use windows_sys::Win32::Storage::FileSystem::{MoveFileExW, MOVEFILE_REPLACE_EXISTING, MOVEFILE_WRITE_THROUGH};

static NEXT_STAGE: AtomicUsize = AtomicUsize::new(0);

fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message)
}

fn host_name(host: &str) -> bool {
    if let Ok(address) = host.parse::<Ipv4Addr>() {
        return !address.is_loopback();
    }
    let valid_label = |label: &str| {
        !label.is_empty() && label.len() <= 63
            && label.as_bytes()[0].is_ascii_alphanumeric()
            && label.as_bytes()[label.len() - 1].is_ascii_alphanumeric()
            && label.bytes().all(|byte| byte.is_ascii_alphanumeric() || byte == b'-')
    };
    host.len() <= 253 && host.contains('.') && host.split('.').all(valid_label)
        && host.bytes().any(|byte| byte.is_ascii_alphabetic())
}

fn valid_address(address: &str) -> bool {
    if host_name(address) {
        return true;
    }
    let Some((scheme, rest)) = address.split_once("://") else { return false };
    if !scheme.eq_ignore_ascii_case("https")
        || rest.chars().any(|letter| letter.is_whitespace() || matches!(letter, '?' | '#'))
    {
        return false;
    }
    let authority = rest.split('/').next().unwrap_or_default();
    match authority.split_once(':') {
        Some((host, port)) => host_name(host)
            && !port.is_empty() && port.len() <= 5 && port.bytes().all(|byte| byte.is_ascii_digit())
            && port.parse::<u16>().is_ok_and(|port| port != 0),
        None => host_name(authority),
    }
}

fn read(install: &Path) -> io::Result<(Option<Vec<u8>>, Map<String, Value>)> {
    let path = install.join("user/coop.json");
    match fs::read(&path) {
        Ok(bytes) => {
            let profile: Value = serde_json::from_slice(&bytes)
                .map_err(|_| invalid("Existing co-op settings are unreadable. Open the legacy launcher to recover them."))?;
            let Value::Object(profile) = profile else {
                return Err(invalid("Existing co-op settings are not a JSON object."));
            };
            Ok((Some(bytes), profile))
        }
        Err(error) if error.kind() == io::ErrorKind::NotFound => {
            if install.join("settings.bat").is_file() {
                return Err(invalid("Open the legacy launcher once to migrate settings.bat."));
            }
            Ok((None, Map::new()))
        }
        Err(error) => Err(error),
    }
}

pub fn host(install: &Path) -> io::Result<String> {
    let (_, profile) = read(install)?;
    Ok(profile.get("host_ip").and_then(Value::as_str).unwrap_or("").into())
}

struct Pending(PathBuf);

impl Drop for Pending {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

pub fn save(install: &Path, game: Option<&Path>, host: &str) -> io::Result<()> {
    let host = host.trim();
    // The old launcher allows clearing a local address before finishing setup.
    if !host.is_empty() && !valid_address(host) {
        return Err(invalid("Enter an IPv4 address, server name, or HTTPS region directory."));
    }
    let (original, mut profile) = read(install)?;
    if let Some(game) = game {
        let game = game.to_str().ok_or_else(|| invalid("The game folder path cannot be saved as Unicode."))?;
        if profile.get("game").and_then(Value::as_str) != Some(game) {
            profile.insert("game".into(), Value::String(game.into()));
            profile.insert("prepared".into(), Value::String(String::new()));
            profile.insert("update".into(), Value::String(String::new()));
        }
    }
    profile.insert("host_ip".into(), Value::String(host.into()));
    let mut bytes = serde_json::to_vec_pretty(&profile)?;
    bytes.push(b'\n');
    let user = install.join("user");
    fs::create_dir_all(&user)?;
    let (pending, mut file) = loop {
        let name = format!(".coop-native-{}-{}.tmp", std::process::id(), NEXT_STAGE.fetch_add(1, Ordering::Relaxed));
        let pending = user.join(name);
        match OpenOptions::new().write(true).create_new(true).open(&pending) {
            Ok(file) => break (Pending(pending), file),
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(error),
        }
    };
    file.write_all(&bytes)?;
    file.sync_all()?;
    drop(file);
    if read(install)?.0 != original {
        return Err(io::Error::other("Co-op settings changed while saving. Reload the installation and try again."));
    }
    let path = user.join("coop.json");
    let source = super::preview::wide(pending.0.as_os_str());
    let target = super::preview::wide(path.as_os_str());
    // Do not replace a file that another process created since the initial read.
    let flags = MOVEFILE_WRITE_THROUGH | if original.is_some() { MOVEFILE_REPLACE_EXISTING } else { 0 };
    if unsafe { MoveFileExW(source.as_ptr(), target.as_ptr(), flags) } == 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn host_validation_matches_supported_connection_forms() {
        for good in ["192.168.0.2", "play.example.com", "HTTPS://eu.example.com:20443/region"] {
            assert!(valid_address(good), "{good}");
        }
        for bad in ["127.0.0.1", "999.0.0.1", "host", "http://play.example.com", "https://play.example.com:0", "https://user@play.example.com"] {
            assert!(!valid_address(bad), "{bad}");
        }
    }

    #[test]
    fn saves_game_and_host_without_discarding_other_settings() {
        let root = std::env::temp_dir().join(format!(
            "yt-native-profile-test-{}-{}", std::process::id(), NEXT_STAGE.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        let user = root.join("user");
        fs::create_dir(&user).unwrap();
        let path = user.join("coop.json");
        fs::write(&path, br#"{"game":"old","update":"old patch","prepared":"key","server_keys":{"test":"preserve"},"server_type":"global"}"#).unwrap();
        save(&root, Some(Path::new("D:/เกม/Bloodborne")), "play.example.com").unwrap();
        let (_, profile) = read(&root).unwrap();
        assert_eq!(profile["game"], "D:/เกม/Bloodborne");
        assert_eq!(profile["update"], "");
        assert_eq!(profile["prepared"], "");
        assert_eq!(profile["server_keys"]["test"], "preserve");
        assert_eq!(profile["server_type"], "global");
        assert_eq!(host(&root).unwrap(), "play.example.com");
        let broken = b"{broken json";
        fs::write(&path, broken).unwrap();
        assert!(save(&root, None, "play.example.com").is_err());
        assert_eq!(fs::read(&path).unwrap(), broken);
        fs::remove_dir_all(root).unwrap();
    }
}
