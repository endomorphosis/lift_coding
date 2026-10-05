"""Freeze a compact final Git publication candidate without committing or pushing."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

BASE = Path('/home/barberb/lift_coding')
OUT = BASE / 'maintenance/terminal-ir-publication-20261004-01/root-final-publication-04'
HF = BASE / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
ACC = BASE / 'maintenance/terminal-ir-publication-20261004-01/accelerate-source-model-02'
ACC_CHECKOUT = ACC / 'checkout'
LIMIT = 256 * 1024


def git(*args, cwd=BASE, data=None, private=False):
    env = os.environ.copy()
    if private: env['GIT_INDEX_FILE'] = str(OUT / 'index-preparation-01')
    result = subprocess.run(['git', *args], cwd=cwd, env=env, input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError((args, result.returncode, result.stderr.decode(errors='replace')))
    return result.stdout


def pin(path):
    first = path.lstat()
    if not stat.S_ISREG(first.st_mode): raise ValueError('regular file required')
    data = path.read_bytes(); last = path.stat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(first, key) != getattr(last, key) for key in fields):
        raise ValueError('source changed during capture')
    return data, {'path': str(path.relative_to(BASE)), 'bytes': len(data),
                  'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


start = time.monotonic()
assert git('rev-parse', 'HEAD').decode().strip() == 'fe18069df4203da9bddfb77b1ed41748f4d5fb4d'
assert hashlib.sha256((BASE / '.git/index').read_bytes()).hexdigest() == '80b0426031778d38c8b762a273739e08edbf2ce2b18690efb4f541fa6de120a4'
parent = git('rev-parse', 'origin/main').decode().strip()
assert git('ls-remote', 'origin', 'refs/heads/main').decode().split()[0] == parent
child = git('rev-parse', 'origin/main', cwd=ACC_CHECKOUT).decode().strip()
assert git('ls-remote', 'origin', 'refs/heads/main', cwd=ACC_CHECKOUT).decode().split()[0] == child
git('merge-base', '--is-ancestor', '26812b9267e765ed5792552befea2710bc04b3c6', child, cwd=ACC_CHECKOUT)
source = json.loads((ACC / 'source-snapshot.json').read_bytes())
for row in source['paths'] + source['protected4']:
    data = git('show', child + ':' + row['path'], cwd=ACC_CHECKOUT)
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], row['path']
original = json.loads((ACC / 'prepared-path-correction.json').read_bytes())
assert git('rev-parse', 'HEAD', cwd=BASE / 'external/ipfs_accelerate').decode().strip() == original['original_head']
assert hashlib.sha256(Path(original['original_index']['path']).read_bytes()).hexdigest() == original['original_index']['sha256']
strict = json.loads((HF / 'archive-build-01/closed.json').read_bytes())['source_scope_declarations']['strict_pinned_inputs']
for row in strict:
    data = Path(row['path']).read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], row['path']
assert len(strict) == 348
metrics = BASE / 'qualification/codebase_ir/full-task-reference-metrics-20261005-01'
assert hashlib.sha256((metrics / 'qualified-review.json').read_bytes()).hexdigest() == 'e63564f7396e879ca24f8e022550265dfda97fe2add23238bc98ea17da0e5429'
assert hashlib.sha256((metrics / 'file-seal.json').read_bytes()).hexdigest() == '0fa7ad8b1d232bc402450c89c8f3a02e0f165360413cadf42aa948c54d43a885'
seal = json.loads((metrics / 'file-seal.json').read_bytes())
assert len(seal['files']) == 38
for row in seal['files']:
    data = Path(row['path']).read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']

selected, omitted = set(), []
for root in [metrics, BASE / 'qualification/codebase_ir/full-task-cost-feasibility-source-review-20261005-01']:
    for path in root.rglob('*'):
        if not path.is_file() or path.is_symlink(): continue
        if path.suffix in {'.olean', '.lock', '.pyc'} or path.stat().st_size > LIMIT:
            omitted.append(str(path.relative_to(BASE))); continue
        selected.add(path)
for name in ('publish_successor_evidence_01.py', 'publish_successor_evidence_02.py',
             'prepare_successor_publication_01.py'):
    selected.add(HF / name)
for name in ('successor-source-model-package-01', 'successor-source-model-package-02',
             'successor-publisher-source-review-01', 'successor-publisher-source-review-02',
             'successor-publisher-reader-controls-01', 'bulk-publication-01', 'bulk-publication-outer-01'):
    root = HF / name
    for path in root.glob('*'):
        if path.is_file() and not path.is_symlink() and path.suffix in {'.json', '.py', '.log'} and path.stat().st_size <= LIMIT:
            selected.add(path)
for path in (BASE / 'maintenance/terminal-ir-publication-20261004-01/root-source-model-03').glob('*.json'):
    selected.add(path)
selected.add(OUT / 'capture_final_increment_01.py')

credentials = []
for path in (Path('/home/barberb/.cache/huggingface/token'), Path('/home/barberb/.huggingface/token')):
    if path.is_file():
        value = path.read_bytes().strip()
        if len(value) > 8: credentials.append(value)
for name in ('HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'HUGGINGFACEHUB_API_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN'):
    value = os.environ.get(name)
    if value and len(value) > 8: credentials.append(value.encode())
rows, contents = [], {}
for path in sorted(selected):
    data, row = pin(path)
    if any(value in data for value in credentials): raise ValueError('exact available credential veto')
    text = data.decode('utf-8')
    if path.suffix == '.json': json.loads(text)
    if path.suffix == '.py': ast.parse(text, filename=str(path))
    rows.append(row); contents[row['path']] = data
summary = {'schema': 'terminal-ir-final-root-compact-preparation@1', 'status': 'PREPARED_NO_COMMIT_NO_PUSH',
           'current_parent': parent, 'proposed_accelerator_gitlink': child,
           'original_head_index_unchanged': True, 'original_child_head_index_unchanged': True,
           'original_348_strict_inputs_unchanged': True, 'six_qualified_source_tests_and_protected_four_exact': True,
           'selected_files': rows, 'selected_bytes': sum(row['bytes'] for row in rows),
           'omitted_large_binary_or_lock_files': omitted,
           'awaiting': ['package03 closure and compact file-only review', 'final HF bulk and successor publication closures',
                        'verified final HF revision', 'preparer02 source and immutable output',
                        'parent instruction to publish final ordinary GitHub followup'],
           'new_test_prover_model_native_SQL_calls': 0, 'new_proof_claims': False,
           'full_benchmark_and_asymptotic_convergence': 'OPEN', 'official_score': None,
           'production_defaults': False, 'elapsed_seconds': time.monotonic() - start}
save(OUT / 'selection-preparation-01.json', summary)
contents[str((OUT / 'selection-preparation-01.json').relative_to(BASE))] = (OUT / 'selection-preparation-01.json').read_bytes()
git('read-tree', parent, private=True)
updates, changed = [], []
for name, data in sorted(contents.items()):
    current = subprocess.run(['git', 'show', parent + ':' + name], cwd=BASE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if current.returncode == 0:
        assert current.stdout == data, ('published path differs', name)
        continue
    blob = git('hash-object', '-w', '--stdin', data=data).decode().strip()
    updates.append(('100644 ' + blob + '\t' + name).encode() + b'\0'); changed.append(name)
updates.append(('160000 ' + child + '\texternal/ipfs_accelerate').encode() + b'\0')
git('update-index', '-z', '--index-info', data=b''.join(updates), private=True)
tree = git('write-tree', private=True).decode().strip()
assert sorted(git('diff', '--name-only', parent, tree).decode().splitlines()) == sorted(changed + ['external/ipfs_accelerate'])
for name, data in contents.items(): assert git('show', tree + ':' + name) == data
assert git('rev-parse', 'HEAD').decode().strip() == 'fe18069df4203da9bddfb77b1ed41748f4d5fb4d'
assert hashlib.sha256((BASE / '.git/index').read_bytes()).hexdigest() == '80b0426031778d38c8b762a273739e08edbf2ce2b18690efb4f541fa6de120a4'
save(OUT / 'prepared-tree-01.json', {'schema': 'terminal-ir-final-root-prepared-tree@1',
     'parent': parent, 'tree': tree, 'accelerator_gitlink': child, 'new_paths': len(changed),
     'selected_files': len(contents), 'elapsed_seconds': time.monotonic() - start,
     'commit_created': False, 'pushed': False, 'original_head_index_unchanged': True})
print(json.dumps({'parent': parent, 'tree': tree, 'child': child, 'files': len(contents),
                  'new_paths': len(changed), 'elapsed_seconds': time.monotonic() - start,
                  'commit_created': False, 'pushed': False}))
