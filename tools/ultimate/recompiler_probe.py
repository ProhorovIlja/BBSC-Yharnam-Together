"""Pinned Linux x86-64 tool-intake test; synthetic instructions only, no game image.

Uses bloodborne-native/bloodborne-recomp's generator and differential fuzzer with
bbcpu's interpreter (GPL-2.0-or-later). Sources stay external; this tool imports no
game code and does not enable AOT execution in the production runtime.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess

RECOMP = 'c60ccf8be752b8690f2813505c4daf9eafdb136b'
BBCPU = '3f9b6c1a11d5a443ee2e556a0d1f3aec4a73f0ca'


def pinned(path, expected):
    sha = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
    if sha != expected:
        raise ValueError('checkout revision does not match the reviewed pin')
    subprocess.run(['git', '-C', str(path), 'diff', '--quiet', 'HEAD', '--'], check=True)
    if subprocess.check_output(['git', '-C', str(path), 'ls-files', '--others',
                                '--exclude-standard'], text=True).strip():
        raise ValueError('unexpected untracked donor files; use a clean checkout')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recompiler', type=Path, required=True)
    parser.add_argument('--bbcpu', type=Path, required=True)
    parser.add_argument('--deps', type=Path, required=True, help='Zydis4.1.1/Zycore install prefix')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--trials', type=int, default=1000)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        parser.error('this research probe currently requires Linux x86-64')
    if not 1 <= args.trials <= 10000:
        parser.error('trials must be in1..10000')
    recomp, cpu, deps, out = [p.resolve() for p in
                              (args.recompiler, args.bbcpu, args.deps, args.output)]
    pinned(recomp, RECOMP)
    pinned(cpu, BBCPU)
    api = (recomp / 'tools/recomp/bbcpu_api').read_text().strip()
    header = (cpu / 'src/recomp/rc.h').read_text()
    if not re.search(r'#define BB_RECOMP_API_VERSION ' + re.escape(api) + r'u\b', header):
        raise ValueError('recompiler/bbcpu API mismatch')
    zydis = (deps / 'include/Zydis/Zydis.h').read_bytes()
    # v4.1.1's public macro still spells4.1.0; pin its actual reviewed header bytes.
    if hashlib.sha256(zydis).hexdigest() != '1481ee71bb4289fb7f6bb62cd0441e05229db66565ed8ba2c32a38486c77bb45':
        raise ValueError('use the pinned Zydis4.1.1 headers, not the renderer decoder prefix')
    out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    wrapper = here / 'recompiler-linux-gcc.sh'
    env = dict(os.environ, BB_DEPS=str(deps), BBCPU=str(cpu), CC=str(wrapper),
               BB_CPU='interp', BB_JIT='0')

    def run(command, name, cwd=recomp, timeout=180):
        result = subprocess.run([str(c) for c in command], cwd=cwd, env=env,
                                text=True, capture_output=True, timeout=timeout)
        (out / (name + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(name + ' failed; inspect its log')
        return result.stdout

    run(['bash', 'build.sh'], 'build')
    hello = run([cpu / 'out/hello'], 'interpreter_hello')
    if hello.strip() != 'guest returned 42':
        raise RuntimeError('interpreter example returned an unexpected result')
    encodings = here / 'recompiler-probe-encodings.txt'
    generated = out / 'snippets.c'
    generated_log = run([recomp / 'out/recomp/bbrecomp', '--snippets', encodings, generated],
                        'generate')
    expected = len(encodings.read_text().splitlines())
    if not generated_log.startswith(str(expected) + ' instructions translated natively'):
        raise RuntimeError('not all synthetic encodings were translated natively')
    run([wrapper, '-O1', '-std=gnu11', '-ffp-contract=off', '-shared', '-fPIC',
         '-I' + str(deps / 'include'), '-I' + str(cpu / 'src'), generated,
         '-o', out / 'libsnippets.so'], 'compile_generated')
    run([wrapper, '-O2', '-std=gnu11', '-I' + str(deps / 'include'), '-I' + str(cpu / 'src'),
         recomp / 'tests/fuzz_recomp.c', cpu / 'out/libbbcpu.a',
         deps / 'lib/libZydis.a', deps / 'lib/libZycore.a', '-o', out / 'fuzz_recomp'],
        'compile_fuzzer')
    result = run([out / 'fuzz_recomp', encodings, out / 'libsnippets.so', args.trials, '10'],
                 'differential')
    if f'{expected} instructions tested, 0 failed, 0 crashed, 0 skipped' not in result:
        raise RuntimeError('incomplete differential coverage')
    evidence = {'scope': 'external tools and synthetic integer/memory instructions only',
                'recompiler_commit': RECOMP, 'bbcpu_commit': BBCPU, 'api': int(api),
                'host': 'linux-x86_64', 'hello_output': hello.strip(),
                'encodings': expected, 'trials_per_encoding': args.trials,
                'encodings_sha256': hashlib.sha256(encodings.read_bytes()).hexdigest(),
                'generated_and_interpreter_agree': True, 'game_image_used': False,
                'production_runtime_integrated': False, 'arm64_tested': False,
                'windows_macos_tested': False, 'floating_point_tested': False}
    (out / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
