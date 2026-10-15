#!/usr/bin/env python3
"""Actual Docker worker controls; only the mounted Unix capability is used."""
import base64
import json
import os
from pathlib import Path
import socket
import struct
import time
from client import close_job, encoded, exchange, receive

JOB, OUT = Path('/model-job'), Path('/output')
config = json.loads((JOB / 'client.json').read_bytes())
checks = []


def body(mode='success'):
    return {'model': config['model'], 'messages': [{'role': 'user', 'content': mode}],
            'temperature': 0, 'seed': 104729, 'max_tokens': 32, 'stream': False}


def check(name, value):
    assert value, name
    checks.append({'name': name, 'pass': True})


def direct(value, *, size=None, disconnect_after=None):
    raw = encoded(value)
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(2)
        sock.connect(str(JOB / 'socket'))
        sock.sendall(struct.pack('!I', len(raw) if size is None else size) + (raw if size is None else b''))
        if disconnect_after is not None:
            time.sleep(disconnect_after)
            return None
        deadline = time.monotonic() + 2
        length = struct.unpack('!I', receive(sock, 4, deadline))[0]
        return json.loads(receive(sock, length, deadline))


def request(rid, **changes):
    return {'job_id': config['job_id'], 'token': config['token'], 'request_id': rid,
            'budget_seconds': 2, 'body': body(), **changes}


def main():
    with socket.socket() as probe:
        probe.settimeout(0.2)
        check('host_loopback_is_not_container_loopback', probe.connect_ex(('127.0.0.1', int(os.environ['LMT_FIXTURE_HOST_PORT']))) != 0)
    check('host_authority_not_projected', sorted(p.name for p in JOB.iterdir()) == ['client.json', 'socket']
          and all(p.suffix == '.py' for p in Path('/transport').iterdir()))
    first = '1' * 32
    response, receipt = exchange(JOB, body(), OUT / 'success', request_id=first, budget_seconds=2)
    check('actual_docker_uds_utf8_success', response is not None and response['ok'] and
          json.loads(base64.b64decode(response['response_base64']))['choices'][0]['message']['content'] == 'fixture Ω')
    check('worker_retains_exact_preflight_token_count', receipt['input_count'] == receipt['prompt_tokens'] == 3 and receipt['tokenization_matches_usage'])
    check('wrong_token_rejected', direct(request('2' * 32, token='wrong'))['rejected'])
    check('other_job_rejected', direct(request('3' * 32, job_id='0' * 32))['rejected'])
    check('duplicate_identity_rejected', direct(request(first))['rejected'])
    check('arbitrary_host_url_rejected', direct(request('4' * 32, url='http://127.0.0.1:1/private'))['rejected'])
    check('wrong_model_rejected', direct(request('5' * 32, body={**body(), 'model': 'other-model'}))['rejected'])
    check('token_limit_rejected', direct(request('6' * 32, body={**body(), 'max_tokens': 99999}))['rejected'])
    check('unfrozen_seed_rejected', direct(request('9' * 32, body={**body(), 'seed': 0}))['rejected'])
    check('oversized_frame_rejected', direct({}, size=256 * 1024 + 1)['rejected'])
    for name, seconds in [('slow_headers', 0.7), ('drip', 0.7)]:
        response, receipt = exchange(JOB, body(name), OUT / name, budget_seconds=seconds)
        check(name + '_complete_wall_bounded', not (response and response.get('ok')) and receipt['elapsed_seconds'] <= seconds + 0.2)
    direct(request('7' * 32, budget_seconds=5, body=body('cancel')), disconnect_after=0.6)
    checks.append({'name': 'client_cancel_sent_host_receipt_required', 'pass': True})
    time.sleep(0.1)
    for name, status, raw in [('failed_http', 503, b'fixture failed HTTP body'), ('redirect', 307, b'fixture redirect body')]:
        response, _ = exchange(JOB, body(name), OUT / name, budget_seconds=2)
        check(name + '_exact_body_retained', response and not response['ok'] and response['receipt']['phases']['generation']['worker']['status'] == status
              and base64.b64decode(response['response_base64']) == raw)
    response, _ = exchange(JOB, body('oversize'), OUT / 'oversize', budget_seconds=3)
    check('response_size_bounded', response and not response['ok'] and response['receipt']['phases']['generation']['response_bytes'] == 4 * 1024 * 1024 + 1)
    response, _ = exchange(JOB, body('token_mismatch'), OUT / 'token_mismatch', budget_seconds=2)
    check('usage_preflight_mismatch_rejected', response and not response['ok'] and response['receipt']['input_count'] == 3 and response['receipt']['prompt_tokens'] == 4)
    response, _ = exchange(JOB, body('input_overflow'), OUT / 'input_overflow', budget_seconds=2)
    check('input_token_overflow_blocks_generation', response and not response['ok'] and response['receipt']['input_count'] == 2049 and not response['receipt']['generation_reserved'])
    for name, phase in [('template_oversize', 'template'), ('tokenize_oversize', 'tokenize')]:
        response, _ = exchange(JOB, body(name), OUT / name, budget_seconds=2)
        check(name + '_preflight_byte_bound', response and not response['ok'] and not response['receipt']['generation_reserved']
              and response['receipt']['phases'][phase]['response_bytes'] == 256 * 1024 + 1)
    try:
        exchange(JOB, body(), OUT / 'expired', budget_seconds=0)
    except ValueError:
        check('expired_budget_no_dispatch', not (OUT / 'expired').exists())
    else:
        raise AssertionError('Expired budget accepted')
    try:
        exchange(JOB, body('x' * (256 * 1024)), OUT / 'large_request', budget_seconds=1)
    except ValueError:
        check('request_size_no_dispatch', not (OUT / 'large_request').exists())
    else:
        raise AssertionError('Oversized request accepted')
    try:
        (JOB / 'unauthorized_write').write_text('bad')
    except OSError:
        check('capability_mount_read_only', True)
    else:
        raise AssertionError('Capability directory writable')
    check('finite_job_allowance_enforced', direct(request('8' * 32))['rejected'])
    check('authenticated_job_close', close_job(JOB) == {'ok': True, 'closed': True})
    report = {'schema': 'law-model-transport-worker-controls/v1', 'status': 'PASS', 'checks': checks,
              'uid': os.getuid(), 'gid': os.getgid(), 'netns': os.readlink('/proc/self/ns/net'),
              'model_calls': 0, 'provider_calls': 0, 'host_network_used_by_worker': False}
    (OUT / 'worker_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'checks': len(checks), 'model_calls': 0}))


if __name__ == '__main__':
    main()
