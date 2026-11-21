# SPDX-License-Identifier: GPL-2.0-or-later
"""Compile complete production load/backup/restore functions with synthetic flag memory.

No game image or save is loaded. Memory access, protobuf values, flag ownership,
lamp classification, logging, invasion and NG+ detection are adapters. The actual
load branches, files, serializers and world flag bit operations are compiled.
"""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def between(source, start, end):
    return source[source.index(start):source.index(end, source.index(start))]


def generate():
    core = ROOT / 'emulator/src/core'
    header = (core / 'bloodborne_team.h').read_text()
    team = (core / 'bloodborne_team.cpp').read_text()
    world = (core / 'bloodborne_server_world.cpp').read_text()
    travel = (core / 'bloodborne_travel.cpp').read_text()
    types = between(header, 'struct WorldFlags {', 'bool IsWorldFlag(')
    types += between(header, 'struct FlagBlockBits {', '// `all`:')
    types += between(header, 'struct HomeWorlds {', '// The file ("worlds",')
    types += 'enum class TeamWorldTake : u8 { Aside, Home, SaveLeads };\n'
    # Keep the complete implementations; no hand-copied load policy.
    helpers = between(team, 'namespace {\n\n// The world flags on in one block.',
                      'bool PlaythroughWatch::NextPlaythrough(')
    homes = between(team, 'namespace {\n\nbool IsWorldIdWord(', 'OldSaveWorld OldSavesWorld(')
    serialization = between(team, 'std::string FormatWorldFlags(', 'std::vector<s32> TimeOfDayToFollow(')
    files = between(world, 'std::filesystem::path PersonalWorldFile(', '} // namespace\n\n// This save\'s clear count')
    load = between(world, 'std::optional<s32> SaveClearCount()', 'std::vector<u32> TeamWorldBlocksForGuest()')
    own_flags = between(world, 'bool SavePlaysInTeam()', 'void TickTeamWorld(')
    lamps = between(travel, 'void KeepGuestLampsLit()', '// See HeadstoneLampsLit:')
    fixture = (HERE / 'fixtures/team_world.cpp.in').read_text()
    for name, implementation in [('TYPES', types), ('HELPERS', helpers + homes + serialization),
                                 ('FILES', files), ('LOAD', load), ('OWN_FLAGS', own_flags),
                                 ('LAMPS', lamps)]:
        fixture = fixture.replace('// PRODUCTION_' + name, implementation)
    return fixture


class TeamWorldPreservationTests(unittest.TestCase):
    def test_production_load_and_restore(self):
        compiler = shlex.split(os.environ.get('CXX', 'c++'))
        if not compiler or not shutil.which(compiler[0]):
            self.skipTest('C++20 compiler unavailable; use the CMake fixture on Windows')
        with tempfile.TemporaryDirectory(prefix='team-world-') as directory:
            cpp = Path(directory) / 'fixture.cpp'
            exe = Path(directory) / 'fixture'
            cpp.write_text(generate())
            build = subprocess.run(compiler + ['-std=c++20', '-pthread', str(cpp), '-o', str(exe)],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('World preservation scenarios: 18/18 passed', result.stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', type=Path)
    args, remaining = parser.parse_known_args()
    if args.emit:
        args.emit.write_text(generate())
    else:
        unittest.main(argv=[__file__] + remaining)
