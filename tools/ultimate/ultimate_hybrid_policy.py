"""Executable acceptance model, not production networking or a Discord SDK binding."""
from dataclasses import dataclass
from enum import Enum
import unittest


class Route(Enum):
    AUTHORITY = 'authority'
    DIRECT = 'direct'
    RELAY = 'relay'
    UNAVAILABLE = 'unavailable'


@dataclass(frozen=True)
class PeerPath:
    # True only after two-way probes with the current authenticated peer/session.
    direct_verified: bool = False
    direct_allowed: bool = False
    relay_ready: bool = False
    authority_ready: bool = False


def route(event: str, path: PeerPath) -> Route:
    if event in {'membership', 'world_commit', 'boss_result', 'reward', 'travel_commit', 'invasion_admission'}:
        return Route.AUTHORITY if path.authority_ready else Route.UNAVAILABLE
    if event not in {'pose_snapshot', 'visual_emote'}:
        return Route.UNAVAILABLE
    if path.direct_allowed and path.direct_verified:
        return Route.DIRECT
    return Route.RELAY if path.relay_ready else Route.UNAVAILABLE


def accept_snapshot(current_epoch: int, packet_epoch: int, last_seq: int, seq: int) -> bool:
    # Called after identity, stream, room and replay-window authentication.
    # A transport switch alone does not reset last_seq. Renegotiate epoch before wrap.
    return packet_epoch == current_epoch and 0 <= seq < 2**32 and seq > last_seq


def build_name(strength: int, skill: int, bloodtinge: int, arcane: int) -> str | None:
    stats = (strength, skill, bloodtinge, arcane)
    if any(type(s) is not int or not 0 <= s <= 99 for s in stats):
        return None
    picked = tuple(i for i, value in enumerate(stats) if value >= 18)
    if not picked:
        return None
    if len(picked) == 1:
        return ('Strength Build', 'Skill Build', 'Bloodtinge Build', 'Arcane Build')[picked[0]]
    if picked == (0, 1):
        return 'Quality Build'
    return '/'.join(('STR', 'SKL', 'BLT', 'ARC')[i] for i in picked)


class Acceptance(unittest.TestCase):
    def test_authority_never_falls_back_to_peer(self):
        for e in ('membership', 'world_commit', 'boss_result', 'reward', 'travel_commit', 'invasion_admission'):
            with self.subTest(event=e):
                self.assertIs(route(e, PeerPath(True, True, True, True)), Route.AUTHORITY)
                self.assertIs(route(e, PeerPath(True, True, True, False)), Route.UNAVAILABLE)

    def test_direct_loss_uses_relay(self):
        self.assertIs(route('pose_snapshot', PeerPath(True, True, True, True)), Route.DIRECT)
        self.assertIs(route('pose_snapshot', PeerPath(False, True, True, True)), Route.RELAY)

    def test_relay_only_privacy(self):
        self.assertIs(route('visual_emote', PeerPath(True, False, True, True)), Route.RELAY)

    def test_no_path_and_unknown_packet(self):
        self.assertIs(route('pose_snapshot', PeerPath()), Route.UNAVAILABLE)
        self.assertIs(route('new_unclassified_packet', PeerPath(True, True, True, True)), Route.UNAVAILABLE)

    def test_epoch_and_sequence_do_not_reset_on_failover(self):
        self.assertTrue(accept_snapshot(8, 8, 40, 41))
        self.assertFalse(accept_snapshot(8, 7, 40, 100))
        self.assertFalse(accept_snapshot(8, 8, 40, 40))
        self.assertFalse(accept_snapshot(8, 8, 40, 39))
        self.assertFalse(accept_snapshot(8, 8, 40, 2**32))

    def test_build_threshold_and_names(self):
        self.assertIsNone(build_name(17, 17, 17, 17))
        for i, name in enumerate(('Strength Build', 'Skill Build', 'Bloodtinge Build', 'Arcane Build')):
            a = [17] * 4
            a[i] = 18
            self.assertEqual(build_name(*a), name)
        self.assertEqual(build_name(18, 18, 17, 17), 'Quality Build')
        self.assertEqual(build_name(18, 17, 17, 18), 'STR/ARC')
        self.assertEqual(build_name(17, 18, 18, 18), 'SKL/BLT/ARC')
        self.assertEqual(build_name(18, 18, 18, 18), 'STR/SKL/BLT/ARC')
        self.assertIsNone(build_name(255, 18, 17, 17))


if __name__ == '__main__':
    unittest.main(verbosity=2)
