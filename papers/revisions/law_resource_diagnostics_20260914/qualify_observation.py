#!/usr/bin/env python3
"""One bounded real Docker lifecycle and explicit stale-descriptor probe.

No model, scientific task, provider, network or historical evidence is used.
The retained parent cgroup is deliberately kept after exact-container cleanup.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from cgroup_observation import CgroupReader, ObservationError, retained_parent_check

DOCKER = ['/usr/bin/docker', '--host', 'unix:///var/run/docker.sock']
IMAGE = 'sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6'


def write(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, sort_keys=True, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())


def command(argv, timeout=5):
    return subprocess.run(argv, capture_output=True, stdin=subprocess.DEVNULL,
                          timeout=timeout, env={'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent'})


def inspect(cid):
    result = command(DOCKER + ['inspect', cid])
    if result.returncode:
        raise RuntimeError('Exact container observation failed: ' + result.stderr.decode()[:500])
    return json.loads(result.stdout)[0]


def exact_absence(result, cid):
    if result.returncode != 1 or result.stdout.strip() not in (b'', b'[]'):
        return False
    try:
        message = result.stderr.decode('ascii').strip()
    except UnicodeError:
        return False
    return re.fullmatch(r'(?i:(?:error:[ \t]*|error response from daemon:[ \t]*)?no such (?:object|container):[ \t]*)'
                        + re.escape(cid), message) is not None


def owned(data, cid, name, marker, parent):
    assert data['Id'] == cid and data['Name'] == '/' + name
    assert data['Image'] == IMAGE and data['Config']['Labels'].get('la032.resource-diagnostic') == marker
    host = data['HostConfig']
    assert host['CgroupParent'] == parent and host['NetworkMode'] == 'none'
    assert host['Memory'] == host['MemorySwap'] == 2147483648 and host['PidsLimit'] == 16
    assert host['ReadonlyRootfs'] is True and host['Privileged'] is False
    assert host['NanoCpus'] == 1000000000 and data['Mounts'] == []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    marker = uuid.uuid4().hex
    name = 'la032-resource-diagnostic-' + marker
    parent_name = 'la032diag' + marker + '.slice'
    parent = Path('/sys/fs/cgroup') / parent_name
    assert not parent.exists()
    cpu = min(os.sched_getaffinity(0))
    report = {'schema': 'la032-resource-observation-qualification/v1',
              'scope': 'One constructed no-model Docker lifecycle and deliberate stale-descriptor probe',
              'historical_LA030_failure_cause_proven': False,
              'model_calls': 0, 'scientific_cases_executed': 0,
              'image': IMAGE, 'docker_endpoint': DOCKER[-1], 'name': name,
              'label': marker, 'parent': str(parent), 'sources': {
                  p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (Path(__file__), Path(__file__).with_name('cgroup_observation.py'))}}
    cid = None
    leaf_reader = parent_reader = None
    stale_fd = None
    try:
        image = command(DOCKER + ['image', 'inspect', IMAGE])
        assert image.returncode == 0 and json.loads(image.stdout)[0]['Id'] == IMAGE
        argv = DOCKER + ['create', '--name', name, '--label', 'la032.resource-diagnostic=' + marker,
                '--cgroup-parent', parent_name, '--network', 'none', '--read-only',
                '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                '--cpus', '1', '--cpuset-cpus', str(cpu), '--memory', '2147483648',
                '--memory-swap', '2147483648', '--pids-limit', '16', '--ulimit', 'core=0',
                '--user', f'{os.getuid()}:{os.getgid()}', '--entrypoint', '/usr/bin/python3.12',
                IMAGE, '-I', '-S', '-c', 'import time; time.sleep(1.5)']
        write(out / 'create_intent.json', {'argv': argv, 'wall_budget_seconds': 30})
        created = command(argv)
        (out / 'create.stdout').write_bytes(created.stdout)
        (out / 'create.stderr').write_bytes(created.stderr)
        assert created.returncode == 0
        cid = created.stdout.decode().strip()
        data = inspect(cid)
        owned(data, cid, name, marker, parent_name)
        write(out / 'created.json', data)
        started = command(DOCKER + ['start', cid])
        assert started.returncode == 0
        running = inspect(cid)
        owned(running, cid, name, marker, parent_name)
        assert running['State']['Running'] and running['State']['Pid'] > 0
        pid = running['State']['Pid']
        relative = next(line.split(':', 2)[2] for line in Path(f'/proc/{pid}/cgroup').read_text().splitlines() if line.startswith('0::'))
        leaf = Path('/sys/fs/cgroup') / relative.lstrip('/')
        assert leaf.parent == parent
        parent_reader, leaf_reader = CgroupReader(parent), CgroupReader(leaf)
        before = parent_reader.sample(parent=True)
        first = leaf_reader.sample()
        assert first['memory.max'] == '2147483648' and first['memory.swap.max'] == '0'
        assert first['pids.max'] == '16' and first['cpuset.cpus.effective'] == str(cpu)
        quota, period = first['cpu.max'].split()
        assert int(quota) == int(period)
        write(out / 'parent_before.json', before)
        write(out / 'leaf_first.json', first)
        # Hold an actual kernel controller file across removal to diagnose the
        # precise failure class that a check/read teardown race can encounter.
        stale_fd = os.open('cpu.stat', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=leaf_reader.fd)
        samples, errors = [first], []
        while True:
            assert time.monotonic() - start < 20, 'Diagnostic lifecycle exceeded 20 seconds'
            terminal = inspect(cid)
            owned(terminal, cid, name, marker, parent_name)
            if not terminal['State']['Running']:
                break
            try:
                samples.append(leaf_reader.sample())
            except ObservationError as exc:
                errors.append(exc.detail)
                break
            time.sleep(.01)
        if terminal['State']['Running']:
            waited = command(DOCKER + ['wait', cid])
            assert waited.returncode == 0 and waited.stdout.strip() == b'0'
            terminal = inspect(cid)
        assert not terminal['State']['Running'] and terminal['State']['Pid'] == 0
        assert terminal['State']['ExitCode'] == 0 and not terminal['State']['OOMKilled']
        write(out / 'terminal.json', terminal)
        after = parent_reader.sample(parent=True)
        parent_checks = retained_parent_check(before, after)
        write(out / 'parent_after.json', after)
        write(out / 'leaf_poll_observations.json', {'samples': samples, 'errors': errors})
        try:
            stale_value = os.read(stale_fd, 65536).decode('ascii')
            stale = {'status': 'read_succeeded', 'value': stale_value}
        except OSError as exc:
            try:
                leaf_reader._raise('read_preopened_controller_file_after_terminal_exit', leaf / 'cpu.stat', exc)
            except ObservationError as observed:
                stale = {'status': 'kernel_read_failed', 'detail': observed.detail}
        write(out / 'stale_descriptor_probe.json', stale)
        report.update(status='PASS_FOR_DIAGNOSTICS_ONLY', parent_checks=parent_checks,
                      ordinary_poll_samples=len(samples), ordinary_poll_errors=len(errors),
                      stale_descriptor_status=stale['status'],
                      stale_descriptor_errno=stale.get('detail', {}).get('errno'),
                      descendant_cpu_seconds=after['cpu_usage_seconds'],
                      descendant_memory_peak_bytes=int(after['memory.peak']))
    except BaseException as exc:
        report.update(status='FAILED', error_type=type(exc).__name__, error=str(exc))
        if isinstance(exc, ObservationError):
            report['observation_error'] = exc.detail
    finally:
        if stale_fd is not None:
            os.close(stale_fd)
        if leaf_reader is not None:
            leaf_reader.close()
        if parent_reader is not None:
            parent_reader.close()
        try:
            if cid is not None:
                data = inspect(cid)
                owned(data, cid, name, marker, parent_name)
                removed = command(DOCKER + ['rm', '-f', cid])
                write(out / 'remove_result.json', {'returncode': removed.returncode,
                       'stdout': removed.stdout.decode(), 'stderr': removed.stderr.decode()})
                assert removed.returncode == 0
                absent = command(DOCKER + ['inspect', cid])
                write(out / 'absent_result.json', {'returncode': absent.returncode,
                       'stdout': absent.stdout.decode(), 'stderr': absent.stderr.decode()})
                assert exact_absence(absent, cid)
                report['exact_container_cleanup_proven'] = True
            if parent.exists():
                with CgroupReader(parent) as retained:
                    final = retained.sample(parent=True)
                write(out / 'parent_after_cleanup.json', final)
                if 'before' in locals():
                    report['final_parent_checks'] = retained_parent_check(before, final)
                report['empty_parent_retained'] = True
        except BaseException as exc:
            report.update(status='FAILED', cleanup_error_type=type(exc).__name__, cleanup_error=str(exc))
        report['elapsed_seconds_including_cleanup'] = time.monotonic() - start
        write(out / 'qualification.json', report)
    print(json.dumps(report))
    return 0 if report['status'] == 'PASS_FOR_DIAGNOSTICS_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
