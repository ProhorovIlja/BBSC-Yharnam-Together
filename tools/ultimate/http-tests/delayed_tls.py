"""Loopback-only real TLS regression. Creates an ephemeral CA certificate; no game/account I/O."""
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory(prefix='bloodborne-tls-') as tmp:
        root = Path(tmp)
        cert, key = root / 'cert.pem', root / 'key.pem'
        subprocess.run([sys.argv[2], 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-keyout', str(key), '-out', str(cert), '-subj', '/CN=localhost',
                        '-addext', 'subjectAltName=DNS:localhost'], check=True, capture_output=True)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(('127.0.0.1', 0))
        listener.listen(8)
        listener.settimeout(20)
        port = listener.getsockname()[1]
        threads, errors = [], []

        def serve(raw, delay):
            try:
                with raw:
                    raw.settimeout(12)
                    time.sleep(delay)
                    with context.wrap_socket(raw, server_side=True) as tls:
                        data = b''
                        while b'\r\n\r\n' not in data:
                            part = tls.recv(4096)
                            if not part:
                                return
                            data += part
                        body = b'verified-local-tls'
                        tls.sendall(b'HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Length: ' +
                                    str(len(body)).encode() + b'\r\n\r\n' + body)
            except (ssl.SSLError, BrokenPipeError, ConnectionResetError):
                pass  # The raw timeout and the two certificate-negative controls close TLS early.
            except Exception as error:
                errors.append(repr(error))

        def accept():
            try:
                for delay in (2, 2, 0, 0, 0):
                    raw, _ = listener.accept()
                    thread = threading.Thread(target=serve, args=(raw, delay), daemon=True)
                    threads.append(thread)
                    thread.start()
            except Exception as error:
                errors.append(repr(error))

        acceptor = threading.Thread(target=accept, daemon=True)
        acceptor.start()
        try:
            for mode in ('raw', 'fixed', 'untrusted', 'hostname', 'fast'):
                host = '127.0.0.1' if mode == 'hostname' else 'localhost'
                result = subprocess.run([sys.argv[1], f'https://{host}:{port}', str(cert), mode],
                                        capture_output=True, text=True, timeout=15)
                print(result.stdout, end='', flush=True)
                if result.returncode:
                    raise RuntimeError(f'{mode}: {result.stderr}; exit {result.returncode}')
        finally:
            listener.close()
            acceptor.join(timeout=2)
            for thread in threads:
                thread.join(timeout=2)
        if acceptor.is_alive() or any(thread.is_alive() for thread in threads) or errors:
            raise RuntimeError(f'local server did not finish cleanly: {errors}')
        print('DELAYED_TLS_AND_CERTIFICATE_CONTROLS_PASS')


if __name__ == '__main__':
    main()
