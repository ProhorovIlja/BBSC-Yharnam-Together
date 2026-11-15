# SPDX-License-Identifier: GPL-2.0-or-later
"""Crash guards (crash_guards.py, from Supermedo's bloodborne_pc f1999924): the guard's code, and
patches.py's crash_guards (always on for a patched game, at any frame rate)."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import code_cave  # noqa: E402
import crash_guards  # noqa: E402
import patches  # noqa: E402

SEGMENTS = [(0, code_cave.CODE_END), (0x50DC000, 0x56D30F4)]


def target(code, at, length):
    """Where the rel32 jump ending at `at + length` in `code` (placed at its offset) goes."""
    return code[0] + at + length + struct.unpack_from('<i', code[1], at + length - 4)[0]


def original(start, end):
    data = crash_guards.EVENT_CASE_BYTES if start == crash_guards.EVENT_CASE else b''
    return (data + bytes(end - start))[:end - start]


class CrashGuardsTest(unittest.TestCase):
    def test_the_guard_keeps_upstreams_address_in_the_last_code_page(self):
        (cave, code), _site = crash_guards.code_writes()
        self.assertEqual(cave, 0x50D98C0)
        self.assertGreaterEqual(cave, code_cave.CAVE)
        self.assertLessEqual(cave + len(code), crash_guards.CAVE_END)
        self.assertLessEqual(crash_guards.CAVE_END, code_cave.CAVE_END)

    def test_no_data_goes_where_an_unknown_event_goes_and_data_carries_on(self):
        (cave, code), (site, jump) = crash_guards.code_writes()
        self.assertEqual(code[:3], bytes.fromhex('4d85e4'))                      # test r12, r12
        self.assertEqual(code[3:5], b'\x0f\x84')                                 # jz rel32
        self.assertEqual(target((cave, code), 3, 6), crash_guards.EVENT_UNKNOWN)
        self.assertEqual(code[9:20], crash_guards.EVENT_CASE_BYTES)
        self.assertEqual(code[20], 0xE9)
        self.assertEqual(target((cave, code), 20, 5), crash_guards.EVENT_CASE + 11)
        self.assertEqual(len(code), 25)
        self.assertEqual(site, crash_guards.EVENT_CASE)
        self.assertEqual(len(jump), len(crash_guards.EVENT_CASE_BYTES))
        self.assertEqual(jump[0], 0xE9)
        self.assertEqual(target((site, jump), 0, 5), cave)
        self.assertTrue(all(b == 0x90 for b in jump[5:]))

    def test_other_code_at_the_site_is_refused(self):
        crash_guards.check_original(lambda start, end: crash_guards.EVENT_CASE_BYTES)
        with self.assertRaises(ValueError):
            crash_guards.check_original(lambda start, end: b'\x90' * (end - start))


class PatchesCrashGuardsTest(unittest.TestCase):
    def guards(self, env=None, image_bytes=original, segments=SEGMENTS):
        return patches.crash_guards(image_bytes, segments, env or {})

    def test_on_at_any_frame_rate(self):
        named = self.guards()
        self.assertEqual({name for name, _, _ in named}, {'Crash guards'})
        self.assertEqual([(offset, data) for _, offset, data in named], crash_guards.code_writes())

    def test_turns_off(self):
        self.assertEqual(self.guards(env={'BB_CRASH_GUARDS': '0'}), [])

    def test_other_code_at_the_site_skips_it(self):
        self.assertEqual(self.guards(image_bytes=lambda start, end: bytes(end - start)), [])

    def test_another_segment_layout_skips_it(self):
        self.assertEqual(self.guards(segments=[(0, code_cave.CODE_END - 0x10)]), [])

    def test_it_is_no_gameplay_patch_and_touches_no_co_op_site(self):
        named = self.guards()
        gameplay, other = patches.build_check_names([name for name, _, _ in named])
        self.assertEqual(gameplay, [])
        self.assertEqual(patches.coop_conflicts(named), [])
        # Nor within 48 bytes of one (the frame-rate fixes' rule, docs/FRAME_RATE_FIXES.md).
        for site in patches.load_coop_sites()['sites']:
            start, end = site['offset'] - 48, site['offset'] + len(site['original']) + 48
            for _, offset, data in named:
                self.assertFalse(offset < end and start < offset + len(data), site['name'])


def original_with_lod(start, end):
    data = (crash_guards.LOD_CLAIM_BYTES if start == crash_guards.LOD_CLAIM else
            crash_guards.EVENT_CASE_BYTES if start == crash_guards.EVENT_CASE else b'')
    return (data + bytes(end - start))[:end - start]


class LodClaimTests(unittest.TestCase):
    def test_exact_span_and_bounded_atomic_claim(self):
        offset, code = crash_guards.lod_claim_code()
        self.assertEqual(offset, crash_guards.LOD_CLAIM)
        self.assertEqual(offset + len(code), crash_guards.LOD_CLAIM_END)
        self.assertEqual(len(code), 93)
        bound = code.index(bytes.fromhex('483b84dfa8000000'))
        claim = code.index(bytes.fromhex('f00fb18cb700010000'))
        self.assertLess(bound, claim)
        self.assertEqual(code[bound + 8], 0x73)
        self.assertEqual(code[claim - 3:claim], bytes.fromhex('8d4801'))

    def test_original_bytes_are_required(self):
        crash_guards.check_lod_original(original_with_lod)
        with self.assertRaises(ValueError):
            crash_guards.check_lod_original(lambda start, end: bytes(end - start))

    def test_jump_targets_decode_at_instruction_boundaries(self):
        offset, code = crash_guards.lod_claim_code()
        plain = [bytes.fromhex(h) for h in (
            '4531ff', '83f903', '89ce', '488d1c76', '8b84b700010000', '483b84dfa8000000',
            '8d4801', 'f00fb18cb700010000', '4c8b8cdfb0000000', '4c69d0d0030000',
            '4b8d1411', '91', '8d4e01', '90')]
        jumps = []
        boundaries = set()
        at = 0
        while at < len(code):
            boundaries.add(offset + at)
            known = next((p for p in plain if code.startswith(p, at)), None)
            if known:
                at += len(known)
            elif code[at] in (0x77, 0x73, 0x75, 0xEB):
                destination = offset + at + 2 + struct.unpack_from('b', code, at + 1)[0]
                jumps.append((code[at], destination))
                at += 2
            elif code[at] == 0xE9:
                jumps.append((0xE9, target((offset, code), at, 5)))
                at += 5
            else:
                self.fail(f'Unexpected instruction at +{at:#x}')
        allowed = boundaries | {crash_guards.LOD_CLAIM_END, crash_guards.LOD_ALL_FULL}
        for _, destination in jumps:
            self.assertIn(destination, allowed)
        self.assertIn((0xE9, crash_guards.LOD_ALL_FULL), jumps)
        self.assertIn((0x75, offset + code.index(bytes.fromhex('8b84b700010000'))), jumps)
        self.assertIn((0xEB, crash_guards.LOD_CLAIM_END), jumps)

    def test_both_guards_preserve_the_existing_cave_and_coop_sites(self):
        named = patches.crash_guards(original_with_lod, SEGMENTS, {})
        self.assertEqual([(offset, data) for _, offset, data in named],
                         crash_guards.code_writes() + [crash_guards.lod_claim_code()])
        self.assertEqual(crash_guards.code_writes()[0][0], 0x50D98C0)
        self.assertEqual(patches.coop_conflicts(named), [])
        self.assertEqual(patches.build_check_names([name for name, _, _ in named])[0], [])
        for _, offset, data in named:
            for site in patches.load_coop_sites()['sites']:
                self.assertFalse(offset < site['offset'] + len(site['original']) + 48
                                 and site['offset'] - 48 < offset + len(data), site['name'])

    def test_mismatched_lod_keeps_the_existing_online_guard(self):
        named = patches.crash_guards(original, SEGMENTS, {})
        self.assertEqual([(offset, data) for _, offset, data in named], crash_guards.code_writes())

    def test_mismatched_event_keeps_the_in_place_lod_guard(self):
        def lod_only(start, end):
            return original_with_lod(start, end) if start == crash_guards.LOD_CLAIM else bytes(end-start)
        named = patches.crash_guards(lod_only, SEGMENTS, {})
        self.assertEqual([(offset, data) for _, offset, data in named], [crash_guards.lod_claim_code()])

    def test_switch_and_incompatible_layout_refuse_all_guards(self):
        self.assertEqual(patches.crash_guards(original_with_lod, SEGMENTS, {'BB_CRASH_GUARDS':'0'}), [])
        self.assertEqual(patches.crash_guards(original_with_lod, [(0,0x1000)], {}), [])


if __name__ == '__main__':
    unittest.main()
