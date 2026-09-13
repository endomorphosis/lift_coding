#!/usr/bin/python3.12
"""Sequential operator-only LA029 resource boundary; no retries or providers.
Default writes a plan. --execute consumes one separately approved frozen run.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time

DOCKER = ['/usr/bin/docker', '--host', 'unix:///var/run/docker.sock']
IMAGE = 'sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6'
LIMITS = {'cpus': 1, 'memory_bytes': 2147483648, 'swap_bytes': 0, 'pids': 16,
          'per_cell_wall_seconds': 20, 'per_cell_cpu_seconds': 20, 'global_measured_cpu_seconds': 18000}
THREADS = {key: '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'RAYON_NUM_THREADS')}
ENVIRONMENT = {**THREADS, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0',
               'IPFS_AUTO_INSTALL': 'false', 'IPFS_ACCELERATE_AUTO_INSTALL': 'false',
               'IPFS_DATASETS_AUTO_INSTALL': 'false', 'IPFS_KIT_AUTO_INSTALL': 'false',
               'IPFS_KIT_AUTO_INSTALL_DEPS': '0', 'IPFS_DATASETS_ENSURE_INSTALLER': 'false',
               'IPFS_ACCEL_SKIP_CORE': '1', 'IPFS_DATASETS_PY_SKIP_CORE': '1',
               'IPFS_DATASETS_PY_LAZY_INSTALL_ERGOAI': '0', 'CUDA_VISIBLE_DEVICES': '',
               'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
               'IPFS_DATASETS_LOCAL_BIN': '/tmp/local-bin', 'IPFS_DATASETS_LOCAL_DEPS': '/tmp/local-deps',
               'NPM_PREFIX': '/tmp/npm', 'HOME': '/tmp/home',
               'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin'}


def require(ok, reason):
    if not ok: raise RuntimeError(reason)


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path, digest):
    p = Path(path)
    require(p.resolve() == p and p.is_file() and not p.is_symlink() and sha(p) == digest, 'Bound file changed')
    return json.loads(p.read_bytes())


def write(path, value, fresh=True):
    p = Path(path); tmp = p if fresh else p.with_name(p.name + '.pending')
    require(not p.is_symlink(), 'Redirected output')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(value, out, sort_keys=True, indent=2); out.write('\n'); out.flush(); os.fsync(out.fileno())
    if not fresh: os.replace(tmp, p)
    fd = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def command(argv, timeout=5):
    return subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout, env={'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent'})


def absent(result, target):
    if result.returncode != 1 or result.stdout.strip() not in (b'', b'[]'): return False
    try: message = result.stderr.decode('ascii').strip()
    except UnicodeError: return False
    return re.fullmatch(r'(?i:(?:error:[ \t]*|error response from daemon:[ \t]*)?no such (?:object|container):[ \t]*)' + re.escape(target), message) is not None


def inspect(target):
    result = command(DOCKER + ['inspect', target])
    if absent(result, target): return None
    require(result.returncode == 0, 'Docker observation unavailable')
    values = json.loads(result.stdout)
    require(len(values) == 1, 'Ambiguous Docker identity')
    return values[0]


def owned(data, name, authority, mounts):
    require(data['Name'] == '/' + name and data['Config']['Labels'].get('la029.admission') == authority
            and data['Image'] == IMAGE, 'Container authority/identity differs')
    expected = {(str(a), b): writable for a, b, writable in mounts}
    actual = {(m['Source'], m['Destination']): m['RW'] for m in data['Mounts'] if m['Type'] == 'bind'}
    require(actual == expected, 'Container mounts differ')
    return data['Id']


def configured(data, cpu, parent):
    host = data['HostConfig']
    require(host['NanoCpus'] == 1000000000 and host['CpusetCpus'] == str(cpu)
            and host['Memory'] == 2147483648 and host['MemorySwap'] == 2147483648
            and host['PidsLimit'] == 16 and host['NetworkMode'] == 'none'
            and host['ReadonlyRootfs'] is True and not host['Privileged']
            and host['CgroupParent'] == parent, 'Docker resource boundary differs')


def cgroup_for_pid(pid):
    text = (Path('/proc') / str(pid) / 'cgroup').read_text()
    relative = next(line.split(':', 2)[2] for line in text.splitlines() if line.startswith('0::'))
    root = (Path('/sys/fs/cgroup') / relative.lstrip('/')).resolve()
    require(root.is_relative_to('/sys/fs/cgroup'), 'Unexpected cgroup path')
    return root


def sample(root):
    fields = {name: (root / name).read_text().strip() for name in
              ('cpu.stat', 'cpu.max', 'cpuset.cpus.effective', 'memory.current', 'memory.peak',
               'memory.max', 'memory.swap.max', 'memory.events', 'pids.current', 'pids.max', 'pids.events')}
    counters = dict(line.split() for line in fields['cpu.stat'].splitlines())
    fields['cpu_usage_seconds'] = int(counters['usage_usec']) / 1000000
    fields['observed_monotonic'] = time.monotonic()
    return fields


def verify_sample(fields, cpu):
    quota, period = fields['cpu.max'].split()
    require(quota != 'max' and int(quota) == int(period) and fields['cpuset.cpus.effective'] == str(cpu), 'Effective CPU control drift')
    require(fields['memory.max'] == '2147483648' and fields['memory.swap.max'] == '0'
            and fields['pids.max'] == '16', 'Effective memory/swap/process control drift')


def parent_name(authority, index):
    require(re.fullmatch(r'[0-9a-f]{64}', authority) and type(index) is int and 0 <= index < 900,
            'Invalid exact parent identity')
    return 'la029' + authority[:24] + 'x' + f'{index:04d}' + '.slice'


def parent_sample(root):
    require(root.is_dir() and not root.is_symlink(), 'Retained parent unavailable')
    fields = {name: (root / name).read_text().strip() for name in
              ('cpu.stat', 'memory.current', 'memory.peak', 'memory.events', 'pids.current', 'pids.events', 'cgroup.events')}
    counters = dict(line.split() for line in fields['cpu.stat'].splitlines())
    fields.update(cpu_usage_seconds=int(counters['usage_usec']) / 1000000,
                  cpu_user_seconds=int(counters['user_usec']) / 1000000,
                  cpu_system_seconds=int(counters['system_usec']) / 1000000,
                  inode=root.stat().st_ino, observed_monotonic=time.monotonic())
    return fields


def parent_empty(reading):
    events = dict(line.split() for line in reading['cgroup.events'].splitlines())
    return reading['pids.current'] == '0' and events.get('populated') == '0'


class Watchdog:
    """Deadline enforcement is independent of blocking Docker CLI observations."""
    def __init__(self, start, cpu, cid_ref, out, parent, clock=time.monotonic, kill=None):
        self.start, self.cpu, self.cid_ref, self.out, self.clock = start, cpu, cid_ref, out, clock
        self.parent = parent; self.parent_inode = None
        self.kill = kill or (lambda cid: command(DOCKER + ['kill', cid], timeout=5))
        self.stop = threading.Event(); self.thread = threading.Thread(target=self.loop, daemon=True)
        self.root = None; self.samples = []; self.parent_samples = []; self.error = None; self.kill_result = None

    def fail(self, reason):
        if self.error is not None: return
        self.error = {'reason': reason, 'at_monotonic': self.clock(), 'cid': self.cid_ref.get('cid')}
        # The deadline action precedes potentially blocking persistence.
        if self.cid_ref.get('cid'):
            try:
                result = self.kill(self.cid_ref['cid'])
                self.kill_result = {'returncode': result.returncode}
                if self.parent.exists():
                    reading = parent_sample(self.parent)
                    self.kill_result.update(parent_after_kill=reading, whole_group_empty_after_kill=parent_empty(reading),
                                            elapsed_to_postkill_parent_observation=self.clock()-self.start)
            except BaseException as exc: self.kill_result = {'error_type': type(exc).__name__}
        try: write(self.out / 'budget_decision.json', self.error)
        except BaseException as exc: self.error['persistence_error'] = type(exc).__name__

    def check(self):
        if self.clock() - self.start >= 20:
            self.fail('whole_cell_wall_budget'); return
        try:
            if self.parent.exists():
                reading = parent_sample(self.parent)
                require(self.parent_inode in (None, reading['inode']), 'Parent counter identity changed')
                require(not self.parent_samples or reading['cpu_usage_seconds'] >= self.parent_samples[-1]['cpu_usage_seconds'],
                        'Parent CPU counter regressed')
                self.parent_inode = reading['inode']; self.parent_samples.append(reading)
                events = dict(line.split() for line in reading['memory.events'].splitlines())
                if reading['cpu_usage_seconds'] >= 20: self.fail('whole_group_cpu_budget')
                elif any(int(events.get(k, 0)) for k in ('oom', 'oom_kill', 'max')): self.fail('memory_limit_event')
                elif any(int(v) for k,v in (line.split() for line in reading['pids.events'].splitlines()) if k=='max'): self.fail('process_limit_event')
            elif self.parent_inode is not None:
                self.fail('persistent_parent_disappeared')
            if self.root is not None and self.root.exists():
                reading = sample(self.root); verify_sample(reading, self.cpu); self.samples.append(reading)
                pids_events = dict(line.split() for line in reading['pids.events'].splitlines())
                if int(pids_events.get('max', 0)): self.fail('process_limit_event')
        except (FileNotFoundError, ProcessLookupError):
            # The leaf may disappear after normal exit. The private parent
            # must remain, and its final counters/empty state are mandatory.
            if self.parent_inode is not None and not self.parent.exists(): self.fail('persistent_parent_disappeared')
        except BaseException as exc: self.fail('resource_observation_' + type(exc).__name__)

    def loop(self):
        while not self.stop.is_set() and self.error is None:
            self.check(); self.stop.wait(.02)

    def finish(self):
        self.stop.set(); self.thread.join(timeout=6)
        require(not self.thread.is_alive(), 'Watchdog did not stop')


def clean_git(root):
    result=command(['git', '--no-optional-locks', '-C', str(root), 'status', '--porcelain=v1', '--untracked-files=all'])
    require(result.returncode == 0 and result.stdout == b'', 'Git cleanliness unavailable or dirty')


def source_guard(admission):
    root = Path(admission['source_root'])
    require(root.resolve() == root and root.is_dir(), 'Source root redirected')
    head = command(['git', '--no-optional-locks', '-C', str(root), 'rev-parse', 'HEAD'])
    require(head.returncode == 0 and head.stdout.decode().strip() == admission['source_commit'], 'Frozen source commit changed')
    clean_git(root)
    for rel, expected in admission['source_files'].items():
        require(sha(root / rel) == expected and not (root / rel).is_symlink(), 'Source file changed')
    for rel, pin in admission['native_pins'].items():
        observed = command(['git', '--no-optional-locks', '-C', str(root / rel), 'rev-parse', 'HEAD'])
        require(observed.returncode == 0 and observed.stdout.decode().strip() == pin, 'Native checkout pin changed')
        clean_git(root / rel)
    return root


def runtime_guard(admission, root):
    """Invoke the existing native exact-tree verifier once before any cell."""
    runner = root / 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/grok_cli_runner.py'
    require(sha(runner) == admission['native_runtime_verifier_sha256'], 'Native runtime verifier changed')
    for key, value in ENVIRONMENT.items():
        if key.startswith('IPFS_') or key == 'PYTHONDONTWRITEBYTECODE': os.environ[key] = value
    spec = importlib.util.spec_from_file_location('la029_frozen_runtime_verifier', runner)
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    profile = {'schema': 'docker-research-toolchain/v1', 'root': admission['runtime_root'],
               'manifest': admission['runtime_manifest']['path'],
               'manifest_sha256': admission['runtime_manifest']['sha256']}
    result = module._research_task_toolchain({'IPFS_ACCELERATE_AGENT_RESEARCH_TOOLCHAIN_JSON': json.dumps(profile)})
    require(result['root'] == admission['runtime_root'], 'Qualified runtime root differs')
    return result


def create_argv(admission, authority, index, mounts, name, worker):
    argv = DOCKER + ['create', '--name', name, '--label', 'la029.admission=' + authority,
                    '--cgroup-parent', parent_name(authority, index), '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                    '--cpus', '1', '--cpuset-cpus', str(admission['cpu']), '--memory', '2147483648',
                    '--memory-swap', '2147483648', '--pids-limit', '16', '--ulimit', 'core=0',
                    '--user', str(os.getuid()) + ':' + str(os.getgid()), '--workdir', '/source',
                    '--tmpfs', '/tmp:rw,nosuid,nodev,size=67108864,mode=1777']
    for source, destination, writable in mounts:
        argv += ['--mount', 'type=bind,src=' + str(source) + ',dst=' + destination + ('' if writable else ',readonly')]
    environment = {**ENVIRONMENT, 'PYTHONPATH': str(Path(admission['runtime_root']) / 'python') + ':/opt/ipfs-validation-site-packages'}
    for key, value in environment.items(): argv += ['--env', key + '=' + value]
    argv += ['--entrypoint', '/usr/bin/python3.12', IMAGE, '-B',
             '/source/papers/completion/law_to_action/benchmark/fixed_action_operator/cell.py',
             '--inputs', '/inputs.json', '--inputs-sha256', admission['inputs']['sha256'],
             '--index', str(index), '--shared', '/shared', '--output', '/output']
    return argv


def run_cell(admission, authority, index, directory, shared):
    started = time.monotonic(); worker = directory / 'worker'; worker.mkdir(mode=0o700)
    host = directory / 'host'; host.mkdir(mode=0o700)
    source = source_guard(admission)
    runtime = Path(admission['runtime_root'])
    mounts = [(source, '/source', False), (runtime, str(runtime), False),
              (Path(admission['inputs']['path']), '/inputs.json', False), (shared, '/shared', True), (worker, '/output', True)]
    name = 'la029-' + authority[:16] + '-' + f'{index:04d}'
    parent = Path('/sys/fs/cgroup') / parent_name(authority, index)
    require(not parent.exists(), 'Exact fresh private cgroup parent required')
    ref = {}; watcher = Watchdog(started, admission['cpu'], ref, host, parent); created_attempted = False
    report = {'schema': 'la029-operator-cell-envelope/v1', 'index': index, 'admission_sha256': authority,
              'started_monotonic': started, 'pending': None, 'admitted': False,
              'cpu_allowance_seconds': 20, 'private_parent_cgroup': str(parent), 'parent_preexisting': False, 'termination_proven': False,
              'cleanup_proven': False, 'scientific_retry': False}
    try:
        require(inspect(name) is None, 'Exact container name already exists')
        write(host / 'consumed.json', {'index': index, 'admission_sha256': authority, 'effect_outcome': 'unknown_before_create'})
        watcher.thread.start()
        created_attempted = True; report['pending'] = 'container_create'
        result = command(create_argv(admission, authority, index, mounts, name, worker), timeout=max(.001, 20 - (time.monotonic() - started)))
        require(result.returncode == 0 and re.fullmatch(b'[0-9a-f]{64}\n?', result.stdout), 'Docker create not acknowledged')
        cid = result.stdout.decode().strip(); data = inspect(cid); require(data is not None, 'Created container disappeared')
        require(owned(data, name, authority, mounts) == cid, 'Created CID differs'); ref['cid'] = cid
        configured(data, admission['cpu'], parent.name); write(host / 'created.json', data)
        require(watcher.error is None and time.monotonic() - started < 20, 'Prestart wall budget exhausted')
        report.update(pending='running', container_id=cid)
        with (host / 'stdout.txt').open('xb') as out, (host / 'stderr.txt').open('xb') as err:
            process = subprocess.Popen(DOCKER + ['start', '--attach', cid], stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, env={'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent'})
            while process.poll() is None:
                if watcher.root is None:
                    current = inspect(cid)
                    if current and current['State']['Pid']:
                        watcher.root = cgroup_for_pid(current['State']['Pid'])
                        require(watcher.root.parent == parent, 'Running child outside exact private parent')
                if watcher.error is not None:
                    try: process.wait(timeout=6)
                    except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=2)
                    break
                time.sleep(.02)
            report['attach_returncode'] = process.returncode
        terminal = inspect(cid); require(terminal is not None, 'Terminal container unavailable')
        owned(terminal, name, authority, mounts); write(host / 'terminal.json', terminal)
        final = parent_sample(parent); write(host / 'parent_after_exit.json', final)
        require(watcher.parent_inode in (None, final['inode']), 'Terminal parent identity changed')
        report['termination_proven'] = terminal['State']['Running'] is False and terminal['State']['Pid'] == 0 and parent_empty(final)
        report.update(measured_group_cpu_seconds=final['cpu_usage_seconds'], measured_group_user_cpu_seconds=final['cpu_user_seconds'],
                      measured_group_system_cpu_seconds=final['cpu_system_seconds'], measured_group_peak_memory_bytes=int(final['memory.peak']))
        report['wall_seconds_to_group_exit_observation'] = time.monotonic() - started
        report['process_exit_code'] = terminal['State']['ExitCode']; report['oom_killed'] = terminal['State']['OOMKilled']
        require(report['termination_proven'], 'Whole group termination unproven')
        watcher.finish()
        write(host / 'resources.json', {'leaf_samples': watcher.samples, 'parent_samples': watcher.parent_samples, 'decision': watcher.error,
              'kill_result': watcher.kill_result, 'samples_are_cumulative_not_additive': True,
              'final_descendant_counter_retained': True, 'final_parent': final})
        require(watcher.error is None and not report['oom_killed'] and report['process_exit_code'] == 0
                and report['attach_returncode'] == 0 and report['wall_seconds_to_group_exit_observation'] <= 20
                and final['cpu_usage_seconds'] <= 20 and int(final['memory.peak']) <= 2147483648,
                'Cell failed or exceeded its fixed resource boundary')
        kernel = json.loads((worker / 'child_boundary.json').read_bytes()); verify_sample(kernel, admission['cpu'])
        require(not any(int(v) for k, v in (line.split() for line in final['memory.events'].splitlines()) if k in ('oom', 'oom_kill', 'max')), 'Final memory limit event')
        require(not any(int(v) for k,v in (line.split() for line in final['pids.events'].splitlines()) if k=='max'), 'Final process limit event')
        body = json.loads((worker / 'result.json').read_bytes())
        require(body['schema'] == 'la029-fixed-action-cell-result/v1' and body['index'] == index
                and body['inputs_sha256'] == admission['inputs']['sha256'] and body['store_close_completed'] is True
                and body['slot'] == admission['_schedule'][index],
                'Actual frozen cell result missing')
        report.update(result_sha256=sha(worker / 'result.json'), cell_result=body,
                      observed_effects_are_not_model_self_report=True, pending=None)
    except BaseException as exc:
        report.update(error_type=type(exc).__name__, error=str(exc), requires_reconciliation=created_attempted)
    finally:
        if watcher.thread.is_alive():
            try: watcher.finish()
            except BaseException as exc:
                report.update(watchdog_shutdown_error=type(exc).__name__, error_type=type(exc).__name__)
        # A watcher shutdown failure must not skip exact-owned cleanup or
        # retained final counters. No name is removed before our create attempt.
        # Preexisting names are never cleaned. An ambiguous create is cleaned
        # only after exact label/image/mount identity is independently observed.
        if created_attempted:
            try:
                data = inspect(ref.get('cid', name))
                if data is not None:
                    cid = owned(data, name, authority, mounts)
                    cleanup = command(DOCKER + ['rm', '-f', cid], timeout=6)
                    report['cleanup_returncode'] = cleanup.returncode
                    report['cleanup_proven'] = cleanup.returncode == 0 and inspect(cid) is None
                else:
                    report['cleanup_proven'] = bool(ref.get('cid'))
                    if not ref.get('cid'): report['pending'] = 'uncertain_create_manual_reconciliation'
            except BaseException as exc:
                report['cleanup_error_type'] = type(exc).__name__
        if parent.exists():
            try:
                retained = parent_sample(parent); write(host / 'parent_after_cleanup.json', retained)
                require(parent_empty(retained) and watcher.parent_inode in (None, retained['inode']), 'Final parent not empty/stable')
                report.update(final_parent_empty=True, measured_group_cpu_seconds=retained['cpu_usage_seconds'],
                              measured_group_user_cpu_seconds=retained['cpu_user_seconds'], measured_group_system_cpu_seconds=retained['cpu_system_seconds'],
                              measured_group_peak_memory_bytes=int(retained['memory.peak']), empty_parent_retained=True)
                require(retained['cpu_usage_seconds'] <= 20, 'Final CPU overshoot')
            except BaseException as exc:
                report.update(parent_accounting_error=type(exc).__name__, error_type=type(exc).__name__)
        elif created_attempted:
            report.update(parent_accounting_unknown=True, error_type=report.get('error_type', 'MissingFinalParent'))
        report['admitted'] = ('cell_result' in report and report['termination_proven'] and report['cleanup_proven']
                              and report.get('error_type') is None and watcher.error is None and report.get('final_parent_empty') is True)
        report['elapsed_seconds_including_cleanup'] = time.monotonic() - started
        report['watchdog_kill_result'] = watcher.kill_result
        report['cost_scope'] = 'Measured final descendant-inclusive CPU/user/system and memory peak from a fresh private parent retained empty after exact child cleanup. CPU samples are cumulative, never added. Host orchestration/cleanup wall is separately reported; unknown counters stop the run.'
        write(host / 'result.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admission', required=True, type=Path)
    parser.add_argument('--admission-sha256', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(); os.umask(0o077)
    admission = load(args.admission, args.admission_sha256)
    require(admission['schema'] == 'la029-root-operator-admission/v1'
            and admission['controller_sha256'] == sha(__file__) and admission['limits'] == LIMITS,
            'Fixed controller/admission limits changed')
    inputs = load(admission['inputs']['path'], admission['inputs']['sha256'])
    require(inputs['schema'] == 'la029-frozen-fixed-action-inputs/v1'
            and len(inputs['schedule']) == 900 and len(inputs['candidates']) == 60, 'Frozen population differs')
    require(type(admission['cpu']) is int and admission['cpu'] in os.sched_getaffinity(0), 'Assigned CPU unavailable')
    source = source_guard(admission)
    load(admission['runtime_manifest']['path'], admission['runtime_manifest']['sha256'])
    output = Path(admission['output_root'])
    require(output.is_absolute() and output.resolve() == output and not output.exists(), 'Fresh private output required')
    output.mkdir(mode=0o700)
    plan = {'schema': 'la029-operator-plan/v1', 'admission_sha256': args.admission_sha256,
            'controller_sha256': sha(__file__), 'limits': LIMITS, 'cells': 900, 'image': IMAGE,
            'source': admission['source_commit'], 'inputs_sha256': admission['inputs']['sha256'],
            'no_retries': True, 'cpu': admission['cpu'], 'old_diagnostic_runs_preserved': admission['prior_runs']}
    write(output / 'plan.json', plan)
    if not args.execute: return
    require(admission.get('approved') is True and admission.get('bounded_resource_qualification_passed') is True,
            'Actual bounded resource qualification and root admission required before scientific dispatch')
    write(output / 'runtime_verification.json', runtime_guard(admission, source))
    admission['_schedule'] = inputs['schedule']
    lock = os.open(output / 'controller.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    write(output / 'one_use.json', {'admission_sha256': args.admission_sha256, 'consumed_before_any_cell': True})
    shared = output / 'shared'; shared.mkdir(mode=0o700)
    cells = output / 'cells'; cells.mkdir(mode=0o700)
    results = []; measured = 0.0; started_count = 0; controller_started = time.monotonic(); host_cpu_started = time.process_time()
    failure = None
    try:
        for index, slot in enumerate(inputs['schedule']):
            require(LIMITS['global_measured_cpu_seconds'] - measured >= 20, 'Global measured CPU budget has less than one full cell allowance remaining')
            directory = cells / f'{index:04d}'; directory.mkdir(mode=0o700)
            write(directory / 'reserved.json', {'index': index, 'slot': slot, 'maximum_new_cpu_seconds': 20,
                                                'global_measured_cpu_seconds_before': measured, 'consumed_before_dispatch': True})
            started_count += 1
            try: result = run_cell(admission, args.admission_sha256, index, directory, shared)
            except BaseException as exc:
                result = {'index': index, 'admitted': False, 'error_type': type(exc).__name__,
                          'dispatch_or_cost_outcome_unknown': True, 'requires_reconciliation': True}
                write(directory / 'controller_failure.json', result)
            results.append(result)
            cost = result.get('measured_group_cpu_seconds')
            if type(cost) in (int, float) and cost >= 0: measured += cost
            else: result['cost_unknown_stops_batch'] = True
            write(output / 'progress.json', {'finished_cells': len(results), 'measured_cpu_seconds': measured,
                                            'last_admitted': result['admitted']}, fresh=len(results) == 1)
            if not result['admitted'] or cost is None: break
            require(measured <= LIMITS['global_measured_cpu_seconds'], 'Global measured CPU overshoot')
    except BaseException as exc:
        failure = {'error_type': type(exc).__name__, 'error': str(exc)}
    finally:
        write(output / 'result.json', {'schema': 'la029-fixed-action-operator-result/v1', 'results': results,
              'admission_sha256': args.admission_sha256, 'all900_resource_admitted': len(results) == 900 and all(r['admitted'] for r in results),
              'remaining_not_started': inputs['schedule'][started_count:], 'measured_known_group_cpu_seconds': measured,
              'host_controller_cpu_seconds': time.process_time() - host_cpu_started,
              'host_controller_wall_seconds': time.monotonic() - controller_started, 'failure': failure,
              'actual_cpu_accounting': 'Sum of measured final fresh-parent descendant CPU counters. Unknown costs retained and stop; no reservation substituted as usage.',
              'hard_cumulative_prior_usage_claimed': False, 'prior_runs': admission['prior_runs'],
              'model_calls': 0, 'scientific_retries': 0})
        fcntl.flock(lock, fcntl.LOCK_UN); os.close(lock)


if __name__ == '__main__': main()
