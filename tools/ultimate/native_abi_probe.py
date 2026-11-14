# SPDX-License-Identifier: GPL-2.0-or-later
"""Developer smoke test: host libraries only. No retail input, code generation or game launch."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

# A deliberately tiny test ABI. This is not the existing bbcoop ABI.
MODULE = r'''
#if defined(_WIN32)
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif
EXPORT unsigned ultimate_probe_abi(void) { return ABI; }
#ifndef NO_START
EXPORT int ultimate_probe_start(void) { return 42; }
#endif
'''

LINUX_HOST = r'''
#include <dlfcn.h>
int main(int argc, char **argv) {
    if (argc != 2 || argv[1][0] != '/') return 10;
    void *lib = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!lib) return 11;
    unsigned (*abi)(void) = (unsigned (*)(void))dlsym(lib, "ultimate_probe_abi");
    int result = 12;
    if (abi && abi() == 1) {
        int (*start)(void) = (int (*)(void))dlsym(lib, "ultimate_probe_start");
        result = !start ? 13 : start() != 42 ? 14 : 0;
    }
    dlclose(lib);
    return result;
}
'''


def run(args, cwd, expected=0, env=None):
    p = subprocess.run(args, cwd=cwd, env=env, check=False, timeout=30,
                       capture_output=True, text=True)
    if p.returncode != expected:
        raise RuntimeError(f'{Path(args[0]).name}: expected {expected}, got {p.returncode}\n{p.stderr}')
    return p.stdout


def main():
    if sys.platform != 'linux':
        raise SystemExit('The smoke harness currently runs on Linux.')
    with tempfile.TemporaryDirectory(prefix='ultimate-native-probe-') as tmp:
        work = Path(tmp).resolve()
        (work / 'module.c').write_text(MODULE, encoding='ascii')
        (work / 'host.c').write_text(LINUX_HOST, encoding='ascii')
        cc = shutil.which('cc')
        if not cc:
            raise SystemExit('cc is required to run this developer fixture.')
        run([cc, '-Wall', '-Wextra', '-Werror', 'host.c', '-ldl', '-o', 'host'], work)
        for name, flags in [('good', ['-DABI=1']), ('badabi', ['-DABI=2']),
                            ('nostart', ['-DABI=1', '-DNO_START'])]:
            run([cc, '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC', '-fvisibility=hidden',
                 *flags, 'module.c', '-o', name + '.so'], work)
        (work / 'invalid.so').write_bytes(b'not a native library')
        env = {k: v for k, v in os.environ.items() if not k.startswith('LD_')}
        for file, code in [('good.so', 0), ('badabi.so', 12), ('nostart.so', 13),
                           ('missing.so', 11), ('invalid.so', 11)]:
            run([str(work / 'host'), str(work / file)], work, code, env)
        run([str(work / 'host'), 'good.so'], work, 10, env)
        print('PASS Linux: six host-library smoke cases, no PS4 files in fixture')
        clang, link, objdump = map(shutil.which, ('clang', 'lld-link', 'objdump'))
        if not all((clang, link, objdump)):
            print('SKIP Windows cross-build: clang, lld-link and objdump required')
            return
        run([clang, '--target=x86_64-pc-windows-msvc', '-DABI=1', '-c', 'module.c', '-o', 'module.obj'], work)
        run([link, '/dll', '/noentry', '/nodefaultlib', '/machine:x64', '/out:probe.dll', 'module.obj'], work)
        dump = run([objdump, '-p', 'probe.dll'], work)
        if not all(s in dump for s in ('pei-x86-64', 'ultimate_probe_abi', 'ultimate_probe_start')):
            raise RuntimeError('Missing Windows x64 format or expected probe exports')
        print('PASS Windows: cross-built PE x64 DLL and inspected exports; not executed')


if __name__ == '__main__':
    main()
