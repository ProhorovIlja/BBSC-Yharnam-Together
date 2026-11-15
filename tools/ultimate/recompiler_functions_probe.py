"""Exercise the pinned recompiler's whole-function ABI using invented x86 bytes.

The fixture layout/ELF approach is informed by V395/V401 in
https://github.com/ProhorovIlja/bloodborne_pc_windows_port at
f151b8f79ee6bbaee81797efcc8b146845e2db09; this is a new independent harness.
It never reads a game image or enables production AOT dispatch.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess

from recompiler_probe import BBCPU, RECOMP, pinned

# Original test instructions, not extracted from any game.
FUNCTIONS = (
    (0x1000, '488d0437c3', 'leaf_add'),
    (0x1020, 'e8dbffffff4883c003c3', 'direct_call_add3'),
    (0x1040, 'ffd04883c005c3', 'indirect_call_add5'),
    (0x1060, 'e99bffffff', 'tail_leaf'),
    (0x1080, '64488b042500000000c3', 'fs_zero_tcb'),
    (0x10a0, '65488b1c2540000000c3', 'gs_40_tcb_rbx'),
    (0x10c0, '0f05c3', 'negative_syscall'),
    (0x10e0, '64488b042540000000c3', 'negative_fs_nonzero'),
    (0x1100, '4883ec1048c704244d00000048c744240858000000ffd04883c4104883c005c3',
     'host_call_with_stack_args'),
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('recompiler', 'bbcpu', 'deps', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--sanitize', action='store_true', help='instrument generated C and test host')
    a = p.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        p.error('currently Linux x86-64 only')
    recomp, cpu, deps, out = [getattr(a, name).resolve() for name in
                              ('recompiler', 'bbcpu', 'deps', 'output')]
    pinned(recomp, RECOMP)
    pinned(cpu, BBCPU)
    if hashlib.sha256((deps / 'include/Zydis/Zydis.h').read_bytes()).hexdigest() != \
            '1481ee71bb4289fb7f6bb62cd0441e05229db66565ed8ba2c32a38486c77bb45':
        raise ValueError('use the reviewed isolated Zydis headers')
    if (recomp / 'tools/recomp/bbcpu_api').read_text().strip() != '4':
        raise ValueError('unexpected RcApi version')
    out.mkdir(parents=True, exist_ok=False)
    elf = bytearray(0x1200)
    elf[:64] = struct.pack('<16sHHIQQQIHHHHHH', b'\x7fELF\x02\x01\x01' + bytes(9),
                          2, 62, 1, 0x1000, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    elf[64:120] = struct.pack('<IIQQQQQQ', 1, 5, 0x1000, 0x1000, 0, 0x200, 0x200, 0x1000)
    for offset, code, _ in FUNCTIONS:
        body = bytes.fromhex(code)
        elf[offset:offset + len(body)] = body
    (out / 'invented.elf').write_bytes(elf)
    (out / 'functions.tsv').write_text('start\tsize\tinsns\tundecodable\n' + ''.join(
        f'0x{off:x}\t{len(bytes.fromhex(code))}\t{n}\t0\n'
        for (off, code, _), n in zip(FUNCTIONS, (2, 3, 3, 1, 2, 2, 2, 2, 7))))
    (out / 'imports.tsv').write_text('')
    (out / 'calls.tsv').write_text('')
    here = Path(__file__).resolve().parent

    def run(cmd, name, expected=0):
        env = dict(os.environ)
        if a.sanitize:
            # LeakSanitizer cannot run inside this ptrace-backed host. Address
            # and undefined-behavior checks remain enabled and terminal.
            env.update(ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
                       UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        r = subprocess.run([str(x) for x in cmd], cwd=out, text=True,
                           capture_output=True, timeout=120, env=env)
        (out / (name + '.log')).write_text(r.stdout + r.stderr)
        if r.returncode != expected:
            raise RuntimeError(f'{name}: expected {expected}, got {r.returncode}; inspect log')
        return r.stdout

    generated = out / 'functions.c'
    run([recomp / 'out/recomp/bbrecomp', out / 'invented.elf', out / 'functions.tsv',
         generated, *[hex(f[0]) for f in FUNCTIONS]], 'generate')
    shard = out / 'functions_00000.c'
    source = shard.read_text()
    for off, _, _ in FUNCTIONS:
        if source.count(f'void f_{off:x}(BbCpu *c) {{') != 1:
            raise ValueError('missing or duplicated whole generated function')
    # Unsupported functions must stay quarantined; their callback is terminal.
    scopes = {off: source.split(f'void f_{off:x}(BbCpu *c) {{', 1)[1].split('\n}\n', 1)[0]
              for off, _, _ in FUNCTIONS}
    for off in (0x1000, 0x1020, 0x1040, 0x1060, 0x1080, 0x10a0, 0x1100):
        # The generator always emits a generic dispatch/bail epilogue, even
        # behind unconditional RET. Actual callback counters below police it.
        if 'rc->step(' in scopes[off]:
            raise ValueError('supported fixture unexpectedly requires fallback')
    for off in (0x1080, 0x10a0):
        if 'c->tcb' not in scopes[off]:
            raise ValueError('TCB normalization missing')
    if 'rc->call(' not in scopes[0x1040] or 'rc->step(' not in scopes[0x10e0]:
        raise ValueError('indirect dispatch/FS-negative fixture did not exercise expected path')
    exe = out / 'function_probe'
    instrument = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                  '-fno-pie', '-no-pie'] if a.sanitize else []
    run([here / 'recompiler-linux-gcc.sh', '-O2', '-std=gnu11', '-Wall', '-Wextra', *instrument,
         '-I' + str(cpu / 'src'), '-I' + str(deps / 'include'), generated, shard,
         here / 'recompiler_functions_host.c', '-o', exe], 'compile')
    result = json.loads(run([exe], 'execute'))
    run([exe, 'unknown'], 'reject_unknown', 81)
    run([exe, 'fs_nonzero'], 'reject_fs_nonzero', 83)
    run([exe, 'syscall'], 'reject_syscall', 83)
    evidence = dict(result, recompiler_commit=RECOMP, bbcpu_commit=BBCPU, api=4,
                    synthetic_functions=len(FUNCTIONS), host='linux-x86_64',
                    address_undefined_sanitizers=a.sanitize,
                    leak_checking=False,
                    fixture_sha256=hashlib.sha256(elf).hexdigest(),
                    generator_binary_sha256=hashlib.sha256(
                        (recomp / 'out/recomp/bbrecomp').read_bytes()).hexdigest(),
                    host_source_sha256=hashlib.sha256(
                        (here / 'recompiler_functions_host.c').read_bytes()).hexdigest(),
                    generated_sha256=hashlib.sha256(generated.read_bytes() + shard.read_bytes()).hexdigest(),
                    unknown_target_rejected=True, unsupported_fallback_terminal=True,
                    game_image_used=False, production_runtime_integrated=False,
                    windows_macos_tested=False, arm64_tested=False)
    (out / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
