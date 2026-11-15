# SPDX-License-Identifier: GPL-2.0-or-later
"""Export the actual production guard bytes for the native isolated harness."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'bbport/scripts'))
import crash_guards

original = crash_guards.LOD_CLAIM_BYTES
offset, patched = crash_guards.lod_claim_code()
assert offset == crash_guards.LOD_CLAIM
assert len(original) == len(patched) == crash_guards.LOD_CLAIM_END - offset
text = '// Generated from the production crash_guards module; no game file is loaded.\n'
for name, data in [('OriginalClaim', original), ('PatchedClaim', patched)]:
    text += 'static constexpr unsigned char ' + name + '[] = {'
    text += ','.join(hex(b) for b in data) + '};\n'
text += f'static constexpr size_t ClaimDone = {len(original)};\n'
text += f'static constexpr size_t ClaimFull = {crash_guards.LOD_ALL_FULL - offset};\n'
Path(sys.argv[1]).write_text(text)
