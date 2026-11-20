# SPDX-License-Identifier: GPL-2.0-or-later
"""Windows desktop shortcuts using IShellLinkW and IPersistFile."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
from uuid import UUID

_HRESULT = C.c_long
_P = C.c_void_p


def _guid(value):
    return (C.c_ubyte * 16).from_buffer_copy(UUID(value).bytes_le)


def _checked(result, operation):
    if result < 0:
        raise OSError(f'{operation} failed (HRESULT 0x{result & 0xffffffff:08X})')


def _function(dll, name, result, *arguments):
    fn = getattr(dll, name)
    fn.restype, fn.argtypes = result, arguments
    return fn


def _method(obj, slot, result, *arguments):
    table = C.cast(obj, C.POINTER(C.POINTER(_P))).contents
    return C.WINFUNCTYPE(result, _P, *arguments)(table[slot])


def _desktop(shell, ole):
    # FOLDERID_Desktop respects redirection and can return a Unicode path.
    folder = _guid('B4BFCC3A-DB2C-424C-B029-7FE99A87C641')
    path = _P()
    get_path = _function(shell, 'SHGetKnownFolderPath', _HRESULT, _P, W.DWORD,
                         W.HANDLE, C.POINTER(_P))
    _checked(get_path(folder, 0, None, C.byref(path)), 'Find Desktop')
    try:
        return Path(C.wstring_at(path))
    finally:
        _function(ole, 'CoTaskMemFree', None, _P)(path)


def write_shortcut(target, directory, icon, arguments='', destination=None):
    """Save a link; `icon` is a (path, index) tuple and arguments are already quoted."""
    ole = C.WinDLL('ole32')
    shell = C.WinDLL('shell32')
    initialize = _function(ole, 'CoInitializeEx', _HRESULT, _P, W.DWORD)
    uninitialize = _function(ole, 'CoUninitialize', None)
    result = initialize(None, 2)  # COINIT_APARTMENTTHREADED
    if result != -2147417850:  # RPC_E_CHANGED_MODE: current apartment already initialized
        _checked(result, 'Initialize COM')
    link, persistence = _P(), _P()
    try:
        path = Path(destination) if destination is not None else _desktop(shell, ole) / 'Bloodborne.lnk'
        clsid = _guid('00021401-0000-0000-C000-000000000046')
        shell_link_w = _guid('000214F9-0000-0000-C000-000000000046')
        persist_file = _guid('0000010B-0000-0000-C000-000000000046')
        create = _function(ole, 'CoCreateInstance', _HRESULT, _P, _P, W.DWORD, _P, C.POINTER(_P))
        _checked(create(clsid, None, 1, shell_link_w, C.byref(link)), 'Create Shell Link')
        # Slots include IUnknown's three entries. These are the wide setters.
        for slot, value, operation in ((20, target, 'Set target'),
                                       (9, directory, 'Set working directory'),
                                       (11, arguments, 'Set arguments')):
            _checked(_method(link, slot, _HRESULT, W.LPCWSTR)(link, str(value)), operation)
        _checked(_method(link, 17, _HRESULT, W.LPCWSTR, C.c_int)(link, str(icon[0]), icon[1]),
                 'Set icon')
        query = _method(link, 0, _HRESULT, _P, C.POINTER(_P))
        _checked(query(link, persist_file, C.byref(persistence)), 'Get IPersistFile')
        _checked(_method(persistence, 6, _HRESULT, W.LPCWSTR, W.BOOL)(
            persistence, str(path), True), 'Save shortcut')
    finally:
        if persistence:
            _method(persistence, 2, W.ULONG)(persistence)
        if link:
            _method(link, 2, W.ULONG)(link)
        if result >= 0:
            uninitialize()
