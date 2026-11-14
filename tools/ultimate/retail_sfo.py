# SPDX-License-Identifier: GPL-2.0-or-later
"""Read PS4 param.sfo identity for first-run diagnostics, not approval."""
import re
import struct

MAX_BYTES = 65536


def identify(data: bytes) -> tuple[str, str]:
    """Return TITLE_ID and APP_VER; ignore folder and localized title names."""
    if not 20 <= len(data) <= MAX_BYTES or data[:4] != b'\x00PSF':
        raise ValueError('invalid SFO header or size')
    _, keys, values, count = struct.unpack_from('<4I', data, 4)
    if count > 512 or not 20 + count * 16 <= keys <= values <= len(data):
        raise ValueError('invalid SFO tables')
    identity = {}
    for i in range(count):
        entry = 20 + 16 * i
        key, = struct.unpack_from('<H', data, entry)
        fmt, = struct.unpack_from('>H', data, entry + 2)
        length, capacity, offset = struct.unpack_from('<III', data, entry + 4)
        start = keys + key
        end = data.find(b'\0', start, values)
        if end <= start or not 0 < length <= capacity or values + offset + capacity > len(data):
            raise ValueError('invalid SFO entry')
        name = data[start:end]
        if name not in (b'TITLE_ID', b'APP_VER'):
            continue
        raw = data[values + offset:values + offset + length]
        if name in identity or fmt != 0x0204 or not raw.endswith(b'\0'):
            raise ValueError('invalid SFO identity field')
        identity[name] = raw[:-1]
    title = identity.get(b'TITLE_ID', b'')
    version = identity.get(b'APP_VER', b'')
    if not re.fullmatch(rb'CUSA[0-9]{5}', title) or not re.fullmatch(rb'[0-9]{2}\.[0-9]{2}', version):
        raise ValueError('missing or invalid title ID or application version')
    return title.decode('ascii'), version.decode('ascii')
