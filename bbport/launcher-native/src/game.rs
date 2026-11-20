use std::fs::File;
use std::io::{self, Read};
use std::path::Path;

const TITLE_IDS: [&str; 9] = [
    "CUSA03173", "CUSA00207", "CUSA00208", "CUSA00900", "CUSA03179", "CUSA01363", "CUSA03023",
    "CUSA00299", "CUSA03014",
];

#[derive(Debug, PartialEq, Eq)]
pub struct Game {
    pub title: String,
    pub version: String,
    pub separate_update: bool,
}

impl Game {
    pub fn inspect(eboot: &Path) -> io::Result<Self> {
        if !eboot
            .file_name()
            .is_some_and(|name| name.eq_ignore_ascii_case("eboot.bin"))
            || !eboot.is_file()
        {
            return Err(invalid("Choose the eboot.bin in your Bloodborne game folder."));
        }
        let folder = eboot.parent().ok_or_else(|| invalid("Game folder is missing."))?;
        let mut game = read_game(folder)?;
        if !TITLE_IDS.contains(&game.title.as_str()) {
            return Err(invalid("The selected game is not a supported Bloodborne edition."));
        }
        if game.version != "01.09" {
            if let (Some(parent), Some(name)) = (folder.parent(), folder.file_name()) {
                let mut by_folder = name.to_os_string();
                by_folder.push("-patch");
                let by_title = format!("{}-patch", game.title);
                for update in [parent.join(by_folder), parent.join(by_title)] {
                    if update.join("eboot.bin").is_file()
                        && read_game(&update).is_ok_and(|patch| {
                            patch.title == game.title && patch.version == "01.09"
                        })
                    {
                        game.version = "01.09".into();
                        game.separate_update = true;
                        break;
                    }
                }
            }
        }
        Ok(game)
    }

    pub fn summary(&self) -> String {
        let status = match (self.version.as_str(), self.separate_update) {
            ("01.09", true) => "Adjacent 1.09 update found",
            ("01.09", false) => "Version 1.09 found",
            _ => "Co-op requires the 1.09 update",
        };
        format!("{}  ·  {}  ·  {status}", self.title, self.version)
    }
}

fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message)
}

fn read_game(folder: &Path) -> io::Result<Game> {
    const LIMIT: u64 = 1024 * 1024;
    let mut data = Vec::new();
    File::open(folder.join("sce_sys").join("param.sfo"))
        .map_err(|error| io::Error::new(error.kind(), "Could not open sce_sys/param.sfo."))?
        .take(LIMIT + 1)
        .read_to_end(&mut data)?;
    if data.len() as u64 > LIMIT {
        return Err(invalid("Game metadata exceeds the supported size."));
    }
    parse_sfo(&data).ok_or_else(|| invalid("Game metadata is missing a valid title or version."))
}

fn u16_at(data: &[u8], offset: usize) -> Option<u16> {
    Some(u16::from_le_bytes(data.get(offset..offset.checked_add(2)?)?.try_into().ok()?))
}

fn u32_at(data: &[u8], offset: usize) -> Option<usize> {
    let bytes = data.get(offset..offset.checked_add(4)?)?.try_into().ok()?;
    usize::try_from(u32::from_le_bytes(bytes)).ok()
}

fn parse_sfo(data: &[u8]) -> Option<Game> {
    if !data.starts_with(b"\0PSF") {
        return None;
    }
    let keys = u32_at(data, 8)?;
    let values = u32_at(data, 12)?;
    let count = u32_at(data, 16)?;
    if count > 256 || 20 + count * 16 > keys || keys > values || values > data.len() {
        return None;
    }
    let (mut title, mut version) = (None, None);
    for entry in (20..20 + count * 16).step_by(16) {
        let key_start = keys.checked_add(usize::from(u16_at(data, entry)?))?;
        let key_storage = data.get(key_start..values)?;
        let key = key_storage.get(..key_storage.iter().position(|&byte| byte == 0)?)?;
        let target = match key {
            b"TITLE_ID" => &mut title,
            b"APP_VER" => &mut version,
            _ => continue,
        };
        if u16_at(data, entry + 2)? != 0x0204 {
            return None;
        }
        let data_start = values.checked_add(u32_at(data, entry + 12)?)?;
        let data_end = data_start.checked_add(u32_at(data, entry + 4)?)?;
        let value = std::str::from_utf8(data.get(data_start..data_end)?).ok()?.trim_end_matches('\0');
        if value.is_empty() || value.chars().any(char::is_control) || target.is_some() {
            return None;
        }
        *target = Some(value.to_owned());
    }
    Some(Game { title: title?, version: version?, separate_update: false })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> Vec<u8> {
        let keys = b"TITLE_ID\0APP_VER\0";
        let mut data = b"\0PSF\x01\x01\0\0".to_vec();
        for number in [52u32, 52 + keys.len() as u32, 2] {
            data.extend_from_slice(&number.to_le_bytes());
        }
        for (name, length, value) in [(0u16, 10u32, 0u32), (9, 6, 10)] {
            data.extend_from_slice(&name.to_le_bytes());
            data.extend_from_slice(&0x0204u16.to_le_bytes());
            for number in [length, length, value] {
                data.extend_from_slice(&number.to_le_bytes());
            }
        }
        data.extend_from_slice(keys);
        data.extend_from_slice(b"CUSA03173\x0001.09\0");
        data
    }

    #[test]
    fn reads_retail_title_and_version() {
        let game = parse_sfo(&sample()).unwrap();
        assert_eq!(game.title, "CUSA03173");
        assert_eq!(game.version, "01.09");
    }

    #[test]
    fn rejects_truncated_records_and_overflowed_value_offsets() {
        let mut data = sample();
        assert!(parse_sfo(&data[..data.len() - 1]).is_none());
        data[32..36].copy_from_slice(&u32::MAX.to_le_bytes());
        assert!(parse_sfo(&data).is_none());
    }

    #[test]
    fn adjacent_update_must_match_the_selected_edition() {
        let root = std::env::temp_dir().join(format!(
            "yt-native-game-check-{}-{:?}",
            std::process::id(),
            std::thread::current().id()
        ));
        std::fs::create_dir(&root).unwrap();
        struct Scratch(std::path::PathBuf);
        impl Drop for Scratch {
            fn drop(&mut self) {
                let _ = std::fs::remove_dir_all(&self.0);
            }
        }
        let scratch = Scratch(root);
        let base = scratch.0.join("Bloodborne");
        let patch = scratch.0.join("CUSA03173-patch");
        for folder in [&base, &patch] {
            std::fs::create_dir_all(folder.join("sce_sys")).unwrap();
            std::fs::write(folder.join("eboot.bin"), []).unwrap();
        }
        let mut base_sfo = sample();
        let version_offset = base_sfo.len() - 6;
        base_sfo[version_offset..version_offset + 5].copy_from_slice(b"01.00");
        std::fs::write(base.join("sce_sys/param.sfo"), base_sfo).unwrap();

        let mut wrong_edition = sample();
        let title_offset = wrong_edition.len() - 16;
        wrong_edition[title_offset..title_offset + 9].copy_from_slice(b"CUSA00900");
        std::fs::write(patch.join("sce_sys/param.sfo"), wrong_edition).unwrap();
        let eboot = base.join("eboot.bin");
        assert_eq!(Game::inspect(&eboot).unwrap().version, "01.00");

        std::fs::write(patch.join("sce_sys/param.sfo"), sample()).unwrap();
        let checked = Game::inspect(&eboot).unwrap();
        assert_eq!(checked.version, "01.09");
        assert!(checked.separate_update);
    }
}
