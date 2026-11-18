use jpeg_decoder::{Decoder, PixelFormat};
use std::io;
use std::sync::OnceLock;
use windows_sys::Win32::Foundation::{HWND, RECT};
use windows_sys::Win32::Graphics::Gdi::*;
use windows_sys::Win32::UI::Controls::{DRAWITEMSTRUCT, ODS_DISABLED, ODS_FOCUS, ODS_SELECTED};
use windows_sys::Win32::UI::WindowsAndMessaging::GetClientRect;

const fn rgb(r: u32, g: u32, b: u32) -> u32 {
    r | (g << 8) | (b << 16)
}

const SIDEBAR: u32 = rgb(13, 15, 19);
const PANEL: u32 = rgb(18, 21, 26);
const CARD: u32 = rgb(25, 28, 34);
const LINE: u32 = rgb(54, 49, 42);
const GOLD: u32 = rgb(213, 177, 115);
const TEXT: u32 = rgb(232, 226, 216);
const MUTED: u32 = rgb(167, 162, 154);
const CONTENT_LEFT: i32 = 264;

static STREET: OnceLock<StreetArt> = OnceLock::new();

struct StreetArt {
    width: i32,
    height: i32,
    pixels: Vec<u8>,
}

pub fn load_street_art() -> io::Result<()> {
    let mut decoder = Decoder::new(&include_bytes!("../../launcher/art/home-banner.jpg")[..]);
    let rgb_pixels = decoder.decode().map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    let info = decoder.info().ok_or(io::ErrorKind::InvalidData)?;
    if info.pixel_format != PixelFormat::RGB24 {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "Expected RGB launcher art."));
    }
    let mut pixels = Vec::with_capacity(rgb_pixels.len() / 3 * 4);
    for rgb in rgb_pixels.chunks_exact(3) {
        pixels.extend_from_slice(&[rgb[2], rgb[1], rgb[0], 0]);
    }
    let _ = STREET.set(StreetArt { width: info.width.into(), height: info.height.into(), pixels });
    Ok(())
}

fn rect(left: i32, top: i32, right: i32, bottom: i32) -> RECT {
    RECT { left, top, right, bottom }
}

unsafe fn fill(dc: HDC, area: &RECT, color: u32) {
    let brush = CreateSolidBrush(color);
    if !brush.is_null() {
        FillRect(dc, area, brush);
        DeleteObject(brush);
    }
}

unsafe fn label(dc: HDC, mut area: RECT, text: &str, size: i32, color: u32, centered: bool) {
    let face = if size >= 24 { "Georgia" } else { "Segoe UI" };
    let face = super::preview::wide(face);
    let font = CreateFontW(-size, 0, 0, 0, if size >= 24 { 600 } else { 400 }, 0, 0, 0,
                           DEFAULT_CHARSET.into(), 0, 0, CLEARTYPE_QUALITY.into(), 0, face.as_ptr());
    if font.is_null() {
        return;
    }
    let old_font = SelectObject(dc, font);
    SetBkMode(dc, TRANSPARENT as i32);
    SetTextColor(dc, color);
    let wide = super::preview::wide(text);
    let align = if centered { DT_CENTER } else { DT_LEFT };
    DrawTextW(dc, wide.as_ptr(), -1, &mut area, align | DT_SINGLELINE | DT_VCENTER | DT_END_ELLIPSIS | DT_NOPREFIX);
    SelectObject(dc, old_font);
    DeleteObject(font);
}

unsafe fn street(dc: HDC, x: i32, y: i32, width: i32) {
    let Some(art) = STREET.get() else { return };
    let height = 164;
    let source_width = (art.height * width / height).min(art.width);
    let info = BITMAPINFO {
        bmiHeader: BITMAPINFOHEADER {
            biSize: std::mem::size_of::<BITMAPINFOHEADER>() as u32,
            biWidth: art.width,
            biHeight: -art.height,
            biPlanes: 1,
            biBitCount: 32,
            biCompression: BI_RGB,
            ..BITMAPINFOHEADER::default()
        },
        ..BITMAPINFO::default()
    };
    SetStretchBltMode(dc, HALFTONE);
    StretchDIBits(dc, x, y, width, height, (art.width - source_width) / 2, 0, source_width, art.height,
                  art.pixels.as_ptr().cast(), &info, DIB_RGB_COLORS, SRCCOPY);
}

pub unsafe fn paint(hwnd: HWND, has_launcher: bool) {
    let mut paint = PAINTSTRUCT::default();
    let dc = BeginPaint(hwnd, &mut paint);
    if !dc.is_null() {
        let mut bounds = RECT::default();
        GetClientRect(hwnd, &mut bounds);
        let right = bounds.right - 28;
        fill(dc, &bounds, PANEL);
        fill(dc, &rect(0, 0, 232, bounds.bottom), SIDEBAR);
        fill(dc, &rect(231, 0, 232, bounds.bottom), LINE);
        label(dc, rect(25, 37, 219, 76), "Yharnam", 32, GOLD, false);
        label(dc, rect(27, 74, 219, 102), "TOGETHER", 15, TEXT, false);
        fill(dc, &rect(26, 119, 207, 120), LINE);
        fill(dc, &rect(15, 143, 218, 185), CARD);
        fill(dc, &rect(15, 143, 18, 185), GOLD);
        label(dc, rect(29, 144, 209, 185), "Home", 17, GOLD, false);

        label(dc, rect(CONTENT_LEFT, 22, right, 60), "Home", 28, TEXT, false);
        if right > CONTENT_LEFT {
            street(dc, CONTENT_LEFT, 76, right - CONTENT_LEFT);
        }
        fill(dc, &rect(CONTENT_LEFT, 239, right, 241), GOLD);
        label(dc, rect(CONTENT_LEFT, 259, right, 300), "Bloodborne Seamless Co-op", 30, GOLD, false);
        let detail = if has_launcher {
            "Play uses your existing installation and settings."
        } else {
            "Attach an existing launcher to enable Play and Settings."
        };
        label(dc, rect(CONTENT_LEFT, 306, right, 335), detail, 16, MUTED, false);
    }
    EndPaint(hwnd, &paint);
}

pub unsafe fn paint_button(item: &DRAWITEMSTRUCT, play: bool) {
    let disabled = item.itemState & ODS_DISABLED != 0;
    let active = item.itemState & ODS_SELECTED != 0;
    let focused = item.itemState & ODS_FOCUS != 0;
    let color = if play && !disabled { GOLD } else { MUTED };
    fill(item.hDC, &item.rcItem, if focused || active { GOLD } else { LINE });
    let inner = rect(item.rcItem.left + 1, item.rcItem.top + 1, item.rcItem.right - 1, item.rcItem.bottom - 1);
    fill(item.hDC, &inner, if active { PANEL } else { CARD });
    label(item.hDC, inner, if play { "PLAY" } else { "Settings" }, 16, color, true);
}
