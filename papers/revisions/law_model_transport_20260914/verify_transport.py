#!/usr/bin/env python3
"""Read retained transport evidence only; never invoke Docker, HTTP, or a model."""
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = 'sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6'
QUALIFICATION_SHA = '46bfc8f075a1676d0f8a9205a26fdb01304ec32c029995faed97125462a07fdd'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def verify():
    qdir = HERE / 'qualification_v4'
    assert sha((qdir / 'qualification.json').read_bytes()) == QUALIFICATION_SHA
    q = read(qdir / 'qualification.json')
    assert q['status'] == 'PASS_NON_MODEL_DOCKER_TRANSPORT'
    assert q['model_calls'] == q['provider_calls'] == q['scientific_candidate_executions'] == 0
    assert q['actual_native_provider_invoked'] is False and all(q['cleanup'].values())
    for name, digest in q['source_files'].items():
        assert sha((HERE / name).read_bytes()) == digest
        assert sha((qdir / 'code' / name).read_bytes()) == digest
    worker = read(qdir / 'worker/worker_report.json')
    assert worker == q['worker_controls'] and worker['status'] == 'PASS'
    assert len(worker['checks']) == 27 and all(c['pass'] is True for c in worker['checks'])
    assert worker['netns'] != q['host_netns'] and worker['host_network_used_by_worker'] is False
    created, terminal = read(qdir / 'created.json'), read(qdir / 'terminal.json')
    assert created['Image'] == terminal['Image'] == q['pinned_worker_image'] == IMAGE
    assert terminal['State']['ExitCode'] == 0 and terminal['State']['Running'] is False
    hc = created['HostConfig']
    assert hc['NetworkMode'] == 'bridge' and hc['Runtime'] == 'runc' and hc['ReadonlyRootfs'] is True
    assert hc['Privileged'] is False and hc['CapDrop'] == ['ALL'] and hc['CapAdd'] is None
    assert 'no-new-privileges' in hc['SecurityOpt'] and hc['PidsLimit'] == 1024
    assert not hc['DeviceRequests'] and not hc['Devices'] and not hc['PortBindings']
    assert hc['Memory'] == hc['MemorySwap'] == 536870912 and hc['NanoCpus'] == 1000000000
    assert created['Config']['User'] == str(worker['uid']) + ':' + str(worker['gid'])
    assert all('noexec' in hc['Tmpfs'][path] for path in ('/tmp', '/var/tmp'))
    mounts = {m['Destination']: m for m in created['Mounts']}
    assert set(mounts) == {'/usr', '/etc/ssl/certs', '/transport', '/model-job', '/output'}
    assert all(m['RW'] is (target == '/output') for target, m in mounts.items())
    assert Path(mounts['/model-job']['Source']).name == 'client'
    assert Path(mounts['/transport']['Source']).name == 'code'
    for kind, reservations, reason in [('job', 11, 'authenticated_job_finished'), ('exp', 0, 'owner_deadline')]:
        closed = read(qdir / kind / 'closed.json')
        assert closed['reserved_attempts'] == reservations and closed['reason'] == reason
        assert closed['socket_removed'] is True and closed['model_owner_stopped_by_gateway'] is False
        assert not (qdir / kind / 'client/socket').exists()
    events = [json.loads(line) for line in (qdir / 'fixture/events.jsonl').read_text().splitlines()]
    actual = [e for e in events if e['event'] == 'request']
    expected_routes = {'/apply-template': 11, '/tokenize': 10, '/v1/chat/completions': 8}
    assert Counter(e['path'] for e in actual) == expected_routes
    assert len(actual) == q['actual_fixture_http_requests'] == 29
    assert not any(e['path'] == '/v1/chat/completions' and e['mode'] in ('input_overflow', 'template_oversize', 'tokenize_oversize') for e in actual)
    assert any(e['event'] == 'upstream_disconnect_observed' and e['mode'] == 'cancel' for e in events)
    attempts = sorted((qdir / 'job/attempts').glob('*/receipt.json'))
    assert len(attempts) == 11
    phase_counts, generation_count, overflow_count = Counter(), 0, 0
    for path in attempts:
        receipt = read(path)
        assert receipt['child_termination_proven'] is True and receipt['cleanup_errors'] == []
        assert receipt['automatic_retry'] is False
        assert receipt['max_input_tokens'] == 2048
        assert receipt['completed_monotonic'] <= receipt['deadline_monotonic'] + 2.1
        assert receipt['generation_reserved'] is (path.parent / 'inference_reserved.json').exists()
        generation_count += receipt['generation_reserved']
        for phase, recorded in receipt['phases'].items():
            phase_counts[phase] += 1
            directory = path.parent / phase
            phase_receipt = read(directory / 'receipt.json')
            dispatch = read(directory / 'dispatch.json')
            assert phase_receipt == recorded
            raw = (directory / 'request.bin').read_bytes()
            response = (directory / 'response.bin').read_bytes() if (directory / 'response.bin').exists() else b''
            assert sha(raw) == dispatch['request_sha256'] == recorded['request_sha256']
            assert sha(response) == recorded['response_sha256'] and len(response) == recorded['response_bytes']
            assert len(response) <= (4194304 if phase == 'generation' else 262144) + 1
            assert dispatch['upstream_path'] == {'template': '/apply-template', 'tokenize': '/tokenize', 'generation': '/v1/chat/completions'}[phase]
            assert recorded['child_termination_proven'] and recorded['cleanup_errors'] == []
            assert recorded['automatic_retry'] is False and recorded['deadline_monotonic'] == receipt['deadline_monotonic']
            assert recorded['cleanup_seconds'] < 2.1
        if receipt['input_count'] is not None:
            template = read(path.parent / 'template/response.bin')['prompt']
            tokens = read(path.parent / 'tokenize/response.bin')['tokens']
            template_request = read(path.parent / 'template/request.bin')
            assert receipt['input_count'] == len(tokens)
            assert sha(template.encode()) == receipt['rendered_prompt_sha256']
            assert sha(canonical(tokens)) == receipt['token_ids_sha256']
            assert sha(canonical(template_request['messages'])) == receipt['messages_sha256']
        if receipt['input_count'] == 2049:
            overflow_count += 1
            assert receipt['generation_reserved'] is False
        if receipt['error'] is None:
            assert receipt['token_usage_known'] and receipt['input_count'] == receipt['prompt_tokens']
            assert 0 <= receipt['completion_tokens'] <= receipt['max_output_tokens']
    assert phase_counts == {'template': 11, 'tokenize': 10, 'generation': 8}
    assert generation_count == 8 and overflow_count == 1
    cancellation = read(qdir / 'job/attempts' / ('7' * 32) / 'receipt.json')
    assert cancellation['termination_reason'] == 'client_disconnected'
    assert cancellation['elapsed_seconds'] == q['cancel_elapsed_seconds'] < 0.9
    success = read(qdir / 'worker/success/client_receipt.json')
    assert success['tokenization_matches_usage'] is True and success['input_count'] == success['prompt_tokens'] == 3
    history = []
    for version, expected_http in [(1, 6), (2, 7), (3, 26), (4, 29)]:
        directory = HERE / ('qualification_v' + str(version))
        prior = read(directory / 'qualification.json')
        requests = [json.loads(line) for line in (directory / 'fixture/events.jsonl').read_text().splitlines()]
        measured = sum(e['event'] == 'request' for e in requests)
        assert measured == expected_http and all(prior['cleanup'].values())
        assert prior['model_calls'] == prior['provider_calls'] == 0
        history.append({'version': version, 'status': prior['status'], 'actual_tiny_http_requests': measured,
                        'qualification_sha256': sha((directory / 'qualification.json').read_bytes())})
    assert history[0]['status'] == 'FAIL_RETAINED'
    assert (HERE / 'qualification_v1/failure_reconciliation.json').exists()
    return {'schema': 'law-model-transport-read-only-verification/v1', 'status': 'PASS',
            'qualification_sha256': QUALIFICATION_SHA, 'source_files': q['source_files'],
            'actual_v4_worker_controls': 27, 'retained_logical_exchange_receipts': 11,
            'retained_http_phase_receipts': dict(phase_counts), 'history': history,
            'all_retained_tiny_http_requests': 68, 'model_calls': 0, 'provider_calls': 0,
            'verification_launches_or_writes': 0, 'remaining_gates': q['remaining_gates'],
            'verifier_sha256': sha(Path(__file__).read_bytes())}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
