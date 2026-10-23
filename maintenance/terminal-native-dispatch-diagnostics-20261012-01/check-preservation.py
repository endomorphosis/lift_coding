"""Named-only M/N byte preservation after the independently supplied N freeze.

No discovery, production imports, database reads, provider calls or Git changes.
The mandatory manifest SHA must be supplied independently by the root.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import stat

C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
N = Path(__file__).resolve().parent
M = N.parent / 'terminal-nomination-lifecycle-20261012-01'
M_EVIDENCE_SHA = 'fdf4456ba06da9e80000768e3a7c2aac122f5d23a9bd0ce818b44b1b5f5f97db'
M_PRESERVATION_SHA = '8d1b3d5a85d70c81d6bed7be29fc9a65aada639815139a1626bc84b65064df10'
M_SOURCE_SHA = '657895d3a12ae52e142cfc0546f0acf6640e89c42d3a2e102fc35438382bc122'
BEGINNING_SHA = '48b2c0f66711ec65005e225ce617021e4589cb0fcceb3403521d6f11c1c0d8f6'
ADDITIONAL_BASELINE_SHA = '41fee072d57df61a3f8a952e36695f1be4292b1be3feee7fc78666b43f6f1006'
RUNNER = 'ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py'
MANDATORY_EXISTING = frozenset({
 'benchmarks/agent_supervisor/container_coding/terminal_container_supervisor.py',
 'ipfs_accelerate_py/agent_supervisor/entrypoints/admitted_benchmark_runtime.py',
 'ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py', RUNNER})
BRIDGE = 'ipfs_accelerate_py/agent_supervisor/todo_daemon/database_portal_bridge.py'
NEW = frozenset({'ipfs_accelerate_py/agent_supervisor/runtime/native_dispatch_diagnostics.py',
 'test/api/test_native_dispatch_diagnostics.py',
 'benchmarks/agent_supervisor/container_coding/test_terminal_native_dispatch_diagnostics.py'})
DENY_SUFFIXES = frozenset({'.duckdb', '.ducklake', '.db', '.sqlite', '.sqlite3',
    '.pem', '.key', '.p12', '.pfx', '.jsonl'})
DENY_PARTS = frozenset({'.codex', '.git', 'credentials', 'private', 'hidden', 'oracle',
    'rollouts', 'transcripts', 'secrets', 'keys'})
DENY_NAMES = frozenset({'auth.json', '.env', 'token', 'private-key', 'supervisor.stdout', 'supervisor.stderr'})
MAX_FILE = 256_000_000
MAX_DOCUMENT = 8_000_000
MAX_CHECKS = 4096
STAT_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
    'st_size', 'st_mtime_ns', 'st_ctime_ns')
cache, witnesses, checks, inputs = {}, {}, [], []


def require(condition, message):
    if condition is not True:
        raise ValueError(message)


def digest(value):
    require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None,
        'Independent canonical SHA256 required')
    return value


def count(value):
    require(type(value) is int and 0 <= value <= MAX_FILE, 'Bounded non-Boolean byte count required')
    return value


def relative(value):
    require(type(value) is str and 0 < len(value.encode()) <= 8192, 'Bounded named relative path required')
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.parts and '..' not in path.parts and str(path) == value,
        'Canonical relative path required')
    return value


def public_path(value):
    text = str(value)
    path = Path(text)
    require(path.is_absolute() and '..' not in path.parts and str(PurePosixPath(text)) == text,
        'Canonical explicitly named absolute path required')
    require(path.suffix.lower() not in DENY_SUFFIXES and path.name.lower() not in DENY_NAMES
        and not any(part.lower() in DENY_PARTS for part in path.parts), 'Private/body path denied')
    require(path.is_relative_to(C) or path.is_relative_to(M.parent), 'Path outside nominated workspace roots')
    return path


def witness(info):
    return tuple(getattr(info, key) for key in STAT_FIELDS)


def opened(path):
    path = public_path(path)
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = following
        handle = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(handle)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and 0 <= info.st_size <= MAX_FILE, 'Bounded single-link regular public file required')
        except BaseException:
            os.close(handle)
            raise
        return handle, parent, info
    except BaseException:
        os.close(parent)
        raise


def capture(path, *, maximum=MAX_FILE, retain=False):
    path = public_path(path)
    handle, parent, before = opened(path)
    try:
        require(before.st_size <= maximum, 'Named public document exceeds byte bound')
        size, hashed, chunks = 0, hashlib.sha256(), []
        while True:
            block = os.read(handle, min(1_048_576, maximum + 1 - size))
            if not block:
                break
            size += len(block)
            require(size <= maximum, 'Public file exceeded bounded read')
            hashed.update(block)
            if retain:
                chunks.append(block)
        require(size == before.st_size and witness(before) == witness(os.fstat(handle))
            == witness(os.stat(path.name, dir_fd=parent, follow_symlinks=False)), 'Public witness changed during read')
    finally:
        os.close(handle)
        os.close(parent)
    pin = {'path': str(path), 'bytes': size, 'sha256': hashed.hexdigest()}
    cache[str(path)], witnesses[str(path)] = pin, witness(before)
    return pin, b''.join(chunks) if retain else None


def observed(path):
    path = public_path(path)
    if str(path) not in cache:
        capture(path)
    return cache[str(path)]


def document(path, expected=None):
    pin, raw = capture(path, maximum=MAX_DOCUMENT, retain=True)
    if expected is not None:
        require(pin['sha256'] == digest(expected), 'Named input SHA does not match independent pin')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON input key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('Nonfinite JSON input refused')
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
    require(type(value) is dict, 'Explicit named JSON object required')
    inputs.append(pin.copy())
    return value


def rows(value, expected):
    require(type(value) is list and len(value) == expected
        and all(type(row) is dict for row in value), 'Exact typed inventory census required')
    return value


def by_path(values):
    result = {}
    for row in values:
        name = relative(row['path'])
        require(name not in result, 'Repeated source inventory entry refused')
        digest(row['sha256']); count(row['bytes'])
        result[name] = row
    return result


def check(group, path, sha, size, disposition='unchanged', **extra):
    require(len(checks) < MAX_CHECKS, 'Logical check budget exceeded')
    got = observed(path)
    passed = got['sha256'] == digest(sha) and got['bytes'] == count(size)
    checks.append({**got, 'group': group, 'expected_sha256': sha, 'expected_bytes': size,
        'disposition': disposition, 'passed': passed, **extra})
    require(passed, 'Explicit public preservation mismatch: ' + str(path))


def final_sources(final, before):
    require(final['checkout'] == str(C), 'Final isolated checkout differs')
    bridge = final.get('bridge_delta_explicitly_authorized')
    require(type(bridge) is bool, 'Explicit bridge authorization marker required')
    existing = MANDATORY_EXISTING | ({BRIDGE} if bridge else set())
    heads = by_path(rows(final['files'], len(existing) + len(NEW)))
    require(set(heads) == existing | NEW and final['existing_deltas'] == len(existing)
        and final['new_files'] == 3, 'Exact independently pinned final source set required')
    for name, head in heads.items():
        require(head['absolute_path'] == str(C / name) and type(head['absent_before']) is bool,
            'Exact source path and Boolean absence required')
        if name in existing:
            old = before[name]
            require(head['absent_before'] is False and head['before_sha256'] == old['sha256']
                and head['before_bytes'] == old['bytes'] and head['baseline'] == old['baseline'],
                'Authorized delta does not join independently captured original bytes')
        else:
            require(head['absent_before'] is True and head['before_sha256'] is None
                and head['before_bytes'] is None and head['baseline'] is None, 'New source cannot invent old bytes')
    return existing, heads


def beginning_sources():
    value = document(N / 'beginning-source-pins.json', BEGINNING_SHA)
    require(value['checkout'] == str(C) and value['prior_manifest']['sha256'] == M_EVIDENCE_SHA,
        'Stage beginning does not join immutable M inventory')
    before = by_path(rows(value['files'], 4))
    require(set(before) == (MANDATORY_EXISTING - {RUNNER}) | {BRIDGE}, 'Exactly four original producer captures required')
    for name, row in before.items():
        row['baseline'] = str(N / 'baseline' / name)
    additional = document(N / 'generation-03-additional-baseline.json', ADDITIONAL_BASELINE_SHA)
    require(additional['checkout'] == str(C) and additional['schema'] == 'native-dispatch-diagnostics-additional-existing-baseline@1'
        and type(additional['generation']) is int and additional['generation'] == 3,
        'Independently pinned generation3 additional producer baseline required')
    extra = by_path(rows(additional['files'], 1))
    require(set(extra) == {RUNNER} and extra[RUNNER]['baseline'] == str(N / 'baseline' / RUNNER),
        'Only the explicitly authorized runner baseline can extend source scope')
    before.update(extra)
    return before


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final-manifest-sha256', required=True)
    args = parser.parse_args()
    output = N / 'preservation-check.json'
    require(not output.exists() and not output.is_symlink(), 'Existing receipt must remain immutable')
    evidence = document(M / 'evidence-manifest.json', M_EVIDENCE_SHA)
    previous = document(M / 'preservation-check.json', M_PRESERVATION_SHA)
    old_manifest = document(M / 'source-manifest.json', M_SOURCE_SHA)
    before = beginning_sources()
    final = document(N / 'source-manifest.json', digest(args.final_manifest_sha256))
    existing, heads = final_sources(final, before)
    def prior(group, path, sha, size):
        path = public_path(path)
        name = path.relative_to(C).as_posix() if path.is_relative_to(C) else None
        if name in existing:
            old, new = before[name], heads[name]
            require(sha == old['sha256'] and size == old['bytes'], 'Prior head does not match exact N-before capture')
            check(group, old['baseline'], sha, size, 'authorized_delta_original_bytes_retained', original_path=str(path))
            check(group, path, new['sha256'], new['bytes'], 'authorized_stage_n_delta', original_sha256=sha, original_bytes=size)
        else:
            check(group, path, sha, size)
    for name, sha in [('evidence-manifest.json', M_EVIDENCE_SHA), ('preservation-check.json', M_PRESERVATION_SHA),
            ('source-manifest.json', M_SOURCE_SHA)]:
        check('prior_m_fixed_pins', M / name, sha, observed(M / name)['bytes'])
    # Evidence inventories use absolute explicitly nominated public paths;
    # source inventories use relative checkout names. Keep these types distinct.
    artifacts = rows(evidence['files'], 261)
    artifact_names = set()
    old_source_names = set(by_path(rows(old_manifest['files'], 14)))
    public_artifact_count, old_source_head_count = 0, 0
    for row in artifacts:
        path = public_path(row['path'])
        require(str(path) not in artifact_names, 'Repeated prior M inventory path')
        artifact_names.add(str(path))
        if path.is_relative_to(M):
            public_artifact_count += 1
            check('prior_m_261_public_artifacts', path, row['sha256'], row['bytes'])
        else:
            require(path.is_relative_to(C) and path.relative_to(C).as_posix() in old_source_names,
                'Foreign path outside exact M artifact/source inventory')
            old_source_head_count += 1
            prior('prior_m_261_public_artifacts', path, row['sha256'], row['bytes'])
    require(public_artifact_count == 247 and old_source_head_count == 14,
        'Exact prior M public-artifact and source-head census differs')
    records = rows(previous['checks'], 806)
    require(previous['all_checks_passed'] is True and type(previous['pin_checks']) is int
        and previous['pin_checks'] == 806 and previous['unique_checked_paths'] == 622
        and len({row['path'] for row in records}) == 622, 'Prior qualified preservation census differs')
    for row in records:
        require(row['passed'] is True and row['sha256'] == row['expected_sha256'] and row['bytes'] == row['expected_bytes'],
            'Previous logical preservation row was not qualified')
        prior('prior_m_806_logical_checks', row['path'], row['sha256'], row['bytes'])
    old = by_path(rows(old_manifest['files'], 14))
    evidence_sources = by_path(rows(evidence['sources'], 14))
    require(set(evidence_sources) == set(old) and all(
        evidence_sources[name]['sha256'] == old[name]['sha256'] and evidence_sources[name]['bytes'] == old[name]['bytes']
        for name in old), 'M evidence/source byte inventories differ')
    for name, row in old.items():
        prior('prior_m_fourteen_sources', C / name, row['sha256'], row['bytes'])
    for name, row in before.items():
        check('all_five_stage_beginning_captures', row['baseline'], row['sha256'], row['bytes'])
        prior('all_five_stage_beginning_heads', C / name, row['sha256'], row['bytes'])
    for name, row in heads.items():
        check('all_final_source_heads', C / name, row['sha256'], row['bytes'])
    check('final_patch', N / 'changes.patch', final['patch_sha256'], final['patch_bytes'])
    for name, recorded in witnesses.items():
        handle, parent, info = opened(Path(name))
        try:
            require(witness(info) == recorded == witness(os.stat(Path(name).name, dir_fd=parent, follow_symlinks=False)),
                'Final named-file witness changed')
        finally:
            os.close(handle); os.close(parent)
    value = {'schema': 'native-dispatch-diagnostics-independent-preservation@1', 'all_checks_passed': True,
        'inputs': inputs, 'checker': observed(Path(__file__).absolute()), 'checks': checks, 'pin_checks': len(checks),
        'unique_checked_paths': len({row['path'] for row in checks}), 'unique_hashed_paths': len(cache),
        'groups': {group: sum(row['group'] == group for row in checks) for group in sorted({row['group'] for row in checks})},
        'prior_m_261_public_artifacts_unchanged': True, 'prior_m_806_logical_checks_rechecked': True,
        'prior_m_622_original_unique_paths': 622, 'all_five_stage_beginning_captures_retained': True,
        'unchanged_bridge_before_pin_verified': BRIDGE not in existing,
        'all_final_source_pins_match': True, 'existing_authorized_deltas': sorted(existing), 'new_current_sources': sorted(NEW),
        'unexpected_deltas': [], 'database_bodies_read': False, 'credentials_or_raw_rollouts_read': False,
        'recursive_discovery': False, 'source_edits': False, 'git_index_mutated': False, 'providers_invoked': 0, 'tests_rerun': False,
        'limitations': ['Only explicitly nominated public byte/SHA pins; unlisted files and repository cleanliness are outside scope.',
            'Only root-pinned authorized source heads replace old current-head observations; exact originals remain captured.',
            'No SDK/model/provider/task/source-equivalence/convergence qualification is inferred from preservation.']}
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'receipt': str(output), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
        'pin_checks': len(checks), 'all_checks_passed': True}))


if __name__ == '__main__':
    main()
