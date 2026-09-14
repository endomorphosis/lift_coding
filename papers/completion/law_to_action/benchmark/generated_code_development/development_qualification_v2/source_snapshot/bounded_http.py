"""One loopback HTTP request in a child with a parent-enforced wall deadline.

Retains raw bytes, dispatch identity, failures and termination evidence. This
helper loads no models and performs no request without an explicit caller.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class HTTPTransportError(RuntimeError):
    pass


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def checked_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', '::1')
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.port is None):
        raise ValueError('An explicit loopback HTTP port and path are required')
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise HTTPTransportError('HTTP redirects are forbidden')


def post_json(url, body, directory, label, remaining_seconds, *, max_response_bytes=MAX_RESPONSE_BYTES):
    """Return decoded JSON, or raise after retaining the exact observed attempt.

    The deadline covers process startup and the full HTTP exchange. Up to two
    additional seconds are allowed only to reap a killed child, and reported
    separately. Socket inactivity is not used as the total wall bound.
    """
    checked_url(url)
    if (isinstance(remaining_seconds, bool) or not isinstance(remaining_seconds, (int, float))
            or not math.isfinite(remaining_seconds) or remaining_seconds <= 0):
        raise ValueError('No positive finite request budget remains')
    if type(max_response_bytes) is not int or not 1 <= max_response_bytes <= MAX_RESPONSE_BYTES:
        raise ValueError('Invalid response byte bound')
    if not re.fullmatch(r'[a-z][a-z0-9_-]*', label):
        raise ValueError('Invalid request label')
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    prefix = directory / label
    if list(directory.glob(label + '.*')):
        raise FileExistsError('A recorded request cannot be silently repeated')
    start = time.monotonic()
    timeout = min(60.0, float(remaining_seconds))
    deadline = start + timeout
    raw = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    request_path = Path(str(prefix) + '.request.bin')
    with request_path.open('xb') as stream:
        stream.write(raw)
    save(str(prefix) + '.dispatch.json', {
        'url': url, 'request_sha256': hashlib.sha256(raw).hexdigest(),
        'started_monotonic': start, 'deadline_monotonic': deadline,
        'timeout_seconds': timeout, 'dispatch_reserved': True,
    })
    process = None
    timed_out = False
    error = None
    deadline_observed = None
    try:
        if time.monotonic() >= deadline:
            raise TimeoutError('Budget expired before child dispatch')
        with Path(str(prefix) + '.stderr.txt').open('xb') as stderr:
            process = subprocess.Popen([
                sys.executable, '-I', str(Path(__file__).resolve()), '--worker',
                '--url', url, '--prefix', str(prefix), '--deadline', str(deadline),
                '--max-response-bytes', str(max_response_bytes)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=stderr)
            save(str(prefix) + '.child.json', {'pid': process.pid, 'child_started': True})
            process.wait(timeout=max(0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        timed_out = True
        deadline_observed = time.monotonic()
        error = 'HTTP exchange exceeded its complete wall deadline'
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        cleanup_errors = []
        if process is not None and process.poll() is None:
            try:
                process.kill()
            except BaseException as exc:
                cleanup_errors.append({'operation': 'kill', 'error_type': type(exc).__name__, 'error': str(exc)})
            try:
                process.wait(timeout=2)
            except BaseException as exc:
                cleanup_errors.append({'operation': 'reap', 'error_type': type(exc).__name__, 'error': str(exc)})
                error = 'HTTP child termination is unproven; do not retry'
        end = time.monotonic()
        worker_path = Path(str(prefix) + '.worker.json')
        worker = None
        worker_metadata_error = None
        try:
            if worker_path.exists():
                worker = json.loads(worker_path.read_text())
                if (not isinstance(worker, dict) or type(worker.get('complete')) is not bool
                        or (worker.get('status') is not None and type(worker['status']) is not int)):
                    raise ValueError('Worker metadata has an invalid shape')
        except BaseException as exc:
            worker = None
            worker_metadata_error = {'error_type': type(exc).__name__, 'error': str(exc)}
        response_path = Path(str(prefix) + '.response.bin')
        response = None
        response_read_error = None
        try:
            if response_path.exists():
                with response_path.open('rb') as stream:
                    response = stream.read(max_response_bytes + 2)
                if len(response) > max_response_bytes + 1:
                    raise ValueError('Retained response exceeds the worker byte bound')
        except BaseException as exc:
            response_read_error = {'error_type': type(exc).__name__, 'error': str(exc)}
        receipt = {
            'request_sha256': hashlib.sha256(raw).hexdigest(), 'status': None if worker is None else worker.get('status'),
            'response_sha256': None if response is None else hashlib.sha256(response).hexdigest(),
            'response_bytes_retained': None if response is None else len(response),
            'wall_seconds': end - start, 'timeout_seconds': timeout,
            'deadline_expired': timed_out, 'deadline_overrun_seconds': None if deadline_observed is None else max(0, deadline_observed - deadline),
            'cleanup_seconds_after_deadline_observation': None if deadline_observed is None else end - deadline_observed,
            'child_started': process is not None, 'child_pid': None if process is None else process.pid,
            'child_returncode': None if process is None else process.poll(),
            'child_termination_proven': process is None or process.poll() is not None,
            'worker': worker, 'worker_metadata_error': worker_metadata_error,
            'response_read_error': response_read_error, 'cleanup_errors': cleanup_errors,
            'error': error,
        }
        save(str(prefix) + '.receipt.json', receipt)
    if (timed_out or process is None or process.returncode != 0 or not worker
            or worker_metadata_error is not None or response_read_error is not None
            or cleanup_errors or not worker.get('complete') or response is None
            or type(worker.get('status')) is not int or not 200 <= worker['status'] < 300):
        raise HTTPTransportError(error or 'HTTP request failed; see retained request/response and receipt')
    return json.loads(response)


def worker(args):
    checked_url(args.url)
    prefix = Path(args.prefix)
    raw = Path(str(prefix) + '.request.bin').read_bytes()
    left = args.deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError('Parent deadline already expired')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(args.url, data=raw, headers={'Content-Type': 'application/json'})
    report = {'complete': False, 'status': None, 'error': None, 'body_limit_exceeded': False}
    code = 1
    try:
        try:
            response = opener.open(request, timeout=left)
        except urllib.error.HTTPError as exc:
            response = exc  # Retain error bodies just like successful bodies.
        with response, Path(str(prefix) + '.response.bin').open('xb') as stream:
            report['status'] = response.status
            retained = 0
            while True:
                block = response.read1(min(65536, args.max_response_bytes + 1 - retained))
                if not block:
                    report['complete'] = True
                    break
                stream.write(block)
                stream.flush()
                retained += len(block)
                if retained > args.max_response_bytes:
                    report['body_limit_exceeded'] = True
                    raise HTTPTransportError('Response exceeds retained byte bound')
        code = 0 if 200 <= report['status'] < 300 else 1
    except BaseException as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        save(str(prefix) + '.worker.json', report)
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', action='store_true', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--deadline', type=float, required=True)
    parser.add_argument('--max-response-bytes', type=int, required=True)
    raise SystemExit(worker(parser.parse_args()))
