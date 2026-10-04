"""Publish exact compact successor sources and receipts using a private index."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

BASE = Path('/home/barberb/lift_coding')
OUT = BASE / 'maintenance/terminal-ir-publication-20261004-01/root-source-model-03'
HF = BASE / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
ACC = BASE / 'maintenance/terminal-ir-publication-20261004-01/accelerate-source-model-02'
ACC_COMMIT = '26812b9267e765ed5792552befea2710bc04b3c6'
BRANCH = 'refs/heads/codex/terminal-ir-source-model-20261004-03'
LIMIT = 256 * 1024


def git(*args, data=None, private=False):
    env = os.environ.copy()
    if private:
        env['GIT_INDEX_FILE'] = str(OUT / 'index')
    result = subprocess.run(['git', *args], cwd=BASE, env=env,
                            input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError((args, result.returncode, result.stderr.decode(errors='replace')))
    return result.stdout


def pin(path):
    first = path.lstat()
    if not stat.S_ISREG(first.st_mode):
        raise ValueError('only regular files may be selected')
    data = path.read_bytes()
    last = path.stat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(first, f) != getattr(last, f) for f in fields):
        raise ValueError('source changed while reading')
    return data, {'path': str(path.relative_to(BASE)), 'bytes': len(data),
                  'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


started = time.monotonic()
original_head = git('rev-parse', 'HEAD').decode().strip()
index_path = Path(git('rev-parse', '--git-path', 'index').decode().strip())
if not index_path.is_absolute(): index_path = BASE / index_path
original_index = hashlib.sha256(index_path.read_bytes()).hexdigest()
assert original_head == 'fe18069df4203da9bddfb77b1ed41748f4d5fb4d'
assert original_index == '80b0426031778d38c8b762a273739e08edbf2ce2b18690efb4f541fa6de120a4'
parent = git('rev-parse', 'origin/main').decode().strip()
assert git('ls-remote', 'origin', 'refs/heads/main').decode().split()[0] == parent
archive = json.loads((HF / 'archive-build-01/closed.json').read_bytes())
strict = archive['source_scope_declarations']['strict_pinned_inputs']
for row in strict:
    data = Path(row['path']).read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], row['path']
assert len(strict) == 348

selected = set()
excluded = []
roots = [p for p in (BASE / 'qualification/codebase_ir').glob('*20261004*')
         if p.name.startswith(('selector-semantics-', 'full-task-source-', 'global-shape-reference-', 'source-model-next-stage-'))]
for root in roots:
    for path in root.rglob('*'):
        if not path.is_file() or path.is_symlink(): continue
        relative = path.relative_to(root)
        if (path.stat().st_size > LIMIT or path.suffix in {'.lock', '.olean', '.duckdb', '.ducklake', '.parquet', '.pyc'}
                or any(x in relative.parts for x in {'__pycache__', 'exports', 'data'})
                or ('metadata' in relative.parts and path.name not in {'manifest.json', 'history.json'})):
            excluded.append(str(path.relative_to(BASE))); continue
        path.read_bytes().decode('utf-8')
        selected.add(path)

# Final helpers are closed and frozen; archive payloads and private databases stay outside Git.
for name in ('build_evidence_archive.py', 'build_evidence_archive_02.py', 'run_local_archive_build.py',
             'classify_and_prepare_public_archive_07.py', 'run_decoder_controls_05.py',
             'publish_bootstrap_01.py', 'publish_qualified_archive_02.py',
             'run_frozen_publication_phase.py', 'prepare_candidate_inventory.py',
             'review_closed_public_archive_01.py'):
    selected.add(HF / name)
assert hashlib.sha256((HF / 'review_closed_public_archive_01.py').read_bytes()).hexdigest() == '106c82a7c24cd134f2c2f43e814741d310d27b0f9ea47840bcb7916762ac71e6'
# Only compact declarative top-level metadata, never candidate bodies.
for path in HF.glob('*.json'):
    if path.stat().st_size <= LIMIT: selected.add(path)
for directory in ('archive-build-01', 'archive-build-outer-01', 'archive-classification-01',
                  'archive-classification-outer-01', 'bootstrap-01',
                  'independent-source-review-01', 'independent-source-review-02',
                  'fixture-provenance-01', 'fixture-provenance-02',
                  'oauthlib-public-fixture-provenance-01', 'oauthlib-public-fixture-provenance-02',
                  'root-physical-review-01', 'root-physical-review-controls-01',
                  'root-physical-review-controls-02', 'root-physical-review-negative-01',
                  'scoped-publication-review-01', 'candidate-inventory-01',
                  'decoder-controls-01', 'decoder-controls-02', 'decoder-controls-03',
                  'decoder-controls-04', 'decoder-controls-05'):
    root = HF / directory
    for path in root.rglob('*.json'):
        if (path.is_symlink() or path.stat().st_size > LIMIT
                or path.name in {'candidate-files.json'}
                or any(x in path.relative_to(root).parts for x in {'input', 'inputs', 'captured-source', 'payloads', 'shards', 'chunks'})):
            continue
        selected.add(path)
for path in ACC.glob('*.json'): selected.add(path)
selected.add(OUT / 'prepare_root_increment_01.py')

# The actual available HF token is checked privately and is never printed or stored in receipts.
credential_values = []
for path in (Path('/home/barberb/.cache/huggingface/token'), Path('/home/barberb/.huggingface/token')):
    if path.is_file():
        value = path.read_bytes().strip()
        if len(value) > 8: credential_values.append(value)
for name in ('HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'HUGGINGFACEHUB_API_TOKEN', 'GITHUB_TOKEN', 'GH_TOKEN'):
    value = os.environ.get(name)
    if value and len(value) > 8: credential_values.append(value.encode())
rows, contents = [], {}
for path in sorted(selected):
    data, record = pin(path)
    if any(value in data for value in credential_values): raise ValueError('active exact credential veto')
    text = data.decode('utf-8')
    if path.suffix == '.json': json.loads(text)
    if path.suffix == '.py': ast.parse(text, filename=str(path))
    rows.append(record); contents[record['path']] = data

summary = {'schema': 'terminal-ir-successor-root-compact-selection@1', 'parent': parent,
           'accelerator_commit': ACC_COMMIT, 'original_head': original_head,
           'original_index_sha256': original_index, 'original_348_strict_inputs_unchanged': True,
           'selected_files': rows, 'selected_bytes': sum(x['bytes'] for x in rows),
           'large_repeated_payloads_metadata_binaries_complete_olean_archive_shards': 'Hugging Face evidence package only',
           'omitted_qualification_files': sorted(excluded),
           'scope': 'Compact exact source, Lean text, immutable qualification and publication receipts',
           'new_test_prover_model_native_SQL_calls': 0, 'production_defaults': False,
           'official_score': None, 'all_32_macro_acceptance': 'OPEN',
           'source_to_model_universal_full_task_and_asymptotic_AE_convergence': 'OPEN',
           'HF_status': 'bootstrap published; closed scoped archive prepared; bulk upload pending'}
save(OUT / 'selection.json', summary)
contents[str((OUT / 'selection.json').relative_to(BASE))] = (OUT / 'selection.json').read_bytes()
git('read-tree', parent, private=True)
updates = []
changed = []
for path, data in sorted(contents.items()):
    existing = subprocess.run(['git', 'show', parent + ':' + path], cwd=BASE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if existing.returncode == 0:
        assert existing.stdout == data, ('existing published path changed', path)
        continue
    blob = git('hash-object', '-w', '--stdin', data=data).decode().strip()
    updates.append(('100644 ' + blob + '\t' + path).encode() + b'\0')
    changed.append(path)
updates.append(('160000 ' + ACC_COMMIT + '\texternal/ipfs_accelerate').encode() + b'\0')
git('update-index', '-z', '--index-info', data=b''.join(updates), private=True)
tree = git('write-tree', private=True).decode().strip()
actual = git('diff', '--name-only', parent, tree).decode().splitlines()
assert sorted(actual) == sorted(changed + ['external/ipfs_accelerate'])
commit = git('commit-tree', tree, '-p', parent,
             data=b'Retain qualified selector and ranker evidence with scoped archive publication tools\n').decode().strip()
git('update-ref', BRANCH, commit)
for path, data in contents.items(): assert git('show', commit + ':' + path) == data
assert git('rev-parse', 'HEAD').decode().strip() == original_head
assert hashlib.sha256(index_path.read_bytes()).hexdigest() == original_index
save(OUT / 'prepared.json', {'schema': 'terminal-ir-successor-root-prepush@1', 'parent': parent,
     'tree': tree, 'commit': commit, 'private_branch': BRANCH, 'ordinary_nonforce_push': True,
     'selected_count': len(contents), 'new_paths': len(changed), 'changed_paths': actual,
     'duration_seconds': time.monotonic() - started, 'original_head_index_unchanged': True,
     'source_pin_readback_exact': True, 'tests_provers_rerun': False})
print(json.dumps({'commit': commit, 'parent': parent, 'count': len(contents),
                  'bytes': summary['selected_bytes'], 'new_paths': len(changed),
                  'duration_seconds': time.monotonic() - started}))
