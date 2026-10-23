#!/usr/bin/env python3
"""Qualify a real pinned Docker worker against a tiny owned local endpoint."""
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from transport import identity, owner_check, prepare, save, sha

HERE = Path(__file__).resolve().parent
IMAGE = 'sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6'
DOCKER = ['/usr/bin/docker', '--host', 'unix:///var/run/docker.sock']


def command(argv, seconds=10):
    return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=seconds)


def inspect(name):
    result = command(DOCKER + ['inspect', name])
    return json.loads(result.stdout)[0] if result.returncode == 0 else None


def wait_file(path, process, seconds=3):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if path.exists():
            return json.loads(path.read_bytes())
        if process.poll() is not None:
            raise RuntimeError('Fixture process exited before readiness')
        time.sleep(0.02)
    raise TimeoutError('Fixture readiness exceeded its bound')


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(HERE):
        raise ValueError('Qualification output must remain in this new transport revision')
    out.mkdir(mode=0o700)
    worker = out / 'worker'
    worker.mkdir(mode=0o700)
    code = out / 'code'
    code.mkdir(mode=0o700)
    for source in HERE.glob('*.py'):
        (code / source.name).write_bytes(source.read_bytes())
    key = secrets.token_hex(12)
    name = 'law-model-transport-fixture-' + key
    gateway = fixture = expiry_gateway = None
    cid = None
    started = time.monotonic()
    report = {'schema': 'law-model-transport-docker-qualification/v1', 'status': 'RUNNING',
              'started_at': datetime.now(timezone.utc).isoformat(), 'model_calls': 0, 'provider_calls': 0,
              'scientific_candidate_executions': 0, 'pinned_worker_image': IMAGE,
              'docker_endpoint': 'unix:///var/run/docker.sock', 'host_netns': os.readlink('/proc/self/ns/net'),
              'source_files': {f.name: sha(f.read_bytes()) for f in HERE.glob('*.py')}, 'checks': []}
    logs = []
    def launch(argv, name):
        stdout, stderr = (out / (name + '.stdout')).open('xb'), (out / (name + '.stderr')).open('xb')
        logs.extend([stdout, stderr])
        return subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
    try:
        image = command(DOCKER + ['image', 'inspect', IMAGE])
        assert image.returncode == 0 and json.loads(image.stdout)[0]['Id'] == IMAGE
        save(out / 'image.json', json.loads(image.stdout)[0])
        assert inspect(name) is None
        fixture = launch([sys.executable, '-B', str(HERE / 'fixture_server.py'), '--directory', str(out / 'fixture')], 'fixture')
        ready = wait_file(out / 'fixture/ready.json', fixture)
        owner = {'schema': 'law-model-owner/v1', 'scope': 'tiny_non_model_fixture', 'host': '127.0.0.1',
                 'port': ready['port'], 'process': identity(fixture.pid), 'model': 'tiny-fixture-no-model',
                 'started_monotonic': started, 'deadline_monotonic': started + 45, 'wall_seconds': 45,
                 'startup_seconds': 3, 'model_identity': {'kind': 'no-model-qualification-fixture'}}
        save(out / 'owner.json', owner)
        wrong = deepcopy(owner)
        wrong['process']['command_sha256'] = '0' * 64
        try:
            owner_check(wrong)
        except ValueError:
            report['checks'].append('owner_process_identity_mismatch_rejected')
        else:
            raise AssertionError('Wrong owner accepted')
        real = deepcopy(owner)
        real.update(scope='real_model', wall_seconds=900, startup_seconds=360)
        try:
            owner_check(real)
        except ValueError:
            report['checks'].append('real_owner_900_wall_rejected')
        else:
            raise AssertionError('Wrong real owner wall accepted')
        job = prepare(out / 'job', owner, max_requests=11, max_tokens=64)
        gateway = launch([sys.executable, '-B', str(HERE / 'transport.py'), 'serve', '--job', str(job)], 'gateway')
        wait_file(job / 'started.json', gateway)
        mounts = [(Path('/usr'), '/usr', False), (Path('/etc/ssl/certs'), '/etc/ssl/certs', False),
                  (code, '/transport', False), (job / 'client', '/model-job', False), (worker, '/output', True)]
        argv = DOCKER + ['create', '--pull=never', '--name', name, '--label', 'law.model.transport.fixture=' + key,
                         '--network=bridge', '--runtime=runc', '--read-only', '--cap-drop=ALL',
                         '--security-opt=no-new-privileges', '--pids-limit=1024',
                         '--user', f'{os.getuid()}:{os.getgid()}', '--workdir', '/output',
                         '--cpus=1', '--memory=536870912', '--memory-swap=536870912',
                         '--tmpfs', f'/tmp:rw,nosuid,nodev,noexec,mode=0700,uid={os.getuid()},gid={os.getgid()}',
                         '--tmpfs', f'/var/tmp:rw,nosuid,nodev,noexec,mode=0700,uid={os.getuid()},gid={os.getgid()}',
                         '--env', 'NVIDIA_VISIBLE_DEVICES=void', '--env', 'LMT_FIXTURE_HOST_PORT=' + str(ready['port']),
                         '--entrypoint=/usr/bin/python3.12']
        for source, destination, writable in mounts:
            argv += ['--mount', 'type=bind,src=' + str(source) + ',dst=' + destination + ('' if writable else ',readonly')]
        argv += [IMAGE, '-B', '/transport/worker_controls.py']
        save(out / 'container_create_command.json', argv)
        created = command(argv)
        (out / 'create.stdout').write_bytes(created.stdout)
        (out / 'create.stderr').write_bytes(created.stderr)
        assert created.returncode == 0
        cid = created.stdout.decode().strip()
        data = inspect(cid)
        assert data['Image'] == IMAGE and data['Config']['Labels']['law.model.transport.fixture'] == key
        assert data['HostConfig']['NetworkMode'] == 'bridge' and data['HostConfig']['ReadonlyRootfs'] is True
        assert data['HostConfig']['Runtime'] == 'runc' and data['HostConfig']['DeviceRequests'] is None
        assert sorted((m['Source'], m['Destination'], m['RW']) for m in data['Mounts']) == sorted((str(s), d, w) for s, d, w in mounts)
        save(out / 'created.json', data)
        ran = command(DOCKER + ['start', '--attach', cid], seconds=25)
        (out / 'worker.stdout').write_bytes(ran.stdout)
        (out / 'worker.stderr').write_bytes(ran.stderr)
        terminal = inspect(cid)
        save(out / 'terminal.json', terminal)
        assert ran.returncode == 0 and terminal['State']['ExitCode'] == 0 and not terminal['State']['Running']
        worker_report = json.loads((worker / 'worker_report.json').read_bytes())
        assert worker_report['status'] == 'PASS' and worker_report['netns'] != report['host_netns']
        gateway.wait(timeout=3)
        closed = json.loads((job / 'closed.json').read_bytes())
        assert closed['reason'] == 'authenticated_job_finished' and closed['socket_removed'] and closed['reserved_attempts'] == 11
        attempts = [json.loads(p.read_bytes()) for p in sorted((job / 'attempts').glob('*/receipt.json'))]
        assert len(attempts) == 11 and all(r['child_termination_proven'] and not r['cleanup_errors'] for r in attempts)
        cancellation = json.loads((job / 'attempts' / ('7' * 32) / 'receipt.json').read_bytes())
        assert cancellation['termination_reason'] == 'client_disconnected' and cancellation['elapsed_seconds'] < 0.9
        events = [json.loads(line) for line in (out / 'fixture/events.jsonl').read_text().splitlines()]
        actual = [e for e in events if e['event'] == 'request']
        report['actual_fixture_http_requests'] = len(actual)
        assert len(actual) == 29 and all(e['path'] in ('/apply-template', '/tokenize', '/v1/chat/completions') for e in actual)
        assert sum(e['path'] == '/v1/chat/completions' for e in actual) == 8
        assert not any(e['path'] == '/v1/chat/completions' and e['mode'] == 'input_overflow' for e in actual)
        assert any(e['event'] == 'upstream_disconnect_observed' and e['mode'] == 'cancel' for e in events)
        report['checks'] += ['actual_pinned_bridge_worker_connected_over_read_only_unix_mount',
                             'all_11_reserved_attempts_have_terminated_phase_child_receipts',
                             'wrong_auth_and_duplicate_and_arbitrary_url_never_reached_upstream',
                             'redirect_not_followed', 'client_disconnect_propagated_to_owned_upstream',
                             'authenticated_close_removed_socket_and_exited_gateway',
                             'atomic_template_tokenize_generation_and_input_count_equality',
                             'input_token_overflow_did_not_dispatch_generation']
        report['worker_controls'] = worker_report
        report['actual_fixture_http_requests'] = len(actual)
        report['cancel_elapsed_seconds'] = cancellation['elapsed_seconds']
        expiry_owner = deepcopy(owner)
        expiry_start = time.monotonic()
        expiry_owner.update(started_monotonic=expiry_start, wall_seconds=0.3, deadline_monotonic=expiry_start + 0.3)
        expiry_job = prepare(out / 'exp', expiry_owner, max_requests=1)
        expiry_gateway = launch([sys.executable, '-B', str(HERE / 'transport.py'), 'serve', '--job', str(expiry_job)], 'expiry')
        wait_file(expiry_job / 'started.json', expiry_gateway)
        expiry_gateway.wait(timeout=2)
        expiry_closed = json.loads((expiry_job / 'closed.json').read_bytes())
        assert expiry_closed['socket_removed'] and expiry_closed['reserved_attempts'] == 0
        report['checks'].append('finite_owner_deadline_exits_gateway_without_requests')
        report['status'] = 'PASS_NON_MODEL_DOCKER_TRANSPORT'
    except BaseException as exc:
        report['status'] = 'FAIL_RETAINED'
        report['error'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        for process in (expiry_gateway, gateway, fixture):
            stop(process)
        actual_container = inspect(cid or name)
        if actual_container is not None:
            assert actual_container['Image'] == IMAGE and actual_container['Config']['Labels'].get('law.model.transport.fixture') == key
            removal = command(DOCKER + ['rm', '--force', actual_container['Id']])
            (out / 'remove.stdout').write_bytes(removal.stdout)
            (out / 'remove.stderr').write_bytes(removal.stderr)
        report['cleanup'] = {'fixture_server_exited': fixture is None or fixture.poll() is not None,
                             'gateway_exited': gateway is None or gateway.poll() is not None,
                             'expiry_gateway_exited': expiry_gateway is None or expiry_gateway.poll() is not None,
                             'owned_container_removed': inspect(cid or name) is None}
        report['elapsed_seconds'] = time.monotonic() - started
        report['actual_native_provider_invoked'] = False
        report['qualification_boundary'] = 'Actual same-image bridge container with worker UID, read-only root, host /usr/CA, no capabilities/GPU/Docker socket, and a per-job read-only Unix capability mount. Additional 1 CPU/512 MiB qualification caps are stricter than current native implementation-worker defaults. Provider CLIs/authentication and a model were not invoked.'
        report['remaining_gates'] = ['Actual model/tokenizer/template/decoding and prompt equality qualification.',
                                   'Actual owned model lifecycle qualification at 10000 total wall / 360 startup; no model owner was launched here.',
                                   'Verify real model generation cancellation on disconnect and actual compute/accounting.',
                                   'Authorize an explicit per-job capability projection in the actual native provider launcher; no global provider/Docker settings were changed.',
                                   'Integrate socket post_json with the qualified scientific loop and finite scheduler; preserve attempted-call and token accounting.']
        save(out / 'qualification.json', report)
        for log in logs:
            log.close()
    print(json.dumps({'status': report['status'], 'worker_controls': len(report['worker_controls']['checks']),
                      'actual_fixture_http_requests': report['actual_fixture_http_requests'],
                      'cleanup': report['cleanup'], 'model_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
