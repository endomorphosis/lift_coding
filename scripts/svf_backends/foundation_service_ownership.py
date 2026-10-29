"""Protected service promotion for the two explicitly registered SVF foundations.

This module does not install units, reset recovery counters, or complete tasks.
Only an active backend-repair worker beneath the original leased supervisor may
reload an exact pre-registered backend pair. The registration is authored during
operator maintenance; model edits never create service-control authority.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

REGISTRATION = 'config/swissknife_visual_functional_foundation_owners.json'
RUNTIME = 'data/agent_supervisor/swissknife_visual_functional'
PROFILE = 'config/swissknife_visual_functional_supervisor.json'
FAMILIES = {
    'kit-pubsub': ('SVF-043', ('swissknife-visual-functional-native-kit.service',
                             'swissknife-visual-functional-kit-facade.service')),
    'accelerate-supervisor': ('SVF-044', ('swissknife-visual-functional-native-accelerate.service',
                                      'swissknife-visual-functional-accelerate-facade.service')),
}
REQUIRED_SOURCES = {
    'kit-pubsub': {
        'external/ipfs_kit/ipfs_kit_py/assurance/pinned_pubsub.py',
        'scripts/svf_backends/native_pubsub_backend.py',
        'scripts/svf_backends/owned_pubsub_peers.py',
        'scripts/svf_backends/native_kit_service.py',
        'swissknife/scripts/ipfs-kit-native-forwarder.cjs',
        'swissknife/scripts/start-ipfs-kit-mcp-compat.cjs',
    },
    'accelerate-supervisor': {
        'scripts/svf_backends/native_supervisor_backend.py',
        'scripts/svf_backends/native_accelerate_service.py',
        'swissknife/scripts/ipfs-accelerate-native-forwarder.cjs',
        'swissknife/scripts/start-ipfs-accelerate-mcp-compat.cjs',
    },
}
REQUIRED_PROTECTED = {
    'scripts/svf_backends/foundation_service_ownership.py',
    'scripts/svf_backends/validate_pubsub_foundation.py',
    'scripts/svf_backends/validate_supervisor_foundation.py',
    'scripts/svf_backends/fixed_supervisor_worker.py',
    'scripts/svf_backends/fixed_supervisor_output_validator.py',
    'tests/test_svf_pubsub_foundation_contract.py',
    'tests/test_svf_supervisor_foundation_contract.py',
    'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/intent_repository.py',
    'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/database_task_source.py',
    'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/verification/process_runner.py',
    'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/resource_scheduler.py',
    'external/ipfs_kit/ipfs_kit_py/assurance/pinned_ipfs.py',
    'swissknife/config/visual-functional-app-contracts.json',
    'scripts/swissknife_visual_functional_supervisor.py',
    'scripts/swissknife_visual_functional_worker.py',
    'scripts/swissknife_visual_functional_phase_budget.py',
    'scripts/swissknife_visual_functional_review_recheck.py',
    'scripts/swissknife_visual_functional_recovery.py',
    'scripts/swissknife_visual_functional_native_context.py',
    'scripts/svf_backends/foundation_native_entrypoint.py',
    'swissknife/docs/svf-native-foundation-contracts.md',
    'swissknife/docs/svf-pubsub-app-contract.json',
    'swissknife/docs/svf-supervisor-app-contract.json',
    'swissknife/scripts/capture-visual-functional-baseline.mjs',
    'config/swissknife_visual_functional_watchdog.json',
    'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/leased_service_watchdog.py',
}


class ServiceStarting(ValueError):
    """Exact registered unit has no process yet; this is never a live identity."""
    def __init__(self, unit):
        self.unit = unit
        super().__init__('registered unit is waiting for its owned process to start')


class ServicePortsNotReady(ValueError):
    def __init__(self, identity):
        self.identity = identity
        super().__init__('registered process has not bound its expected listeners yet')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular(path: Path) -> None:
    st = path.lstat()
    if not path.is_file() or path.is_symlink() or st.st_uid != os.getuid() or st.st_mode & 0o022:
        raise ValueError('registration/source is not a private owner-controlled regular file')


def _within(root: Path, relative: str) -> Path:
    if type(relative) is not str or not relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('unsafe source path')
    path = root / relative
    if path.resolve() != path or not path.is_relative_to(root):
        raise ValueError('source path has a symlink or escapes the physical checkout')
    return path


def _registration(root: Path) -> dict:
    if not root.is_absolute() or root.resolve() != root:
        raise ValueError('canonical physical checkout is required')
    path = root / REGISTRATION
    regular(path)
    cfg = json.loads(path.read_text())
    if (set(cfg) != {'schema', 'status', 'root', 'families', 'units', 'protected_sha256', 'pubsub_peers'}
            or cfg['schema'] != 'swissknife.foundation-service-registration.v1'
            or cfg['status'] != 'REGISTERED' or cfg['root'] != str(root)
            or set(cfg['families']) != set(FAMILIES)
            or set(cfg['units']) != {u for _, units in FAMILIES.values() for u in units}
            or not REQUIRED_PROTECTED <= set(cfg['protected_sha256'])):
        raise ValueError('missing, draft, or foreign foundation registration')
    for family, (_, units) in FAMILIES.items():
        rule = cfg['families'][family]
        if (set(rule) != {'units', 'mcp_url', 'runtime_root', 'required_sources'}
                or rule['units'] != list(units)
                or set(rule['required_sources']) != REQUIRED_SOURCES[family]):
            raise ValueError('unregistered service family')
        expected_url = 'http://127.0.0.1:18316/mcp' if family == 'kit-pubsub' else 'http://127.0.0.1:18315/mcp'
        expected_runtime = root / RUNTIME / 'backends' / ('native-pubsub' if family == 'kit-pubsub' else 'supervisor-fixtures')
        if rule['mcp_url'] != expected_url or rule['runtime_root'] != str(expected_runtime):
            raise ValueError('foreign service endpoint/runtime')
    for name, expected in cfg['protected_sha256'].items():
        path = _within(root, name)
        regular(path)
        if re.fullmatch('[0-9a-f]{64}', expected) is None or sha(path) != expected:
            raise ValueError('protected source changed')
    return cfg


def process(pid: int) -> dict:
    proc = Path('/proc') / str(pid)
    before = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
    if pid <= 1 or before[0] in {'Z', 'X'} or proc.stat().st_uid != os.getuid():
        raise ValueError('foreign or nonlive process')
    sockets = set()
    for fd in (proc / 'fd').iterdir():
        try: sockets.add(os.readlink(fd))
        except FileNotFoundError: pass
    ports = set()
    for row in Path('/proc/net/tcp').read_text().splitlines()[1:]:
        values = row.split()
        if values[3] == '0A' and values[1].startswith('0100007F:') and 'socket:[' + values[9] + ']' in sockets:
            ports.add(int(values[1].split(':')[1], 16))
    result = {
        'pid': pid, 'start_ticks': before[19], 'ppid': int(before[1]),
        'uid': proc.stat().st_uid, 'executable_path': str((proc / 'exe').resolve()),
        'argv': (proc / 'cmdline').read_bytes().rstrip(b'\0').decode().split('\0'),
        'cwd': str((proc / 'cwd').resolve()), 'binary_sha256': sha(proc / 'exe'),
        'cgroups': (proc / 'cgroup').read_text().splitlines(),
        'environment': dict(x.split('=', 1) for x in (proc / 'environ').read_bytes().decode().split('\0') if '=' in x),
        'ports': sorted(ports),
    }
    if (proc / 'stat').read_text().rsplit(')', 1)[1].split()[:20] != before[:20]:
        # CPU counters can advance. Only lifecycle fields below are stable.
        after = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        if after[0] in {'Z', 'X'} or after[1] != before[1] or after[19] != before[19]:
            raise ValueError('process changed while observing its identity')
    return result


def unit_identity(root: Path, name: str, expected: dict) -> dict:
    if name not in {u for _, units in FAMILIES.values() for u in units} and not re.fullmatch(
            r'swissknife-visual-functional-pubsub-[ab]\.service', name):
        raise ValueError('unregistered unit')
    keys = ('Id', 'MainPID', 'LoadState', 'ActiveState', 'SubState', 'FragmentPath', 'DropInPaths',
            'NeedDaemonReload', 'ControlGroup', 'InvocationID', 'WorkingDirectory', 'KillMode', 'ExecStart')
    raw = subprocess.check_output(['systemctl', '--user', 'show', name, *['--property=' + k for k in keys]],
                                  text=True, timeout=8)
    unit = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
    fragment = Path(expected['fragment'])
    regular(fragment)
    if (fragment != Path.home() / '.config/systemd/user' / name or sha(fragment) != expected['fragment_sha256']
            or unit.get('Id') != name or unit.get('FragmentPath') != str(fragment)
            or unit.get('DropInPaths') or unit.get('NeedDaemonReload') != 'no'
            or unit.get('LoadState') != 'loaded' or unit.get('WorkingDirectory') != expected['cwd']
            or unit.get('KillMode') != 'control-group'):
        raise ValueError('unit is not the exact active registered owner')
    loaded_argv = re.search(r'argv\[\]=(.*?) ;', unit.get('ExecStart', ''))
    if not loaded_argv or loaded_argv.group(1) != ' '.join(expected['argv']):
        raise ValueError('loaded service command changed')
    if (unit.get('ActiveState') == 'activating' and unit.get('SubState') in {'start', 'auto-restart'}
            and unit.get('MainPID') == '0'):
        raise ServiceStarting(name)
    if (unit.get('ActiveState') != 'active' or unit.get('SubState') != 'running'
            or not unit.get('InvocationID') or not unit.get('MainPID', '').isdigit()
            or int(unit['MainPID']) <= 1):
        raise ValueError('registered unit has no exact active process owner')
    p = process(int(unit['MainPID']))
    if (p['argv'] != expected['argv'] or p['cwd'] != expected['cwd']
            or p['binary_sha256'] != expected['binary_sha256']
            or any(p['environment'].get(k) != v for k, v in expected['environment'].items())
            or not unit['ControlGroup'].endswith('/' + name)
            or not any(row.split(':', 2)[-1] == unit['ControlGroup'] for row in p['cgroups'])):
        raise ValueError('process birth/executable/environment/cgroup does not match its unit')
    identity = {'pid': p['pid'], 'start_ticks': p['start_ticks'], 'unit': name,
                'invocation_id': unit['InvocationID'], 'control_group': unit['ControlGroup']}
    if not set(expected['ports']) <= set(p['ports']):
        raise ServicePortsNotReady(identity)
    return identity


def _admission(root: Path, family: str) -> tuple[str, str]:
    sys.path.insert(0, str(root / 'scripts'))
    from swissknife_visual_functional_supervisor import load_profile, assert_campaign_lease
    from swissknife_visual_functional_worker import assert_no_campaign_hold, assert_storage_available
    profile = load_profile(root)
    assert_no_campaign_hold(profile)
    assert_storage_available(profile)
    lease = assert_campaign_lease(profile, root=root)
    status = json.loads((root / RUNTIME / 'state/svf_status.json').read_text())
    task_id = FAMILIES[family][0]
    if status.get('active_task_id') != task_id or status.get('phase') != 'deterministic_command':
        raise ValueError('service promotion is limited to its active declared foundation task')
    target = process(status['pid'])
    from ipfs_accelerate_py.agent_supervisor.rescue.leased_service_watchdog import Config, LeasedServiceWatchdog
    owner_cfg = Config.from_dict(json.loads((root / 'config/swissknife_visual_functional_watchdog.json').read_text()))
    if owner_cfg.repo_root != root or owner_cfg.unit != 'swissknife-visual-functional-supervisor.service':
        raise ValueError('foreign foreground unit registration')
    owners = LeasedServiceWatchdog(owner_cfg)._owners()  # Read-only, no cycle(), state write, or restart.
    foreground = owners.get('child')
    group = owners.get('unit', {}).get('ControlGroup', '')
    if (owners.get('unit', {}).get('ActiveState') != 'active' or not foreground or not group
            or foreground['pid'] != target['pid'] or foreground['start_ticks'] != target['start_ticks']
            or not any(row.split(':', 2)[-1] == group for row in target['cgroups'])):
        raise ValueError('foundation worker is not bound to the original live systemd foreground')
    current = os.getpid()
    worker_seen = False
    for _ in range(128):
        p = process(current)
        if not any(row.split(':', 2)[-1] == group for row in p['cgroups']):
            raise ValueError('foreign cgroup in foundation checker ancestry')
        if p['argv'][1:] == ['scripts/swissknife_visual_functional_worker.py', '--task-id', task_id]:
            worker_seen = True
        if current == target['pid']:
            if not worker_seen or p['start_ticks'] != target['start_ticks']:
                raise ValueError('foundation checker is not beneath its actual worker')
            break
        current = p['ppid']
    else:
        raise ValueError('foundation checker is not beneath the leased supervisor')
    # The registered Node observer only reads procfs. It opens no browser.
    script = ('import {findBrowserOwners} from "./swissknife/scripts/capture-visual-functional-baseline.mjs";'
              'process.stdout.write(JSON.stringify(findBrowserOwners()));')
    owners = json.loads(subprocess.check_output(['/usr/bin/node', '--input-type=module', '-e', script],
                                                cwd=root, text=True, timeout=10))
    if owners:
        raise ValueError('a browser owner is active; wait for its natural release')
    return lease['lease_id'], target['start_ticks']


def _sources(root: Path, cfg: dict, family: str, expected: dict[str, str]) -> None:
    required = set(cfg['families'][family]['required_sources'])
    protected = cfg['protected_sha256']
    # Independent safety sources are mandatory even when the candidate's
    # expected_sources map names only the modules imported by its native unit.
    for name, fingerprint in protected.items():
        path = _within(root, name)
        regular(path)
        if sha(path) != fingerprint:
            raise ValueError('protected source changed during promotion')
    if type(expected) is not dict or not required <= set(expected) or set(expected) - required - set(protected):
        raise ValueError('candidate source closure differs from the registered family')
    ledger = json.loads((root / RUNTIME / 'owned-source-hashes.json').read_text())
    for name, fingerprint in expected.items():
        path = _within(root, name)
        regular(path)
        if (type(fingerprint) is not str or re.fullmatch('[0-9a-f]{64}', fingerprint) is None
                or sha(path) != fingerprint or (protected.get(name) if name in protected else ledger.get(name)) != fingerprint):
            raise ValueError('candidate/protected source is not its independently registered current bytes')


def _atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError('symlink attestation refused')
    tmp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    try:
        with tmp.open('x', encoding='utf8') as out:
            os.chmod(tmp, 0o600)
            json.dump(value, out, sort_keys=True, allow_nan=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        tmp.unlink(missing_ok=True)


def _arm_capture(root, cfg, family, native, expected_sources, lease_id, foreground_birth):
    """Arm a bounded observation window after a genuinely fresh native startup."""
    relative = (RUNTIME + '/backends/foundation-call-witness/' + family + '/'
                + native['invocation_id'] + '/capture.json')
    path = _within(root, relative)
    observer_file = path.parent / 'observer.json'
    regular(observer_file)
    if observer_file.stat().st_size > 16384:
        raise ValueError('protected SDK observer manifest exceeds its source bound')
    observer = json.loads(observer_file.read_text())
    observer_source = 'scripts/svf_backends/foundation_native_entrypoint.py'
    identity = {'pid': native['pid'], 'start_ticks': native['start_ticks']}
    if (observer.get('schema') != 'swissknife.foundation-sdk-call-observer.v1'
            or observer.get('family') != family or observer.get('invocation_id') != native['invocation_id']
            or observer.get('identity') != identity
            or observer.get('observer_sha256') != cfg['protected_sha256'][observer_source]
            or observer.get('observational_only') is not True
            or observer.get('authenticated_origin') is not False or observer.get('completion_authority') is not False
            or any(observer.get('source_sha256', {}).get(k) != v for k, v in expected_sources.items())):
        raise ValueError('fresh native startup has no source-bound protected SDK observer')
    issued = time.time()
    value = {'schema': 'swissknife.foundation-sdk-call-capture.v1', 'capture_id': str(uuid.uuid4()),
             'family': family, 'invocation_id': native['invocation_id'], 'task_id': FAMILIES[family][0],
             'native_process': identity, 'lease_id': lease_id, 'foreground_birth': foreground_birth,
             'issued_at': issued, 'expires_at': issued + 300, 'expected_sources': expected_sources,
             'observational_only': True, 'completion_authority': False}
    if path.exists() or path.is_symlink():
        raise ValueError('immutable capture reservation already exists')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)
    capture = {'path': relative, 'sha256': sha(path), 'bytes': path.stat().st_size,
               'capture_id': value['capture_id'], 'expires_at': value['expires_at']}
    return {'schema': 'swissknife.foundation-sdk-call-capture-ref.v1', 'family': family,
            'invocation_id': native['invocation_id'], 'capture': capture, 'capture_id': value['capture_id'],
            'observer_source': {'path': observer_source, 'sha256': cfg['protected_sha256'][observer_source]}}


def ensure_owned_services(root: Path, *, family: str, expected_sources: dict[str, str], output_dir: Path) -> dict:
    """Promote only a verified source revision into its already registered units."""
    root = Path(root)
    if family not in FAMILIES:
        raise ValueError('unknown foundation family')
    registration_path = root / REGISTRATION
    regular(registration_path)
    registration_sha = sha(registration_path)
    cfg = _registration(root)
    if sha(registration_path) != registration_sha:
        raise ValueError('registration changed during validated load')
    def source_fence():
        regular(registration_path)
        if sha(registration_path) != registration_sha:
            raise ValueError('registration changed during promotion')
        _sources(root, cfg, family, expected_sources)
    output_dir = Path(output_dir)
    if not output_dir.is_absolute() or output_dir.resolve() != output_dir or not output_dir.is_relative_to(root / RUNTIME / 'tasks' / FAMILIES[family][0]):
        raise ValueError('qualification output is outside its declared task')
    lease_id, foreground_birth = _admission(root, family)
    source_fence()
    names = FAMILIES[family][1]
    def same_admission():
        if _admission(root, family) != (lease_id, foreground_birth):
            raise ValueError('leased owner changed during service promotion')
        source_fence()

    def observe_one(name, *, prior=None):
        deadline = time.monotonic() + 35
        generation = None
        while True:
            same_admission()
            ready = True
            try:
                identity = unit_identity(root, name, cfg['units'][name])
            except ServicePortsNotReady as pending:
                identity, ready = pending.identity, False
            except ServiceStarting:
                if generation is not None:
                    raise ValueError('registered process disappeared while waiting for listeners')
                identity, ready = None, False
            if identity is not None:
                if prior is not None and (identity['invocation_id'] == prior['invocation_id']
                        or (identity['pid'], identity['start_ticks']) == (prior['pid'], prior['start_ticks'])):
                    raise ValueError('service reload did not establish a fresh process generation')
                if generation is not None and generation != identity:
                    raise ValueError('promoted service changed generation while waiting for listeners')
                generation = identity
            same_admission()
            if ready:
                return identity
            if time.monotonic() >= deadline:
                raise ValueError('registered service did not bind its listeners within35seconds')
            time.sleep(0.5)

    before = [observe_one(name) for name in names]
    attestation = root / RUNTIME / 'backends/foundation-service-attestations' / (family + '.json')
    if attestation.resolve() != attestation or attestation.is_symlink():
        raise ValueError('symlink service attestation refused before control')
    if attestation.exists():
        regular(attestation)
    # An old writable telemetry document is never proof that current source
    # was imported. Each actual foundation qualification loads a fresh native
    # and facade generation. Ordinary read-only validation never calls here.
    def control_fence(identities):
        same_admission()
        if [unit_identity(root, n, cfg['units'][n]) for n in names] != identities:
            raise ValueError('registered backend changed before promotion')
        # Observation/admission callbacks cannot change a source between the
        # last source check and the following single registered control job.
        same_admission()

    control_fence(before)
    subprocess.run(['systemctl', '--user', 'restart', names[0]], check=True,
                   capture_output=True, text=True, timeout=90)
    native = observe_one(names[0], prior=before[0])
    # The strict facade may refuse startup until native preload and its actual
    # listeners are ready. Preserve the old facade owner until that boundary.
    control_fence([native, before[1]])
    subprocess.run(['systemctl', '--user', 'restart', names[1]], check=True,
                   capture_output=True, text=True, timeout=90)
    facade = observe_one(names[1], prior=before[1])
    after = [native, facade]
    control_fence(after)
    capture = _arm_capture(root, cfg, family, after[0], expected_sources, lease_id, foreground_birth)
    source_fence()
    if _admission(root, family) != (lease_id, foreground_birth):
        raise ValueError('leased owner changed during capture admission')
    witness = {'schema': 'swissknife.foundation-service-source-attestation.v1',
               'family': family, 'at': time.time(), 'lease_id': lease_id,
               'foreground_birth': foreground_birth, 'registration_sha256': registration_sha,
               'processes': after, 'expected_sources': expected_sources, 'sdk_call_witness': capture,
               'reloaded': True, 'work_complete': False, 'completion_authority': False}
    _atomic(attestation, witness)
    witness_path = output_dir / ('service-ownership-' + uuid.uuid4().hex + '.json')
    _atomic(witness_path, witness)
    rule = cfg['families'][family]
    return {'native_process': after[0], 'facade_process': after[1], 'mcp_url': rule['mcp_url'],
            'runtime_root': rule['runtime_root'], 'expected_sources': expected_sources,
            'sdk_call_witness': capture,
            'witness_path': str(witness_path), 'witness_sha256': sha(witness_path)}


def inspect_registered_pubsub_peers(root: Path) -> list[dict]:
    """Read-only process/API proof for two root-registered peers, never discovery."""
    from urllib.request import Request, urlopen
    cfg = _registration(Path(root))
    peers = cfg['pubsub_peers']
    if type(peers) is not list or len(peers) != 2:
        raise ValueError('both real pubsub peers must be independently registered before admission')
    results = []
    for index, expected in enumerate(peers):
        letter = 'ab'[index]
        unit = 'swissknife-visual-functional-pubsub-' + letter + '.service'
        api = 'http://127.0.0.1:' + str(5032 + index)
        if expected['unit'] != unit or expected['api'] != api:
            raise ValueError('foreign pubsub peer registration')
        registration = expected['unit_registration']
        if registration.get('ports') not in ([5032 + index], [5032 + index, 40032 + index]):
            raise ValueError('pubsub API ownership must include its exact registered listener')
        identity = unit_identity(Path(root), unit, expected['unit_registration'])
        repo = Path(expected['repo'])
        if not repo.is_relative_to(Path(root) / RUNTIME / 'backends/native-pubsub') or repo.resolve() != repo:
            raise ValueError('foreign pubsub repo')
        if registration.get('environment', {}).get('IPFS_PATH') != str(repo):
            raise ValueError('registered peer environment does not name its exact owned repo')
        regular(repo / 'config')
        if sha(repo / 'config') != expected['config_sha256']:
            raise ValueError('registered peer repo configuration changed')
        p = process(identity['pid'])
        if p['environment'].get('IPFS_PATH') != str(repo):
            raise ValueError('peer process is not using the registered repo')
        with urlopen(Request(api + '/api/v0/id', method='POST'), timeout=5) as response:
            raw = response.read(16385)
        if len(raw) > 16384:
            raise ValueError('oversized node identity')
        node = json.loads(raw)
        if node.get('ID') != expected['node_id']:
            raise ValueError('API node identity differs from its registered repo')
        if unit_identity(Path(root), unit, expected['unit_registration']) != identity:
            raise ValueError('peer process changed during API proof')
        swarm = '/ip4/127.0.0.1/tcp/' + str(40032 + index) + '/p2p/' + node['ID']
        results.append({**identity, 'role': letter, 'api': api, 'api_url': api,
                        'repo': str(repo), 'repo_path': str(repo), 'node_id': node['ID'],
                        'uid': p['uid'], 'cgroup': identity['control_group'],
                        'executable_path': p['executable_path'], 'executable_sha256': p['binary_sha256'],
                        'swarm_multiaddr': swarm, 'config_sha256': expected['config_sha256']})
    if results[0]['node_id'] == results[1]['node_id']:
        raise ValueError('pubsub endpoints are the same peer')
    return results
