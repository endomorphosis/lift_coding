"""Package the three declared Q source changes without touching the Git index."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

Q = Path(__file__).resolve().parent
C = Q.parent / 'terminal-token-reduction-20261007-01/checkout'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    with (Q / name).open('x') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')


baseline_raw = (Q / 'baseline-manifest.json').read_bytes()
baseline = json.loads(baseline_raw)
final_raw = (Q / 'final-source-pins.json').read_bytes()
final = json.loads(final_raw)
assert baseline['checkout'] == final['checkout'] == str(C)
assert len(final['files']) == len(baseline['files']) == 3
before = {r['path']: r for r in baseline['files']}
assert set(before) == {r['path'] for r in final['files']}
archive_raw = (Q / 'runtime-archive/manifest.json').read_bytes()
archive = json.loads(archive_raw)
members = {r['path']: r for r in archive['files']}
assert len(members) == len(archive['files'])
scratch = Q / 'patch-review-scratch'
scratch.mkdir(exist_ok=False)
subprocess.run(['git', 'init', '-q', str(scratch)], check=True, capture_output=True)
patch, rows = [], []
for pin in final['files']:
    relative = pin['path']
    raw = (C / relative).read_bytes()
    assert len(raw) == pin['bytes'] and sha(raw) == pin['sha256']
    ast.parse(raw)
    old = before[relative]
    original = b''
    if old['exists']:
        original = Path(old['capture']).read_bytes()
        assert len(original) == old['bytes'] and sha(original) == old['sha256']
        target = scratch / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(original)
    captured = Q / 'final-source' / relative
    captured.parent.mkdir(parents=True, exist_ok=True)
    with captured.open('xb') as stream:
        stream.write(raw)
    patch.extend(difflib.unified_diff(original.decode().splitlines(keepends=True),
        raw.decode().splitlines(keepends=True), fromfile='a/' + relative if old['exists'] else '/dev/null',
        tofile='b/' + relative))
    runtime = not Path(relative).name.startswith('test_')
    member = members.get('source/' + relative)
    if runtime:
        assert member and member['bytes'] == len(raw) and member['sha256'] == sha(raw)
    else:
        assert member is None
    rows.append({**pin, 'absolute_path': str(C / relative), 'final_capture': str(captured),
        'absent_before': not old['exists'], 'before_bytes': old.get('bytes'),
        'before_sha256': old.get('sha256'), 'original_capture': old.get('capture'),
        'runtime_archive_member': runtime})
patch_bytes = ''.join(patch).encode()
with (Q / 'changes.patch').open('xb') as stream:
    stream.write(patch_bytes)
for extra in (['--check'], []):
    subprocess.run(['git', 'apply', *extra, str(Q / 'changes.patch')], cwd=scratch,
        check=True, capture_output=True)
for row in rows:
    applied = (scratch / row['path']).read_bytes()
    assert len(applied) == row['bytes'] and sha(applied) == row['sha256']
    ast.parse(applied)
manifest = {'schema': 'terminal-token-pair-source-manifest@1', 'checkout': str(C), 'files': rows,
    'baseline_manifest_sha256': sha(baseline_raw), 'final_source_pins_sha256': sha(final_raw),
    'archive_sha256': archive['archive_sha256'], 'archive_manifest_sha256': sha(archive_raw),
    'patch_sha256': sha(patch_bytes), 'patch_bytes': len(patch_bytes)}
write('source-manifest.json', manifest)
write('patch-qualification.json', {'schema': 'terminal-token-pair-patch-qualification@1', 'qualified': True,
    'original_git_index_mutated': False, 'clean_scratch_git_apply_check_and_apply_passed': True,
    'all_three_applied_sources_match_pins': True, 'all_three_python_asts_parsed': True,
    'runtime_members_match': 2, 'test_members_excluded': 1, 'source_manifest_sha256': sha((Q / 'source-manifest.json').read_bytes()),
    'patch_sha256': sha(patch_bytes), 'original_capture_count': 1, 'new_source_count': 2,
    'archive_bodies_read_or_extracted': False, 'source_or_prior_stage_mutation': False})
print(json.dumps({'qualified': True, 'source_count': 3, 'patch_bytes': len(patch_bytes)}))
