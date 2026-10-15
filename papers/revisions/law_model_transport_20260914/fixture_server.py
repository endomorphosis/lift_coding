#!/usr/bin/env python3
"""Tiny loopback test endpoint. It contains and loads no model."""
import argparse
import json
import os
from pathlib import Path
import select
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    args.directory.mkdir(mode=0o700)
    def record(value):
        with LOCK, (args.directory / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps({'at': time.monotonic(), **value}) + '\n')
            stream.flush()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def do_POST(self):
            length = int(self.headers.get('Content-Length', '0'))
            if not 1 <= length <= 256 * 1024:
                self.send_error(413)
                return
            raw = self.rfile.read(length)
            body = json.loads(raw)
            mode = body['content'].removeprefix('FIXTURE_PROMPT::') if self.path == '/tokenize' else body['messages'][0]['content']
            record({'event': 'request', 'path': self.path, 'mode': mode, 'body_bytes': len(raw)})
            def wait_disconnect():
                end = time.monotonic() + 3
                while time.monotonic() < end:
                    readable, _, _ = select.select([self.connection], [], [], 0.025)
                    if readable and self.connection.recv(1, socket.MSG_PEEK) == b'':
                        record({'event': 'upstream_disconnect_observed', 'mode': mode})
                        return True
                return False
            try:
                if self.path in ('/apply-template', '/tokenize'):
                    if self.path == '/apply-template':
                        assert body['add_generation_prompt'] is True
                        value = {'prompt': 'x' * (256 * 1024 + 1) if mode == 'template_oversize' else 'FIXTURE_PROMPT::' + mode}
                    else:
                        assert body['add_special'] is True and body['parse_special'] is True
                        value = {'tokens': list(range(2049)) if mode == 'input_overflow' else [1, 2, 3]}
                        if mode == 'tokenize_oversize':
                            value['unexpected_padding'] = 'x' * (256 * 1024 + 1)
                    data = json.dumps(value).encode()
                    self.send_response(200)
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if mode in ('slow_headers', 'cancel') and wait_disconnect():
                    return
                if mode == 'redirect':
                    data = b'fixture redirect body'
                    self.send_response(307)
                    self.send_header('Location', f'http://127.0.0.1:{self.server.server_port}/forbidden')
                elif mode == 'failed_http':
                    data = b'fixture failed HTTP body'
                    self.send_response(503)
                elif mode == 'oversize':
                    data = b'x' * (4 * 1024 * 1024 + 4096)
                    self.send_response(200)
                elif mode == 'drip':
                    self.send_response(200)
                    self.send_header('Content-Length', '100000')
                    self.end_headers()
                    for _ in range(80):
                        self.wfile.write(b'x')
                        self.wfile.flush()
                        time.sleep(0.05)
                    return
                else:
                    data = json.dumps({'choices': [{'message': {'role': 'assistant', 'content': 'fixture Ω'}}],
                                       'usage': {'prompt_tokens': 4 if mode == 'token_mismatch' else 3, 'completion_tokens': 2},
                                       'fixture_no_model': True}, ensure_ascii=False).encode()
                    self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                record({'event': 'upstream_disconnect_observed', 'mode': mode})
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    (args.directory / 'ready.json').write_text(json.dumps({'pid': os.getpid(), 'port': server.server_port,
                                                         'host': '127.0.0.1', 'model_loaded': False}))
    server.serve_forever(poll_interval=0.05)


if __name__ == '__main__':
    main()
