# SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""A ping on the rig, as players over the internet have: every game's traffic to the other games
and to the rig's servers arrives a random 50-100 ms (the default) round trip later.

The games delay what they send each other themselves (SHADPS4_P2P_DELAY_MS, one way: half the
ping); the servers sit behind DelayProxy, a TCP proxy that holds every chunk half the ping each
way. Each way keeps its order, as a real connection would.
"""
from collections import deque
import random
import socket
import threading
import time

DEFAULT_PING = "50-100"


def parse_ping(text: str) -> tuple[int, int] | None:
    """A round trip in milliseconds, "80" or "50-100"; None for "0" or "off" (no delay)."""
    text = text.strip().lower()
    if text in ("0", "off", "none", ""):
        return None
    parts = text.split("-")
    if len(parts) > 2 or not all(part.isdigit() for part in parts):
        raise ValueError(f"a ping is milliseconds, \"80\" or \"50-100\": {text!r}")
    low, high = int(parts[0]), int(parts[-1])
    if low > high:
        raise ValueError(f"the ping's range runs low to high: {text!r}")
    return low, high


def one_way(ping: tuple[int, int]) -> tuple[int, int]:
    """Half a round trip, rounded so both ways still add up to it."""
    return ping[0] // 2, (ping[1] + 1) // 2


def game_setting(ping: tuple[int, int]) -> str:
    """SHADPS4_P2P_DELAY_MS for a ping: what each game holds back the packets it sends."""
    low, high = one_way(ping)
    return f"{low}-{high}"


class DelayLine:
    """When each packet of one way is due: a random point in the range after it was sent, but
    never before the one sent ahead of it (no reordering)."""

    def __init__(self, delay_ms: tuple[int, int], seed: int | None = None):
        self.low, self.high = delay_ms[0] / 1000, delay_ms[1] / 1000
        self.random = random.Random(seed)
        self.last_due = 0.0

    def due_at(self, sent: float) -> float:
        due = sent + self.random.uniform(self.low, self.high)
        due = max(due, self.last_due)
        self.last_due = due
        return due


class DelayProxy:
    """Listens on 127.0.0.1:`port` (0 for any) and passes each connection on to `target`, every
    chunk held one way's delay (`delay_ms`, the range of one way) in each direction."""

    def __init__(self, port: int, target: int, delay_ms: tuple[int, int]):
        self.target = target
        self.delay_ms = delay_ms
        self.listener = socket.create_server(("127.0.0.1", port))
        self.port = self.listener.getsockname()[1]
        self.stopping = threading.Event()
        self.sockets: list[socket.socket] = []
        self.lock = threading.Condition()
        self.held_until = 0.0  # an outage (outage()): nothing passes before this (monotonic)
        self.accept_thread: threading.Thread | None = None

    def outage(self, seconds: float):
        """Nothing gets through for `seconds` (players' links dropped for 15-31 s): what is sent
        meanwhile arrives after it, in order, as TCP sends it again."""
        with self.lock:
            self.held_until = max(self.held_until, time.monotonic() + seconds)
            self.lock.notify_all()

    def start(self):
        self.accept_thread = threading.Thread(target=self.accept_all, daemon=True)
        self.accept_thread.start()

    def stop(self):
        self.stopping.set()
        # close() alone need not wake a different thread blocked in accept()/recv().
        close(self.listener)
        with self.lock:
            for sock in self.sockets:
                close(sock)
            self.sockets.clear()
            self.lock.notify_all()
        if self.accept_thread is not None and self.accept_thread is not threading.current_thread():
            self.accept_thread.join(timeout=1)

    def accept_all(self):
        while not self.stopping.is_set():
            try:
                client, _ = self.listener.accept()
            except OSError:
                return
            try:
                server = socket.create_connection(("127.0.0.1", self.target), timeout=10)
                server.settimeout(None)
            except OSError:
                close(client)
                continue
            for sock in (client, server):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with self.lock:
                if self.stopping.is_set():
                    close(client)
                    close(server)
                    return
                self.sockets += [client, server]
            remaining = [2]
            failed = threading.Event()

            def finish(client=client, server=server, remaining=remaining):
                with self.lock:
                    remaining[0] -= 1
                    if remaining[0] == 0:
                        for sock in (client, server):
                            if sock in self.sockets:
                                self.sockets.remove(sock)
                            close(sock)

            self.pass_on(client, server, failed, finish)
            self.pass_on(server, client, failed, finish)

    # A slow or suspended receiver pushes back to TCP rather than consuming unlimited RAM.
    CHUNK_BYTES = 64 * 1024
    QUEUE_CHUNKS = 32

    def pass_on(self, source, sink, failed, finish):
        """Delay a direction, preserving TCP order and half-close semantics."""
        line = DelayLine(self.delay_ms)
        queue: deque[tuple[float, bytes]] = deque()

        def cancelled():
            return self.stopping.is_set() or failed.is_set()

        def abort():
            with self.lock:
                failed.set()
                self.lock.notify_all()
            close(source)
            close(sink)

        def read():
            while True:
                with self.lock:
                    self.lock.wait_for(lambda: cancelled() or len(queue) < self.QUEUE_CHUNKS)
                    if cancelled():
                        return
                try:
                    data = source.recv(self.CHUNK_BYTES)
                except OSError:
                    abort()
                    return
                with self.lock:
                    if cancelled():
                        return
                    queue.append((line.due_at(time.monotonic()), data))
                    self.lock.notify_all()
                if not data:
                    return

        def write():
            try:
                while True:
                    with self.lock:
                        while not cancelled():
                            if not queue:
                                self.lock.wait()
                                continue
                            due, data = queue[0]
                            wait = max(due, self.held_until) - time.monotonic()
                            if wait <= 0:
                                break
                            self.lock.wait(wait)  # recheck if a new outage extends the deadline
                        else:
                            return
                        queue.popleft()
                        self.lock.notify_all()
                    if not data:
                        sink.shutdown(socket.SHUT_WR)
                        return
                    sink.sendall(data)
            except OSError:
                abort()
            finally:
                finish()

        threading.Thread(target=read, daemon=True).start()
        threading.Thread(target=write, daemon=True).start()


def close(sock: socket.socket):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass
