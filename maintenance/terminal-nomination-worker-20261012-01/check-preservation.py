"""Preserve explicitly nominated public evidence, allowing only declared K deltas.

Run only after the root declares the final K source manifest frozen. This script
does not discover files recursively or open database, credential or rollout data.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import stat

C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
J = Path('/home/barberb/lift_coding/maintenance/terminal-source-nomination-20261012-01')
K = Path('/home/barberb/lift_coding/maintenance/terminal-nomination-worker-20261012-01')
J_MANIFEST_SHA = '10cadfc8c88098c0c39473853993622cc5f90a330eae5bb38a994f93abc20249'
J_PRESERVATION_SHA = 'da99a728142e3be00a1018c13fe941b66075677ee22ab9cf9234d31db31993a0'
EXPECTED_EXISTING_DELTAS = {
    'benchmarks/agent_supervisor/container_coding/full_supervisor_benchmark.py',
    'benchmarks/agent_supervisor/container_coding/full_supervisor_harbor_agent.py',
    'benchmarks/agent_supervisor/container_coding/terminal_container_supervisor.py',
    'ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py',
    'ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py',
    'ipfs_accelerate_py/agent_supervisor/runtime/intent_source_inspection.py',
}
DENY_SUFFIXES = {'.duckdb', '.ducklake', '.db', '.sqlite', '.sqlite3', '.pem', '.key', '.p12', '.pfx', '.jsonl'}
DENY_PARTS = {'.codex', 'credentials', 'private', 'hidden', 'oracle', 'rollouts', 'transcripts'}
cache, checks, input_pins = {}, [], []


def observed(path, *, fresh=False):
    path = Path(path)
    if (not path.is_absolute() or '..' in path.parts or path.suffix.lower() in DENY_SUFFIXES
            or any(part.lower() in DENY_PARTS for part in path.parts)):
        raise ValueError('Nonpublic explicit preservation path refused')
    name = str(path)
    if not fresh and name in cache:
        return cache[name]
    handle = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(handle)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('Preservation pins require regular public files')
        size, digest = 0, hashlib.sha256()
        with os.fdopen(handle, 'rb', closefd=False) as stream:
            while block := stream.read(1_048_576):
                size += len(block)
                digest.update(block)
        after, named = os.fstat(handle), path.stat(follow_symlinks=False)
        witness = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        if witness(before) != witness(after) or witness(after) != witness(named):
            raise ValueError('Public preservation input changed while hashing')
    finally:
        os.close(handle)
    result = {'path': name, 'bytes': size, 'sha256': digest.hexdigest()}
    cache[name] = result
    return result


def document(path):
    pin = observed(path)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate manifest JSON key')
            result[key] = value
        return result
    value = json.loads(Path(path).read_bytes(), object_pairs_hook=unique)
    input_pins.append(pin.copy())
    return value


def relative(name):
    path = PurePosixPath(name)
    if not path.parts or path.is_absolute() or str(path) != name or '..' in path.parts:
        raise ValueError('Canonical manifest-relative path required')
    return name


def check(group, path, sha256, size, *, disposition='unchanged', **extra):
    current = observed(path)
    passed = current['sha256'] == sha256 and current['bytes'] == size
    checks.append({**current, 'group': group, 'expected_sha256': sha256, 'expected_bytes': size,
                   'disposition': disposition, 'passed': passed, **extra})
    if not passed:
        raise ValueError('Explicit preservation pin mismatch: ' + str(path))


def main():
    # Root must send the explicit freeze notification before this entry is run.
    prior_manifest = document(J / 'evidence-manifest.json')
    assert observed(J / 'evidence-manifest.json')['sha256'] == J_MANIFEST_SHA
    previous = document(J / 'preservation-check.json')
    assert observed(J / 'preservation-check.json')['sha256'] == J_PRESERVATION_SHA
    prior_sources = document(J / 'source-manifest.json')
    before = document(K / 'beginning-source-pins.json')
    final = document(K / 'source-manifest.json')
    assert len(prior_manifest['files']) == 79
    assert previous['all_checks_passed'] is True and previous['pin_checks'] == 319
    assert previous['unique_checked_paths'] == 300 and len(previous['checks']) == 319
    assert len({row['path'] for row in previous['checks']}) == 300
    assert len(prior_sources['files']) == 8 and len(before['files']) == 13
    assert len(final['files']) == 11
    baseline = {relative(row['path']): row for row in before['files']}
    source_pins = {relative(row['path']): row for row in final['files']}
    existing = {name: row for name, row in source_pins.items() if not row['absent_before']}
    new = {name: row for name, row in source_pins.items() if row['absent_before']}
    assert set(existing) == EXPECTED_EXISTING_DELTAS and len(new) == 5
    for name, row in source_pins.items():
        assert row['absolute_path'] == str(C / name)
        if name in existing:
            assert name in baseline
            assert row['before_sha256'] == baseline[name]['sha256']
            assert row['before_bytes'] == baseline[name]['bytes']

    def prior_check(group, path, sha256, size, **extra):
        path = Path(path)
        relative_name = path.relative_to(C).as_posix() if path.is_relative_to(C) else None
        if relative_name in existing:
            base, head = baseline[relative_name], existing[relative_name]
            if sha256 != base['sha256'] or size != base['bytes']:
                raise ValueError('Older head pin does not match the exact K baseline capture')
            check(group, K / 'baseline' / relative_name, sha256, size,
                  disposition='authorized_head_delta_original_bytes_retained', original_head_path=str(path), **extra)
            check(group, path, head['sha256'], head['bytes'], disposition='authorized_stage_k_delta',
                  original_expected_sha256=sha256, original_expected_bytes=size, **extra)
        else:
            check(group, path, sha256, size, **extra)

    check('prior_j_manifest_fixed_pin', J / 'evidence-manifest.json', J_MANIFEST_SHA,
          observed(J / 'evidence-manifest.json')['bytes'])
    check('prior_j_preservation_fixed_pin', J / 'preservation-check.json', J_PRESERVATION_SHA,
          observed(J / 'preservation-check.json')['bytes'])
    for row in prior_manifest['files']:
        check('prior_j_79_public_artifacts', J / relative(row['path']), row['sha256'], row['bytes'])
    for row in previous['checks']:
        assert row['passed'] is True
        prior_check('prior_319_logical_pin_rechecks', row['path'], row['sha256'], row['bytes'],
                    historical_group=row['group'], historical_disposition=row['disposition'])
    for row in prior_sources['files']:
        prior_check('prior_j_eight_current_sources', C / relative(row['path']), row['sha256'], row['bytes'])
    for name, row in baseline.items():
        check('current_k_13_baseline_captures', K / 'baseline' / name, row['sha256'], row['bytes'],
              disposition='captured_before_bytes_retained')
        prior_check('current_k_13_current_sources', C / name, row['sha256'], row['bytes'])
    for name, row in source_pins.items():
        check('current_k_11_final_source_pins', C / name, row['sha256'], row['bytes'],
              disposition='new_stage_k_file' if row['absent_before'] else 'authorized_stage_k_delta_final_pin')
    check('current_k_final_patch', final['patch_path'], final['patch_sha256'], final['patch_bytes'],
          disposition='final_patch_pin')
    for pin in input_pins:
        observed(pin['path'], fresh=True)
        check('selected_manifest_stability', pin['path'], pin['sha256'], pin['bytes'],
              disposition='inventory_unchanged_during_check')
    groups = {}
    for row in checks:
        group = groups.setdefault(row['group'], {'checks': 0, 'passed': 0, 'unique_paths': set()})
        group['checks'] += 1
        group['passed'] += row['passed']
        group['unique_paths'].add(row['path'])
    for group in groups.values():
        group['unique_paths'] = len(group['unique_paths'])
    prior_rows = [row for row in checks if row['group'] == 'prior_319_logical_pin_rechecks']
    authorized_heads = sorted({row['path'] for row in prior_rows if row['disposition'] == 'authorized_stage_k_delta'})
    receipt = {'schema': 'reviewed-source-nomination-worker-preservation-check@1',
        'enumeration': 'Only explicit J/K public inventory pins; no recursive discovery, database-body reads, credentials, raw rollouts or private fixture scans.',
        'inputs': input_pins, 'checks': checks, 'groups': groups,
        'pin_checks': len(checks), 'unique_checked_paths': len({row['path'] for row in checks}),
        'unique_hashed_paths': len(cache), 'all_checks_passed': all(row['passed'] for row in checks),
        'prior_j_79_public_artifacts_unchanged': True,
        'prior_j_fixed_manifest_and_preservation_receipts_unchanged': True,
        'prior_319_logical_pins_rechecked': True, 'prior_319_original_unique_paths': 300,
        'prior_checks_unchanged_count': sum(row['disposition'] == 'unchanged' for row in prior_rows),
        'prior_authorized_head_delta_checks': sum(row['disposition'] == 'authorized_stage_k_delta' for row in prior_rows),
        'prior_authorized_head_delta_unique_paths': authorized_heads,
        'prior_expected_head_bytes_retained_for_every_authorized_delta': True,
        'prior_j_eight_sources_seven_unchanged_one_authorized_k_delta': True,
        'all_13_current_baseline_captures_retained': True,
        'current_beginning_seven_sources_unchanged_six_authorized_deltas': True,
        'all_11_final_source_pins_match': True,
        'authorized_current_delta_unique_paths': sorted(str(C / name) for name in existing),
        'unexpected_deltas': [], 'provider_calls': 0, 'prover_invocations': 0,
        'database_bodies_read': False, 'credentials_or_raw_rollouts_read': False,
        'source_edits': False, 'tests_rerun': False,
        'limitations': ['Exact public bytes/SHA preservation only; unlisted files and complete repository cleanliness are outside scope.',
            'Current authorized K heads are separately joined to their exact preserved baseline bytes, not labelled unchanged.',
            'No behavioral, task-completion, source-authentication or provider-token claim is established.']}
    output = K / 'preservation-check.json'
    if output.exists():
        raise ValueError('Refusing to replace a retained preservation receipt')
    output.write_text(json.dumps(receipt, sort_keys=True, separators=(',', ':')) + '\n')
    raw = output.read_bytes()
    print(json.dumps({'path': str(output), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
        'pin_checks': receipt['pin_checks'], 'unique_checked_paths': receipt['unique_checked_paths'],
        'all_checks_passed': receipt['all_checks_passed'], 'groups': groups,
        'prior_authorized_head_delta_checks': receipt['prior_authorized_head_delta_checks'],
        'prior_authorized_head_delta_unique_paths': authorized_heads}, sort_keys=True))


if __name__ == '__main__':
    main()
