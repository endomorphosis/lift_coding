#!/usr/bin/env python3
"""Worker client for one mounted model job capability; no TCP or provider API."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import secrets
import socket
import struct
import time

FRAME_MAX = 256 * 1024
RESPONSE_MAX = 6 * 1024 * 1024


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def receive(sock, size, deadline):
    out = bytearray()
    while len(out) < size:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError('Complete worker request deadline expired')
        sock.settimeout(left)
        part = sock.recv(size - len(out))
        if not part:
            raise EOFError('Gateway disconnected')
        out.extend(part)
    return bytes(out)


def exchange(job, body, output, *, budget_seconds=60, request_id=None):
    """One recorded attempt; no automatic retry, including uncertain timeouts."""
    if type(budget_seconds) not in (int, float) or not math.isfinite(budget_seconds) or not 0 < budget_seconds <= 60:
        raise ValueError('Positive finite <=60-second budget required')
    job, output = Path(job), Path(output)
    config = json.loads((job / 'client.json').read_bytes())
    rid = request_id or secrets.token_hex(16)
    packet = {'job_id': config['job_id'], 'token': config['token'], 'request_id': rid,
              'budget_seconds': budget_seconds, 'body': body}
    raw = encoded(packet)
    if len(raw) > FRAME_MAX:
        raise ValueError('Request frame exceeds byte limit')
    output.mkdir(mode=0o700)
    (output / 'request.bin').write_bytes(encoded(body))
    started = time.monotonic()
    deadline = started + budget_seconds
    report = {'request_id': rid, 'attempt_reserved': True, 'automatic_retry': False,
              'started_monotonic': started, 'deadline_monotonic': deadline,
              'request_sha256': hashlib.sha256(encoded(body)).hexdigest(), 'response_received': False,
              'connection_started': False, 'error': None}
    response = None
    try:
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(max(0.001, deadline - time.monotonic()))
            sock.connect(str(job / config['socket_name']))
            report['connection_started'] = True
            sock.sendall(struct.pack('!I', len(raw)) + raw)
            size = struct.unpack('!I', receive(sock, 4, deadline))[0]
            if not 1 <= size <= RESPONSE_MAX:
                raise ValueError('Gateway response frame exceeds bound')
            wire = receive(sock, size, deadline)
            response = json.loads(wire)
            (output / 'gateway_response.json').write_bytes(wire + b'\n')
            if 'response_base64' in response:
                raw_response = base64.b64decode(response['response_base64'], validate=True)
                (output / 'response.bin').write_bytes(raw_response)
            report['response_received'] = True
    except Exception as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        report.update(completed_monotonic=time.monotonic(), elapsed_seconds=time.monotonic() - started,
                      local_socket_closed=True,
                      host_cancellation_requires_receipt=not report['response_received'])
        with (output / 'client_receipt.json').open('x') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
    return response, report


def close_job(job):
    job = Path(job)
    config = json.loads((job / 'client.json').read_bytes())
    raw = encoded({'job_id': config['job_id'], 'token': config['token'], 'operation': 'close'})
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(2)
        sock.connect(str(job / config['socket_name']))
        sock.sendall(struct.pack('!I', len(raw)) + raw)
        deadline = time.monotonic() + 2
        size = struct.unpack('!I', receive(sock, 4, deadline))[0]
        if size > 1024:
            raise ValueError('Oversized close receipt')
        return json.loads(receive(sock, size, deadline))


def post_json(job, body, directory, label, remaining_seconds):
    """Explicit socket-capability equivalent of the bounded HTTP helper API."""
    import re
    if not re.fullmatch(r'[a-z][a-z0-9_-]*', label):
        raise ValueError('Invalid retained request label')
    response, receipt = exchange(job, body, Path(directory) / label,
                                  budget_seconds=min(60, remaining_seconds))
    if not response or not response.get('ok'):
        raise RuntimeError('Owned model transport failed; inspect retained receipts, do not retry automatically')
    return json.loads(base64.b64decode(response['response_base64'], validate=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--body', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=60)
    args = parser.parse_args()
    response, receipt = exchange(args.job, json.loads(args.body.read_bytes()), args.output, budget_seconds=args.seconds)
    print(json.dumps({'response_ok': bool(response and response.get('ok')), 'request_id': receipt['request_id'],
                      'receipt': str(args.output / 'client_receipt.json')}))
    raise SystemExit(0 if response and response.get('ok') else 1)
