#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright 2026 bbport contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Crash guards: unchecked game pointers and the GX LOD slot-claim race (game version
01.09; BB_CRASH_GUARDS=0 turns them off).

From Supermedo's bloodborne_pc (Supermedo/bloodborne_pc f1999924, "Crash guard: an online event
without its data no longer crashes the game"), GPL-2.0-or-later; the cave is at the same address as
there (code_cave.py).

- Online event without its data (0x1EB3D10, case 0). The game describes an event (r13: the event, its
  type the switch's value; r12: its data) and returns whether it could, the low byte of r12; an event
  type it does not know goes to 0x1EB3DD0: r12 = 0, "could not". Case 0 copies a string from r12 + 0x80
  without checking r12: a player online crashed there ("read access to 00000000000000a0
  at guest offset 0x1eb56b7") right after the server's ss.info request timed out. Case 0 with no data now
  goes the same way as an unknown event.

- GX LOD slot claims: atomically reserve a count below the slot capacity, preserving the registers
  consumed by the continuation. The exact original loop bytes are required; this is in-place and
  does not consume any Quit/Rebirth cave space. Imported from ayozetr/bloodborne_linux #53.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import code_cave as quit_menu  # noqa: E402

CAVE = quit_menu.CAVE + 0x1C0      # 0x50D98C0: there, the free tail of Quit to Desktop's cave
CAVE_END = quit_menu.CAVE + 0x200  # 0x50D9900: there, Rebirth's cave
EVENT_CASE = 0x1EB3DE8             # sub r12, -0x80; lea rdi, [rbp-0xa0]
EVENT_CASE_BYTES = bytes.fromhex('4983ec80488dbd60ffffff')
EVENT_UNKNOWN = 0x1EB3DD0          # xor r12d, r12d; jmp (the function's end): "could not"


def code_writes():
    cave = quit_menu.Code(CAVE)
    cave.raw('4d85e4')                                   # test r12, r12
    cave.data += b'\x0f\x84' + struct.pack('<i', EVENT_UNKNOWN - (cave.here + 6))   # jz: as unknown
    cave.data += EVENT_CASE_BYTES                        # the case's own first instructions
    cave.jmp(EVENT_CASE + len(EVENT_CASE_BYTES))
    if cave.here > CAVE_END:
        raise ValueError('crash guards do not fit')
    site = quit_menu.Code(EVENT_CASE)
    site.jmp(CAVE)
    site.data += b'\x90' * (len(EVENT_CASE_BYTES) - len(site.data))
    return [(cave.offset, bytes(cave.data)), (site.offset, bytes(site.data))]


def check_original(image_bytes):
    if image_bytes(EVENT_CASE, EVENT_CASE + len(EVENT_CASE_BYTES)) != EVENT_CASE_BYTES:
        raise ValueError(f'Crash guards: unexpected code at {EVENT_CASE + quit_menu.EBOOT_BASE:#x}')


# Atomic LOD claim from ayozetr/bloodborne_linux PR #53, head
# 156e0d6aee62a7cd1840b385455f7801b3964f1c (GPL-2.0-or-later).
# Keep this branch's existing Quit/Rebirth cave allocation unchanged.
LOD_CLAIM = 0x22453A4              # lea rax, [rdi+0xa0]: the slot loop of 0x2245320
LOD_CLAIM_END = 0x2245401          # on with the element: rsi slot, ecx count, rdx element
LOD_ALL_FULL = 0x2246C47           # every slot full: the function returns r15 (0)
LOD_CLAIM_BYTES = bytes.fromhex(
    '488d87a0000000'               # lea rax, [rdi+0xa0]
    '0f1f440000'                   # nop
    '89ca'                         # mov edx, ecx
    '83fa03'                       # cmp edx, 3
    '7717'                         # ja (past the slots)
    '89d1'                         # mov ecx, edx
    '8bb48f00010000'               # mov esi, [rdi+rcx*4+0x100]        the count
    '488d1c49'                     # lea rbx, [rcx+rcx*2]
    '8d4a01'                       # lea ecx, [rdx+1]
    '483b74d808'                   # cmp rsi, [rax+rbx*8+0x8]           against the capacity
    '73e2'                         # jae (the next slot)
    '4531ff'                       # xor r15d, r15d
    '83fa04'                       # cmp edx, 4
    '0f846d180000'                 # je 0x2246c47                       every slot full
    '89d6'                         # mov esi, edx
    '8b8cb700010000'               # mov ecx, [rdi+rsi*4+0x100]        the count, read again
    '488d1476'                     # lea rdx, [rsi+rsi*2]
    '4c8b4cd010'                   # mov r9, [rax+rdx*8+0x10]           the elements
    '4c69d1d0030000'               # imul r10, rcx, 0x3d0
    '4b8d1411'                     # lea rdx, [r9+r10]
    '8d4101'                       # lea eax, [rcx+1]
    '8984b700010000')              # mov [rdi+rsi*4+0x100], eax        count + 1, unlocked


class LodCode(quit_menu.Code):
    def short(self, opcode, target=None):
        """A two-byte jump (jcc rel8 or jmp rel8); without a target, one to fill in with land()."""
        at = len(self.data)
        self.data += bytes([opcode, 0])
        if target is not None:
            self.land(at, target)
        return at

    def land(self, at, target=None):
        """The short jump at data offset `at` goes to target (by default: here)."""
        target = self.here if target is None else target
        distance = target - (self.offset + at + 2)
        if not -128 <= distance <= 127:
            raise ValueError('short jump out of range')
        self.data[at + 1] = distance & 0xFF


def lod_claim_code():
    """The atomic slot claim, in place of LOD_CLAIM_BYTES (entry: rdi owner, ecx first slot, r8 the
    stack guard's pointer, kept). Out as the game's loop: rsi = slot, ecx = claimed count, eax = count
    + 1, rbx = slot * 3, r9 = the slot's elements, r10 = count * 0x3d0, rdx = r9 + r10, r15d = 0; every
    slot full (or a first slot past 3): to LOD_ALL_FULL with r15d = 0."""
    c = LodCode(LOD_CLAIM)
    c.raw('4531ff')                              # xor r15d, r15d
    next_slot = c.here
    c.raw('83f903')                              # cmp ecx, 3
    past_slots = c.short(0x77)                   # ja: every slot full
    c.raw('89ce')                                # mov esi, ecx
    c.raw('488d1c76')                            # lea rbx, [rsi+rsi*2]
    retry = c.here
    c.raw('8b84b700010000')                      # mov eax, [rdi+rsi*4+0x100]
    c.raw('483b84dfa8000000')                    # cmp rax, [rdi+rbx*8+0xa8]
    slot_full = c.short(0x73)                    # jae: the next slot
    c.raw('8d4801')                              # lea ecx, [rax+1]
    c.raw('f00fb18cb700010000')                  # lock cmpxchg [rdi+rsi*4+0x100], ecx
    c.short(0x75, retry)                         # jne: another worker claimed first
    c.raw('4c8b8cdfb0000000')                    # mov r9, [rdi+rbx*8+0xb0]
    c.raw('4c69d0d0030000')                      # imul r10, rax, 0x3d0
    c.raw('4b8d1411')                            # lea rdx, [r9+r10]
    c.raw('91')                                  # xchg eax, ecx
    c.short(0xEB, LOD_CLAIM_END)                 # jmp: on with the element
    c.land(slot_full)
    c.raw('8d4e01')                              # lea ecx, [rsi+1]
    c.short(0xEB, next_slot)                     # jmp
    c.land(past_slots)
    c.jmp(LOD_ALL_FULL)
    if c.here > LOD_CLAIM_END:
        raise ValueError('the LOD slot claim does not fit')
    c.data += b'\x90' * (LOD_CLAIM_END - c.here)
    return c.offset, bytes(c.data)


def check_lod_original(image_bytes):
    if image_bytes(LOD_CLAIM, LOD_CLAIM_END) != LOD_CLAIM_BYTES:
        raise ValueError(f'GX LOD claim: unexpected code at {LOD_CLAIM + quit_menu.EBOOT_BASE:#x}')
