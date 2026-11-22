# SPDX-FileCopyrightText: Copyright 2026 shadNet Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""The region's directory (directory.py) on fakeredis, and once over HTTP:

    python3 -m unittest -v test_directory     (pip install redis 'fakeredis[lua]')
"""
import json
import socket
import threading
import unittest
import urllib.error
import urllib.request

try:
    import fakeredis
    import directory as d
    MISSING = None
except ImportError as missing:  # ctest runs them where they are installed only
    MISSING = f'{missing.name} is not installed'

KEY = 'ab' * 32


class Clock:
    def __init__(self):
        self.at = 1000.0

    def __call__(self):
        return self.at


def beat(shard, port, players=(), codes=(), worlds=(), started=(), capacity=800, draining=False):
    return {'shard': shard, 'address': f'10.0.0.1:{port}', 'key': KEY, 'capacity': capacity,
            'draining': draining, 'count': len(players),
            'players': [{'id': p, 'member': p.encode().hex(), 'name': p} for p in players],
            'codes': list(codes), 'worlds': list(worlds), 'started': list(started)}


@unittest.skipIf(MISSING, MISSING)
class DirectoryTests(unittest.TestCase):
    def setUp(self):
        self.server = fakeredis.FakeServer()
        self.redis = fakeredis.FakeRedis(server=self.server)
        self.clock = Clock()
        self.directory = d.Directory(self.redis, now=self.clock)

    def replica(self):
        """Another directory process on the same Redis."""
        return d.Directory(fakeredis.FakeRedis(server=self.server), now=self.clock)

    def test_heartbeats_list_the_shards_least_loaded_first(self):
        self.directory.heartbeat(beat('eu-1', 1, players=['a', 'b', 'c']))
        self.directory.heartbeat(beat('eu-2', 2, players=['d']))
        self.directory.heartbeat(beat('eu-3', 3, players=[], draining=True))
        rows = self.replica().shards()
        self.assertEqual([row['name'] for row in rows], ['eu-2', 'eu-1', 'eu-3'])
        self.assertEqual(rows[1]['players'], 3)
        self.assertEqual(rows[0]['address'], '10.0.0.1:2')
        self.assertEqual(rows[0]['key'], KEY)

    def test_a_shard_that_stops_beating_goes(self):
        self.directory.heartbeat(beat('eu-1', 1, players=['a']))
        self.directory.heartbeat(beat('eu-2', 2))
        self.redis.delete('shard:eu-1')  # its TTL ran out
        self.assertEqual([row['name'] for row in self.directory.shards()], ['eu-2'])
        self.assertEqual(self.redis.smembers('shards'), {b'eu-2'})
        self.assertGreater(self.redis.ttl('shard:eu-2'), 0)
        self.assertLessEqual(self.redis.ttl('online:a'), d.PRESENCE_S)

    def test_the_answer_says_the_other_shards_players_and_codes(self):
        self.directory.heartbeat(beat('eu-1', 1, players=['Ada'], codes=['ABCDEF']))
        answer = self.replica().heartbeat(beat('eu-2', 2, players=['Kaniel'], codes=['GHJKLM']))
        self.assertEqual(answer['players'], [{'shard': 'eu-1', 'member': 'Ada'.encode().hex(), 'name': 'Ada'}])
        self.assertEqual(answer['codes'], {'ABCDEF': 'eu-1'})
        self.assertEqual({row['name'] for row in answer['shards']}, {'eu-1', 'eu-2'})

    def test_where_a_player_is_or_last_played(self):
        self.directory.heartbeat(beat('eu-1', 1, players=['Ada'], started=['Ada']))
        self.directory.heartbeat(beat('eu-2', 2, players=['Kaniel']))
        found = self.directory.where('Kaniel')
        self.assertEqual((found['online'], found['shard']['name']), (True, 'eu-2'))
        self.redis.delete('online:Ada')  # Ada signed off
        found = self.directory.where('Ada')
        self.assertEqual((found['online'], found['shard']['name']), (False, 'eu-1'))
        self.assertIsNone(self.directory.where('nobody'))
        # Its home shard down: nowhere (the launcher picks the least loaded).
        self.redis.delete('shard:eu-1')
        self.assertIsNone(self.directory.where('Ada'))

    def test_a_world_has_one_holder(self):
        answer = self.directory.heartbeat(beat('eu-1', 1, worlds=['w1', 'w2']))
        self.assertEqual(answer['held'], {})
        # Another shard listing w1 (a copy) does not get it; its own w3 it does.
        answer = self.replica().heartbeat(beat('eu-2', 2, worlds=['w1', 'w3']))
        self.assertEqual(answer['held'], {'w1': 'eu-1'})
        self.assertEqual(self.directory.world('w1')['shard'], 'eu-1')
        self.assertEqual(self.directory.world('w3')['shard'], 'eu-2')
        self.assertIsNone(self.directory.world('w9'))
        # Renewed by its holder only.
        self.redis.expire('lease:w1', 5)
        self.replica().heartbeat(beat('eu-2', 2, worlds=['w1']))
        self.assertLessEqual(self.redis.ttl('lease:w1'), 5)
        self.directory.heartbeat(beat('eu-1', 1, worlds=['w1']))
        self.assertGreater(self.redis.ttl('lease:w1'), 5)
        # Lapsed (its shard died): the next shard that lists it takes it.
        self.redis.delete('lease:w1')
        answer = self.replica().heartbeat(beat('eu-2', 2, worlds=['w1']))
        self.assertEqual(answer['held'], {})
        self.assertEqual(self.directory.world('w1')['shard'], 'eu-2')

    def test_a_new_id_is_its_first_shards(self):
        self.assertEqual(self.directory.claim_account({'id': 'Ada', 'shard': 'eu-1'})['shard'], 'eu-1')
        self.assertEqual(self.replica().claim_account({'id': 'Ada', 'shard': 'eu-2'})['shard'], 'eu-1')
        self.assertEqual(self.directory.claim_account({'id': 'Ada', 'shard': 'eu-1'})['shard'], 'eu-1')
        with self.assertRaises(d.Refused):
            self.directory.claim_account({'id': 'Ada', 'shard': 'not a name'})

    def test_an_invite_reaches_its_shard_once(self):
        invite = {'shard': 'eu-2', 'member': '4164', 'team': '@eu-1/ABCDEF', 'from': '4b', 'from_name': 'Kaniel'}
        self.directory.invite(invite)
        answer = self.replica().heartbeat(beat('eu-2', 2))
        self.assertEqual(answer['inbox'], [{key: invite[key] for key in ('member', 'team', 'from', 'from_name')}])
        self.assertEqual(self.directory.heartbeat(beat('eu-2', 2))['inbox'], [])
        self.assertEqual(self.directory.heartbeat(beat('eu-1', 1))['inbox'], [])
        with self.assertRaises(d.Refused):
            self.directory.invite(dict(invite, team='t1'))

    def test_a_sign_out_reaches_every_shard(self):
        self.directory.heartbeat(beat('a', 1))
        self.directory.heartbeat(beat('b', 2))
        killed = dict(beat('a', 1), revoked=[{'id': 'u0123456789abcd', 'at': 1001},
                                             {'id': 'p0123456789abcd', 'at': 1001},
                                             {'id': 'not an id', 'at': 1}])
        own = self.directory.heartbeat(killed)['revocations']
        self.assertEqual([r['id'] for r in own], ['u0123456789abcd'])  # only signed ids
        heard = self.directory.heartbeat(dict(beat('b', 2), revoked_after=0))['revocations']
        self.assertEqual(heard, [{'seq': 1, 'id': 'u0123456789abcd', 'at': 1001}])
        # Once: the next beat says where it is.
        self.assertEqual(self.directory.heartbeat(dict(beat('b', 2), revoked_after=1))['revocations'], [])
        self.directory.heartbeat(dict(beat('b', 2), revoked=[{'id': 'd0123456789abcd', 'at': 1002}],
                                      revoked_after=1))
        later = self.directory.heartbeat(dict(beat('a', 1), revoked_after=1))['revocations']
        self.assertEqual(later, [{'seq': 2, 'id': 'd0123456789abcd', 'at': 1002}])
        # A new shard hears all of them still alive.
        self.assertEqual(len(self.directory.heartbeat(beat('c', 3))['revocations']), 2)
        self.clock.at += d.REVOKED_S + 10
        self.assertEqual(self.directory.heartbeat(beat('c', 3))['revocations'], [])

    def test_a_bad_heartbeat_is_refused(self):
        for bad in (dict(beat('eu-1', 1), shard='a b'), dict(beat('eu-1', 1), address='nowhere'),
                    dict(beat('eu-1', 1), key='12'), dict(beat('eu-1', 1), address='10.0.0.1:0')):
            with self.assertRaises(d.Refused):
                self.directory.heartbeat(bad)

    def test_directory_refuses_unroutable_redirect_targets_before_publication(self):
        for host in ('100.64.0.1', '100.127.255.254', '192.0.2.7',
                     '198.18.1.1', '198.19.255.254', '198.51.100.3',
                     '203.0.113.4', '224.0.0.1', '240.1.1.1',
                     '169.254.0.10', '0.0.0.1', '255.255.255.255'):
            with self.subTest(host=host):
                with self.assertRaises(d.Refused):
                    self.directory.heartbeat(dict(beat('bad', 31314),
                                                  address=f'{host}:31314'))
        for invalid_port in ('+31314', ' 31314', '0', '65536', '-1', 'abc'):
            with self.subTest(port=invalid_port):
                with self.assertRaises(d.Refused):
                    d.address_of(f'10.10.0.1:{invalid_port}')
        for host in ('127.0.0.1', '10.0.0.1', '172.20.0.5',
                     '192.168.1.8', '8.8.8.8'):
            with self.subTest(valid=host):
                self.assertEqual(d.address_of(f'{host}:31314'), f'{host}:31314')
        self.assertEqual(self.directory.shards(), [], 'rejected shards never enter Redis')


@unittest.skipIf(MISSING, MISSING)
class HttpTests(unittest.TestCase):
    def setUp(self):
        self.directory = d.Directory(fakeredis.FakeRedis())
        self.server = d.serve(self.directory, 'token', port=0, host='127.0.0.1')
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, path, body=None, token='token'):
        request = urllib.request.Request(self.url + path, data=None if body is None else json.dumps(body).encode())
        if token:
            request.add_header('Authorization', f'Bearer {token}')
        try:
            with urllib.request.urlopen(request, timeout=5) as answer:
                return answer.status, json.loads(answer.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_the_shards_calls_need_the_token(self):
        self.assertEqual(self.call('/v1/heartbeat', beat('eu-1', 1), token='')[0], 401)
        self.assertEqual(self.call('/v1/heartbeat', beat('eu-1', 1), token='wrong')[0], 401)
        self.assertEqual(self.call('/v1/account', {'id': 'a', 'shard': 'eu-1'}, token='')[0], 401)
        status, answer = self.call('/v1/heartbeat', beat('eu-1', 1, players=['Ada']))
        self.assertEqual(status, 200)
        self.assertEqual(answer['shards'][0]['name'], 'eu-1')

    def test_a_refused_call_is_answered_once_its_body_is_read(self):
        # A socket closed with unread data sends a reset, and on Windows the caller's read
        # then aborts (WinError 10053) instead of getting the 401.
        body = json.dumps(beat('eu-1', 1)).encode()
        with socket.create_connection(self.server.server_address, timeout=5) as caller:
            caller.sendall(b'POST /v1/heartbeat HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer wrong\r\n'
                           b'Content-Length: %d\r\n\r\n' % len(body))
            caller.settimeout(0.3)
            with self.assertRaises(socket.timeout, msg='answered before the body was read'):
                caller.recv(1)
            caller.settimeout(5)
            caller.sendall(body)
            answer = b''
            while chunk := caller.recv(65536):
                answer += chunk
        self.assertTrue(answer.startswith(b'HTTP/1.0 401'), answer[:40])

    def test_invalid_post_lengths_do_not_block_an_http_worker(self):
        # The directory reads before bearer authentication to avoid resetting
        # ordinary clients. Invalid size must fail *before* a blocking read.
        for header, expected in (
                (b'Content-Length: -1', b'400'),
                (b'Content-Length: NaN', b'400'),
                (b'Content-Length: 999999999999999999999', b'413'),
                (b'Content-Length: ' + b'9' * 5000, b'413'),
                (b'Content-Length: 8388609', b'413'),
                (b'Transfer-Encoding: chunked', b'400'),
                (b'Transfer-Encoding:', b'400'),
                (b'Content-Length: 2\r\nContent-Length: 2', b'400'),
                (b'Content-Length: 2\r\nContent-Length: 3', b'400')):
            with self.subTest(header=header):
                with socket.create_connection(self.server.server_address, timeout=2) as caller:
                    caller.settimeout(2)
                    caller.sendall(b'POST /v1/heartbeat HTTP/1.1\r\nHost: x\r\n' +
                                   header + b'\r\n\r\n')
                    response = caller.recv(512)
                    self.assertTrue(response.startswith(b'HTTP/1.0 ' + expected),
                                    response[:100])

    def test_truncated_post_body_has_absolute_deadline(self):
        from unittest.mock import patch
        # Two bytes of a four-byte body are supplied and the caller holds the
        # connection open. The handler must answer rather than wait forever.
        with patch.object(d, 'POST_BODY_DEADLINE_S', 0.25):
            with socket.create_connection(self.server.server_address, timeout=2) as caller:
                caller.settimeout(2)
                caller.sendall(b'POST /v1/heartbeat HTTP/1.1\r\nHost: x\r\n'
                               b'Content-Length: 4\r\n\r\n{}')
                response = caller.recv(512)
                self.assertTrue(response.startswith(b'HTTP/1.0 408'), response[:100])

    def test_a_launcher_reads_the_shards_and_where_its_player_is(self):
        self.call('/v1/heartbeat', beat('eu-1', 1, players=['Ada']))
        status, answer = self.call('/v1/shards', token='')
        self.assertEqual((status, answer['shards'][0]['address']), (200, '10.0.0.1:1'))
        status, answer = self.call('/v1/where?player=Ada', token='')
        self.assertEqual((status, answer['shard']['name']), (200, 'eu-1'))
        self.assertEqual(self.call('/v1/where?player=Bob', token='')[0], 404)
        self.assertEqual(self.call('/v1/nothing', token='')[0], 404)
        self.assertEqual(self.call('/v1/heartbeat', {'shard': 'x'})[0], 400)


if __name__ == '__main__':
    unittest.main()
