#!/usr/bin/env python3
"""A per-job Unix socket capability for one owned loopback chat endpoint.

No model/service launch, arbitrary URL, HTTP proxy, or provider invocation.
The host gateway is finite, serial, authenticated and preserves every dispatch.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import secrets
import select
import signal
import socket
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request

FRAME_MAX = 256 * 1024
RESPONSE_MAX = 4 * 1024 * 1024
WIRE_MAX = 7 * 1024 * 1024
STOP = False


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path = Path(path)
    with path.open('xb') as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(encode(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())


def identity(pid):
    stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    if stat[0] == 'Z':
        raise ValueError('Owner is a zombie')
    return {'pid': pid, 'start_ticks': stat[19], 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'command_sha256': sha(Path(f'/proc/{pid}/cmdline').read_bytes())}


def owner_check(owner):
    if owner['host'] != '127.0.0.1' or type(owner['port']) is not int or not 1024 <= owner['port'] <= 65535:
        raise ValueError('Only one explicit high loopback port is admitted')
    if identity(owner['process']['pid']) != owner['process']:
        raise ValueError('Model owner identity changed')
    if not math.isfinite(owner['deadline_monotonic']) or time.monotonic() >= owner['deadline_monotonic']:
        raise ValueError('Owner deadline exhausted')
    if owner['scope'] == 'real_model':
        if type(owner['wall_seconds']) not in (int, float) or not 10000 <= owner['wall_seconds'] <= 43200 or owner['startup_seconds'] != 360:
            raise ValueError('Real owner requires 10000-43200 wall seconds and 360 startup seconds')
        # A transport must not turn an unqualified loopback service into a model.
        q = owner['qualification']
        raw = Path(q['path']).read_bytes()
        if sha(raw) != q['sha256']:
            raise ValueError('Real owner qualification hash differs')
        report = strict_json(raw)
        if (report.get('schema') != 'law-warm-model-owner-qualification/v1' or report.get('status') != 'PASS'
                or report.get('model_identity') != owner['model_identity'] or report.get('wall_seconds') != owner['wall_seconds']
                or report.get('startup_seconds') != 360 or report.get('cleanup_qualified') is not True):
            raise ValueError('Real model owner is not qualified')
    elif owner['scope'] != 'tiny_non_model_fixture':
        raise ValueError('Unknown owner scope')
    if owner['deadline_monotonic'] > owner['started_monotonic'] + owner['wall_seconds'] + 0.001:
        raise ValueError('Owner deadline exceeds its declared whole-job bound')
    # Pin actual listening inode to the exact declared process, not merely /health.
    address = '0100007F:' + format(owner['port'], '04X')
    inodes = {row.split()[9] for row in Path('/proc/net/tcp').read_text().splitlines()[1:]
              if row.split()[1] == address and row.split()[3] == '0A'}
    descriptors = set()
    for fd in Path(f"/proc/{owner['process']['pid']}/fd").iterdir():
        try:
            descriptors.add(os.readlink(fd))
        except FileNotFoundError:
            pass
    if not inodes or not any('socket:[' + inode + ']' in descriptors for inode in inodes):
        raise ValueError('Loopback listener is not owned by the pinned process')


def prepare(directory, owner, *, max_requests=100, max_tokens=1024):
    """Trusted host preparation; worker sees only client/ (one socket + token)."""
    owner_check(owner)
    if type(max_requests) is not int or not 1 <= max_requests <= 8192:
        raise ValueError('Invalid finite request allowance')
    if type(max_tokens) is not int or not 1 <= max_tokens <= 8192:
        raise ValueError('Invalid token bound')
    if owner['scope'] == 'real_model' and max_tokens != 1024:
        raise ValueError('Original Law study requires a 1024-token output limit')
    directory = Path(directory).resolve()
    directory.mkdir(mode=0o700)
    client = directory / 'client'
    client.mkdir(mode=0o700)
    if len(os.fsencode(client / 'socket')) >= 108:
        raise ValueError('Unix socket path is too long; use a fresh short owned job path')
    job = secrets.token_hex(16)
    token = secrets.token_hex(32)
    config = {'schema': 'law-model-transport-job/v1', 'job_id': job, 'token': token, 'owner': owner,
              'uid': os.getuid(), 'max_requests': max_requests, 'max_tokens': max_tokens,
              'max_input_tokens': 2048, 'seeds': [104729, 104759, 104761],
              'max_request_bytes': FRAME_MAX, 'max_response_bytes': RESPONSE_MAX,
              'transport_sha256': sha(Path(__file__).read_bytes())}
    save(directory / 'host.json', config)
    save(client / 'client.json', {'schema': 'law-model-transport-client/v1', 'job_id': job, 'token': token,
                                 'model': owner['model'], 'socket_name': 'socket'})
    (directory / 'attempts').mkdir(mode=0o700)
    return directory


def receive(sock, size, deadline):
    output = bytearray()
    while len(output) < size:
        if STOP or time.monotonic() >= deadline:
            raise TimeoutError('Frame deadline exhausted')
        sock.settimeout(max(0.001, deadline - time.monotonic()))
        block = sock.recv(size - len(output))
        if not block:
            raise EOFError('Peer disconnected')
        output.extend(block)
    return bytes(output)


def packet(sock, value):
    raw = encode(value)
    if len(raw) > WIRE_MAX:
        raise ValueError('Response wire byte bound exceeded')
    sock.sendall(struct.pack('!I', len(raw)) + raw)


def disconnected(sock):
    readable, _, _ = select.select([sock], [], [], 0)
    return bool(readable) and sock.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT) == b''


def validate_body(body, config):
    if not isinstance(body, dict) or set(body) != {'model', 'messages', 'temperature', 'seed', 'max_tokens', 'stream'}:
        raise ValueError('Only the fixed chat-completions body contract is accepted')
    if (body['model'] != config['owner']['model'] or body['stream'] is not False
            or type(body['temperature']) not in (int, float) or body['temperature'] != 0):
        raise ValueError('Model/stream/decoding contract differs')
    if type(body['max_tokens']) is not int or not 1 <= body['max_tokens'] <= config['max_tokens']:
        raise ValueError('Token bound exceeded')
    if type(body['seed']) is not int or body['seed'] not in config['seeds']:
        raise ValueError('Seed is not in the original three-seed contract')
    messages = body['messages']
    if not isinstance(messages, list) or not 1 <= len(messages) <= 32:
        raise ValueError('Invalid message count')
    for message in messages:
        if (not isinstance(message, dict) or set(message) != {'role', 'content'}
                or message['role'] not in ('system', 'user', 'assistant') or not isinstance(message['content'], str)):
            raise ValueError('Only bounded plain-text chat messages are accepted')
    if len(encode(body)) > FRAME_MAX - 2048:
        raise ValueError('Request body byte bound exceeded')


def forward(config, body, conn, attempt, deadline, route):
    global STOP
    raw = encode(body)
    request_path = attempt / 'request.bin'
    with request_path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    save(attempt / 'dispatch.json', {'request_sha256': sha(raw), 'reserved_monotonic': time.monotonic(),
                                   'deadline_monotonic': deadline, 'upstream_path': route,
                                   'owner_process': config['owner']['process'], 'model': config['owner']['model'],
                                   'attempt_reserved': True, 'automatic_retry': False})
    child = None
    reason = None
    started = time.monotonic()
    try:
        owner_check(config['owner'])
        if time.monotonic() >= deadline:
            raise TimeoutError('Whole request deadline expired before this phase')
        with (attempt / 'stderr.txt').open('xb') as stderr:
            child = subprocess.Popen([sys.executable, '-I', str(Path(__file__).resolve()), 'http-child',
                                      '--attempt', str(attempt), '--port', str(config['owner']['port']),
                                      '--deadline', str(deadline), '--parent-pid', str(os.getpid()), '--route', route], stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=stderr)
            save(attempt / 'child.json', {'pid': child.pid, 'started_monotonic': time.monotonic()})
            while child.poll() is None:
                if STOP:
                    reason = 'gateway_cancelled'
                    break
                if time.monotonic() >= deadline:
                    reason = 'hard_request_deadline'
                    break
                if disconnected(conn):
                    reason = 'client_disconnected'
                    break
                try:
                    owner_check(config['owner'])
                except Exception:
                    reason = 'owner_identity_or_deadline_changed'
                    break
                time.sleep(0.02)
    except Exception as exc:
        reason = type(exc).__name__ + ': ' + str(exc)
    finally:
        cleanup_start = time.monotonic()
        cleanup_errors = []
        if child is not None and child.poll() is None:
            try:
                child.kill()
                child.wait(timeout=2)
            except Exception as exc:
                cleanup_errors.append(type(exc).__name__ + ': ' + str(exc))
                STOP = True  # Never accept another request with unproven cleanup.
        worker = None
        try:
            worker = strict_json((attempt / 'worker.json').read_bytes())
            if not isinstance(worker, dict) or type(worker.get('complete')) is not bool:
                raise ValueError('Malformed child metadata')
        except Exception as exc:
            metadata_error = type(exc).__name__
        else:
            metadata_error = None
        response = (attempt / 'response.bin').read_bytes() if (attempt / 'response.bin').exists() else b''
        if len(response) > RESPONSE_MAX + 1:
            raise RuntimeError('Worker violated retained response bound')
        receipt = {'schema': 'law-model-transport-attempt/v1', 'request_sha256': sha(raw),
                   'response_sha256': sha(response), 'response_bytes': len(response), 'worker': worker,
                   'metadata_error': metadata_error, 'termination_reason': reason, 'cleanup_errors': cleanup_errors,
                   'child_pid': None if child is None else child.pid, 'child_returncode': None if child is None else child.poll(),
                   'child_termination_proven': child is None or child.poll() is not None,
                   'elapsed_seconds': time.monotonic() - started, 'cleanup_seconds': time.monotonic() - cleanup_start,
                   'deadline_monotonic': deadline, 'completed_monotonic': time.monotonic(),
                   'attempt_reserved': True, 'automatic_retry': False}
        save(attempt / 'receipt.json', receipt)
    ok = bool(reason is None and not cleanup_errors and child is not None and child.returncode == 0
              and worker and worker.get('complete') and 200 <= worker.get('status', 0) < 300)
    return {'ok': ok, 'request_id': attempt.name, 'receipt': receipt,
            'response_base64': base64.b64encode(response).decode()}


def infer(config, body, conn, attempt, deadline):
    """Atomic template/tokenize/generation; the worker cannot bypass preflight."""
    phases = {}
    started = time.monotonic()
    result = {'input_count': None, 'generation_reserved': False, 'token_usage_known': False,
              'prompt_tokens': None, 'completion_tokens': None, 'error': None,
              'messages_sha256': sha(encode(body['messages'])), 'seed': body['seed'],
              'max_input_tokens': config['max_input_tokens'], 'max_output_tokens': body['max_tokens'],
              'deadline_monotonic': deadline, 'automatic_retry': False}
    def phase(name, payload, route):
        destination = attempt / name
        destination.mkdir(mode=0o700)
        response = forward(config, payload, conn, destination, deadline, route)
        phases[name] = response
        if not response['ok']:
            raise RuntimeError(name + '_transport_failed')
        return strict_json(base64.b64decode(response['response_base64'], validate=True))
    ok = False
    try:
        rendered = phase('template', {'messages': body['messages'], 'add_generation_prompt': True}, '/apply-template')
        if not isinstance(rendered, dict) or set(rendered) != {'prompt'} or not isinstance(rendered.get('prompt'), str):
            raise ValueError('Template response is not a prompt string')
        token_body = {'content': rendered['prompt'], 'add_special': True, 'parse_special': True}
        if len(encode(token_body)) > FRAME_MAX:
            raise ValueError('Rendered prompt exceeds bounded tokenization input')
        tokenized = phase('tokenize', token_body, '/tokenize')
        tokens = tokenized.get('tokens') if isinstance(tokenized, dict) and set(tokenized) == {'tokens'} else None
        if not isinstance(tokens, list) or any(type(token) is not int or not 0 <= token < 2**31 for token in tokens):
            raise ValueError('Tokenizer returned malformed token IDs')
        result['input_count'] = len(tokens)
        result['rendered_prompt_sha256'] = sha(rendered['prompt'].encode())
        result['token_ids_sha256'] = sha(encode(tokens))
        if not 1 <= len(tokens) <= config['max_input_tokens']:
            raise ValueError('Original 2048-token input ceiling exceeded')
        if time.monotonic() >= deadline or disconnected(conn) or STOP:
            raise TimeoutError('No active budget remains before generation reservation')
        save(attempt / 'inference_reserved.json', {'input_count': len(tokens), 'seed': body['seed'],
                                                 'messages_sha256': result['messages_sha256'],
                                                 'request_sha256': sha(encode(body)),
                                                 'max_output_tokens': body['max_tokens'],
                                                 'consumed_before_generation': True})
        result['generation_reserved'] = True
        generated = phase('generation', body, '/v1/chat/completions')
        usage = generated.get('usage', {})
        pt, ct = usage.get('prompt_tokens'), usage.get('completion_tokens')
        result.update(prompt_tokens=pt, completion_tokens=ct,
                      token_usage_known=type(pt) is int and type(ct) is int)
        if type(pt) is not int or pt != len(tokens) or type(ct) is not int or not 0 <= ct <= body['max_tokens']:
            raise ValueError('Returned prompt tokens differ from preflight or output usage exceeds its bound')
        if not isinstance(generated['choices'][0]['message']['content'], str):
            raise ValueError('Generated content is not a string')
        ok = True
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        result['phases'] = {name: value['receipt'] for name, value in phases.items()}
        result['child_termination_proven'] = all(value['receipt']['child_termination_proven'] for value in phases.values())
        result['cleanup_errors'] = [error for value in phases.values() for error in value['receipt']['cleanup_errors']]
        result['completed_monotonic'] = time.monotonic()
        result['elapsed_seconds'] = time.monotonic() - started
        result['termination_reason'] = next((value['receipt']['termination_reason'] for value in reversed(list(phases.values()))
                                             if value['receipt']['termination_reason']), None)
        save(attempt / 'receipt.json', result)
    generation = phases.get('generation', {})
    return {'ok': ok, 'request_id': attempt.name, 'receipt': result,
            'response_base64': generation.get('response_base64', ''),
            'preflight': {name: {'response_base64': phases[name]['response_base64'],
                                 'receipt': phases[name]['receipt']} for name in ('template', 'tokenize') if name in phases}}


def serve(directory):
    global STOP
    directory = Path(directory).resolve()
    config = strict_json((directory / 'host.json').read_bytes())
    if sha(Path(__file__).read_bytes()) != config['transport_sha256']:
        raise ValueError('Prepared transport code changed')
    if (directory / 'started.json').exists():
        raise ValueError('One-shot gateway cannot be silently restarted')
    owner_check(config['owner'])
    def stopped(*_):
        global STOP
        STOP = True
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, stopped)
    address = directory / 'client/socket'
    server = socket.socket(socket.AF_UNIX)
    count = 0
    reason = 'owner_deadline'
    try:
        server.bind(str(address))
        os.chmod(address, 0o600)
        server.listen(2)
        server.settimeout(0.1)
        save(directory / 'started.json', {'job_id': config['job_id'], 'process': identity(os.getpid()),
                                          'socket_inode': address.stat().st_ino, 'owner': config['owner']['process'],
                                          'deadline_monotonic': config['owner']['deadline_monotonic'],
                                          'model_loaded_by_gateway': False})
        while not STOP and time.monotonic() < config['owner']['deadline_monotonic']:
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            with conn:
                try:
                    _, uid, _ = struct.unpack('3i', conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                    if uid != config['uid']:
                        raise ValueError('Peer uid differs')
                    frame_deadline = min(time.monotonic() + 1, config['owner']['deadline_monotonic'])
                    size = struct.unpack('!I', receive(conn, 4, frame_deadline))[0]
                    if not 1 <= size <= FRAME_MAX:
                        raise ValueError('Frame byte bound exceeded')
                    request = strict_json(receive(conn, size, frame_deadline))
                    if not isinstance(request, dict) or request.get('job_id') != config['job_id'] or not hmac.compare_digest(str(request.get('token', '')), config['token']):
                        raise ValueError('Job authentication failed')
                    if request.get('operation') == 'close' and set(request) == {'job_id', 'token', 'operation'}:
                        packet(conn, {'ok': True, 'closed': True})
                        reason = 'authenticated_job_finished'
                        break
                    if set(request) != {'job_id', 'token', 'request_id', 'budget_seconds', 'body'}:
                        raise ValueError('Unknown transport capability fields')
                    rid = request['request_id']
                    if not isinstance(rid, str) or not re.fullmatch('[a-f0-9]{32}', rid):
                        raise ValueError('Invalid request identity')
                    budget = request['budget_seconds']
                    if type(budget) not in (int, float) or not math.isfinite(budget) or not 0 < budget <= 60:
                        raise ValueError('Invalid finite request deadline')
                    validate_body(request['body'], config)
                    owner_check(config['owner'])
                    if count >= config['max_requests']:
                        raise ValueError('Job request allowance exhausted')
                    attempt = directory / 'attempts' / rid
                    attempt.mkdir(mode=0o700)  # Durable reservation; duplicate never dispatches.
                    count += 1
                    deadline = min(time.monotonic() + budget, config['owner']['deadline_monotonic'])
                    response = infer(config, request['body'], conn, attempt, deadline)
                    conn.settimeout(1)
                    packet(conn, response)
                except Exception as exc:
                    # Do not record bearer capabilities or supplied message text on rejection.
                    with (directory / 'rejections.jsonl').open('ab') as audit:
                        audit.write(encode({'at_monotonic': time.monotonic(), 'error_type': type(exc).__name__, 'error': str(exc)}) + b'\n')
                    try:
                        conn.settimeout(0.1)
                        packet(conn, {'ok': False, 'rejected': True, 'error_type': type(exc).__name__, 'error': str(exc)})
                    except OSError:
                        pass
    finally:
        server.close()
        if address.exists():
            address.unlink()
        save(directory / 'closed.json', {'job_id': config['job_id'], 'reason': 'signal' if STOP else reason,
                                         'reserved_attempts': count, 'socket_removed': not address.exists(),
                                         'model_owner_stopped_by_gateway': False,
                                         'closed_monotonic': time.monotonic()})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def http_child(attempt, port, deadline, parent_pid, route):
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'Cannot establish parent-death cleanup')
    if os.getppid() != parent_pid:
        raise RuntimeError('Gateway disappeared before child containment')
    attempt = Path(attempt)
    limit = RESPONSE_MAX if route == '/v1/chat/completions' else FRAME_MAX
    report = {'complete': False, 'status': None, 'error': None, 'oversize': False, 'response_limit_bytes': limit}
    try:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError('Deadline expired before upstream request')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        if route not in ('/apply-template', '/tokenize', '/v1/chat/completions'):
            raise ValueError('Unknown fixed endpoint')
        request = urllib.request.Request(f'http://127.0.0.1:{port}' + route,
                                         data=(attempt / 'request.bin').read_bytes(), headers={'Content-Type': 'application/json'})
        try:
            response = opener.open(request, timeout=left)
        except urllib.error.HTTPError as exc:
            response = exc
        with response, (attempt / 'response.bin').open('xb') as out:
            report['status'] = response.status
            retained = 0
            while True:
                block = response.read1(min(65536, limit + 1 - retained))
                if not block:
                    report['complete'] = True
                    break
                out.write(block)
                out.flush()
                retained += len(block)
                if retained > limit:
                    report['oversize'] = True
                    raise ValueError('Response byte bound exceeded')
    except Exception as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        save(attempt / 'worker.json', report)
    return 0 if report['complete'] and 200 <= report['status'] < 300 else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('serve')
    s.add_argument('--job', type=Path, required=True)
    h = sub.add_parser('http-child')
    h.add_argument('--attempt', type=Path, required=True)
    h.add_argument('--port', type=int, required=True)
    h.add_argument('--deadline', type=float, required=True)
    h.add_argument('--parent-pid', type=int, required=True)
    h.add_argument('--route', choices=['/apply-template', '/tokenize', '/v1/chat/completions'], required=True)
    args = parser.parse_args()
    if args.command == 'serve':
        serve(args.job)
    else:
        raise SystemExit(http_child(args.attempt, args.port, args.deadline, args.parent_pid, args.route))
