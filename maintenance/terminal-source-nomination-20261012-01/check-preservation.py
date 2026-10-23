"""Hash only explicit public preservation inventories; no recursive discovery."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import stat

C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
I = Path('/home/barberb/lift_coding/maintenance/terminal-source-inspector-20261011-01')
J = Path('/home/barberb/lift_coding/maintenance/terminal-source-nomination-20261012-01')
I_MANIFEST_SHA = '73a7b7654630008592744c2057aee21b0f3e735ae8af05bc898bcf04c8206721'
J_PATCH_SHA = 'c3f418be77b392adc5b3a17c78afb6ea95ba6b5d1961aa113783c94580bf54d6'
ALLOWED_J_DELTAS = {
    'ipfs_accelerate_py/agent_supervisor/runtime/code_source_inspection.py',
    'benchmarks/agent_supervisor/container_coding/terminal_indexed_preparation.py',
    'ipfs_accelerate_py/agent_supervisor/runtime/task_context_bundle.py',
}
FORBIDDEN_SUFFIXES = {'.duckdb', '.ducklake', '.db', '.sqlite', '.sqlite3', '.pem', '.key', '.p12', '.pfx', '.jsonl'}
FORBIDDEN_PARTS = {'.codex', 'credentials', 'private', 'hidden', 'oracle', 'rollouts', 'transcripts'}
cache, checks, inputs = {}, [], []


def observed(path, *, fresh=False):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or path.suffix.lower() in FORBIDDEN_SUFFIXES or any(
            part.lower() in FORBIDDEN_PARTS for part in path.parts):
        raise ValueError('Nonpublic or noncanonical explicit preservation path refused')
    name = str(path)
    if not fresh and name in cache:
        return cache[name]
    handle = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(handle)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('Preservation pin requires a regular public file')
        digest, size = hashlib.sha256(), 0
        with os.fdopen(handle, 'rb', closefd=False) as stream:
            while block := stream.read(1_048_576):
                digest.update(block)
                size += len(block)
        after, named = os.fstat(handle), path.stat(follow_symlinks=False)
        witness = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        if witness(before) != witness(after) or witness(after) != witness(named):
            raise ValueError('Public preservation file changed during hash')
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
                raise ValueError('Duplicate inventory JSON key')
            result[key] = value
        return result
    result = json.loads(Path(path).read_bytes(), object_pairs_hook=unique)
    inputs.append(pin.copy())
    return result


def relative(name):
    path = PurePosixPath(name)
    if not path.parts or path.is_absolute() or str(path) != name or '..' in path.parts:
        raise ValueError('Canonical inventory-relative path required')
    return name


def check(group, path, sha256, size, *, disposition='unchanged', **extra):
    current = observed(path)
    passed = current['sha256'] == sha256 and current['bytes'] == size
    row = {**current, 'group': group, 'expected_sha256': sha256, 'expected_bytes': size,
           'disposition': disposition, 'passed': passed, **extra}
    checks.append(row)
    if not passed:
        raise ValueError('Explicit preservation pin mismatch: ' + str(path))
    return row


manifest = document(I / 'evidence-manifest.json')
check('prior_stage_manifest_fixed_pin', I / 'evidence-manifest.json', I_MANIFEST_SHA,
      observed(I / 'evidence-manifest.json')['bytes'])
prior = document(I / 'preservation-check.json')
beginning_i = document(I / 'beginning-source-pins.json')
source_i = document(I / 'source-manifest.json')
beginning_j = document(J / 'beginning-source-pins.json')
source_j = document(J / 'source-manifest.json')
assert len(manifest['files']) == 64 and len(prior['prior_unchanged_checks']) == 209
assert len(beginning_i['files']) == 6 and len(source_i['files']) == 4
assert len(beginning_j['files']) == 7 and len(source_j['files']) == 8
current_j = {row['path']: row for row in source_j['files']}
assert {name for name, row in current_j.items() if not row['absent_before']} == ALLOWED_J_DELTAS

for row in manifest['files']:
    check('prior_stage_64_public_artifacts', I / relative(row['path']), row['sha256'], row['bytes'])
for row in prior['prior_unchanged_checks']:
    check('older_209_explicit_pins', row['path'], row['sha256'], row['bytes'], historical_group=row['group'])
old_i_after = {row['path']: row for row in prior['beginning_source_checks']}
for row in beginning_i['files']:
    name = relative(row['path'])
    check('prior_stage_six_before_captures', I / 'baseline' / name, row['sha256'], row['bytes'],
          disposition='captured_before_bytes_retained')
    after = old_i_after[str(C / name)]
    check('prior_stage_six_current_sources', C / name, after.get('after_sha256', after.get('sha256')),
          after.get('after_bytes', after.get('bytes')),
          disposition='expected_prior_stage_reader_delta_still_current' if after.get('intentional_reader_change', False) else 'unchanged',
          original_before_sha256=row['sha256'], original_before_bytes=row['bytes'])

for row in source_i['files']:
    name = relative(row['path'])
    if name in ALLOWED_J_DELTAS:
        final = current_j[name]
        assert final['before_sha256'] == row['sha256'] and final['before_bytes'] == row['bytes']
        check('prior_stage_four_current_sources', C / name, final['sha256'], final['bytes'],
              disposition='authorized_stage_j_delta', original_before_sha256=row['sha256'],
              original_before_bytes=row['bytes'], captured_before_path=str(J / 'baseline' / name))
    else:
        check('prior_stage_four_current_sources', C / name, row['sha256'], row['bytes'])

for row in beginning_j['files']:
    name = relative(row['path'])
    check('current_stage_seven_before_captures', J / 'baseline' / name, row['sha256'], row['bytes'],
          disposition='captured_before_bytes_retained')
    if name in ALLOWED_J_DELTAS:
        final = current_j[name]
        assert final['before_sha256'] == row['sha256'] and final['before_bytes'] == row['bytes']
        check('current_stage_seven_current_sources', C / name, final['sha256'], final['bytes'],
              disposition='authorized_stage_j_delta', original_before_sha256=row['sha256'], original_before_bytes=row['bytes'])
    else:
        check('current_stage_seven_current_sources', C / name, row['sha256'], row['bytes'])

for row in source_j['files']:
    name = relative(row['path'])
    assert row['absolute_path'] == str(C / name)
    check('current_stage_eight_final_sources', C / name, row['sha256'], row['bytes'],
          disposition='new_stage_j_file' if row['absent_before'] else 'authorized_stage_j_delta_final_pin')
assert source_j['patch_sha256'] == J_PATCH_SHA and source_j['patch_bytes'] == 149071
check('current_stage_patch_fixed_pin', J / 'changes.patch', J_PATCH_SHA, 149071,
      disposition='final_patch_pin')
for pin in inputs:
    latest = observed(pin['path'], fresh=True)
    check('selected_inventory_stability', pin['path'], pin['sha256'], pin['bytes'],
          disposition='inventory_unchanged_during_check')

groups = {}
for row in checks:
    groups.setdefault(row['group'], {'checks': 0, 'passed': 0, 'unique_paths': set()})
    group = groups[row['group']]
    group['checks'] += 1
    group['passed'] += row['passed']
    group['unique_paths'].add(row['path'])
for group in groups.values():
    group['unique_paths'] = len(group['unique_paths'])

receipt = {'schema': 'intent-source-nomination-stage-preservation-check@1',
    'enumeration': 'Only the explicitly selected I/J public manifests and inventories. No recursive discovery; database bodies, credentials, private fixtures, raw rollouts and transcripts refused.',
    'inputs': inputs, 'groups': groups, 'checks': checks,
    'pin_checks': len(checks), 'unique_checked_paths': len({row['path'] for row in checks}),
    'unique_hashed_paths': len(cache), 'all_checks_passed': all(row['passed'] for row in checks),
    'older_209_pins_unchanged': True, 'prior_stage_64_public_artifacts_unchanged': True,
    'prior_stage_fixed_manifest_unchanged': True,
    'prior_stage_beginning_five_unchanged_one_expected_reader_delta_still_current': True,
    'prior_stage_six_before_captures_retained': True,
    'prior_stage_four_sources_three_unchanged_one_authorized_current_delta': True,
    'old_c504_reader_bytes_retained_in_current_stage_baseline': True,
    'current_stage_seven_before_captures_retained': True,
    'current_stage_beginning_four_unchanged_three_authorized_deltas': True,
    'current_stage_eight_final_source_pins_match': True,
    'authorized_current_delta_unique_paths': sorted(str(C / name) for name in ALLOWED_J_DELTAS),
    'unexpected_deltas': [], 'provider_calls': 0, 'prover_invocations': 0,
    'source_edits': False, 'tests_rerun': False, 'database_bodies_read': False,
    'credentials_or_raw_rollouts_read': False,
    'limitations': ['This verifies exact SHA256/byte pins, not semantic equivalence, full repository cleanliness, or unlisted artifact preservation.',
                    'Authorized source deltas are distinguished from unchanged files; retained baseline bytes remain independently checked.',
                    'No new admission, model-token, source-authentication or completion authority is established.']}
output = J / 'preservation-check.json'
if output.exists():
    raise ValueError('Preservation receipt already exists; refusing to replace history')
output.write_text(json.dumps(receipt, sort_keys=True, separators=(',', ':')) + '\n')
raw = output.read_bytes()
print(json.dumps({'path': str(output), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
    'pin_checks': len(checks), 'unique_checked_paths': receipt['unique_checked_paths'],
    'all_checks_passed': receipt['all_checks_passed'], 'groups': groups}, sort_keys=True))
