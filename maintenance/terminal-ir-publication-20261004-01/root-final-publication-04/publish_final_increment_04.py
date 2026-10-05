"""Publish the verified compact final Git and Hugging Face release pointer."""
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
    if private: env['GIT_INDEX_FILE'] = str(OUT / 'index-final-04')
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
             'prepare_successor_publication_01.py', 'prepare_successor_publication_02.py',
             'prepare_successor_publication_03.py', 'prepare_successor_publication_04.py'):
    selected.add(HF / name)
for name in ('successor-source-model-package-01', 'successor-source-model-package-02', 'successor-source-model-package-03',
             'successor-publisher-source-review-01', 'successor-publisher-source-review-02',
             'successor-publisher-reader-controls-01', 'bulk-publication-01', 'bulk-publication-outer-01',
             'bulk-publication-02', 'bulk-publication-outer-02',
             'successor-preparer-source-review-03', 'successor-preparer-source-review-04',
             'successor-tooling-file-review-01', 'successor-final-plan-review-01',
             'successor-publication-01', 'successor-publication-outer-01'):
    root = HF / name
    for path in root.glob('*'):
        if path.is_file() and not path.is_symlink() and path.suffix in {'.json', '.py'} and path.stat().st_size <= LIMIT:
            selected.add(path)
for path in (BASE / 'maintenance/terminal-ir-publication-20261004-01/root-source-model-03').glob('*.json'):
    selected.add(path)
selected.add(OUT / 'capture_final_increment_01.py')
selected.add(OUT / 'capture_final_increment_02.py')
selected.add(OUT / 'capture_final_increment_03.py')
selected.add(OUT / 'publish_final_increment_04.py')
for path in OUT.glob('*.patch'): selected.add(path)
for name in ('selection-preparation-01.json', 'prepared-tree-01.json',
             'selection-preparation-02.json', 'prepared-tree-02.json',
             'selection-preparation-03.json', 'prepared-tree-03.json'):
    selected.add(OUT / name)
for name in ('successor-publication-preparation-01', 'successor-publication-preparation-02',
             'successor-publication-preparation-03', 'successor-publication-preparation-04'):
    root = HF / name
    for path in root.glob('*'):
        if path.is_file() and path.suffix in {'.md', '.json'} and path.stat().st_size <= LIMIT: selected.add(path)
selected.add(HF / 'successor-source-model-package-03/package/manifest.json')
bulk = json.loads((HF / 'bulk-publication-02/closed.json').read_bytes())
assert bulk['status'] == 'PUBLISHED_AND_SELECTED_REMOTE_IDENTITIES_VERIFIED'
assert bulk['all_selected_files_verified'] and bulk['file_count'] == 76
assert bulk['selected_uploaded_bytes'] == 6836582999
assert bulk['final_commit'] == 'e008f1ed73c642eb8ce33cec0bec52eac305ae28'
assert len(bulk['commits']) == 4 and all(row['verification_status'] == 'passed' for row in bulk['commits'])
plan = HF / 'successor-publication-preparation-04/file-plan-with-tooling.json'
assert hashlib.sha256(plan.read_bytes()).hexdigest() == '51189f505e55a7cdb5569631a8bce9a6c1b8df21910faec9a5237cc9a1b76372'
for row in json.loads((HF / 'successor-tooling-file-review-01/manifest.json').read_bytes())['files']:
    path = Path(row['path'])
    data = path.read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    assert path.stat().st_size <= LIMIT and path.suffix in {'.json', '.py'}
    selected.add(path)

# The closed actual publisher and independent readback bind the final dataset revision.
addon_path = HF / 'successor-publication-01/closed.json'
assert hashlib.sha256(addon_path.read_bytes()).hexdigest() == '9246ef1380cdcb3c683072ed5a1b456d97b3bb8c187e05fa78ded710f5921f08'
addon = json.loads(addon_path.read_bytes())
assert addon['status'] == 'PUBLISHED_AND_VERIFIED' and addon['remote_readback_verified']
assert addon['commit'] == '580717c7b45e7162ce6f1b5e63309fc76b962b44'
assert addon['parent'] == bulk['final_commit']
assert addon['files'] == 65 and addon['selected_bytes'] == 13600880
assert addon['prior_immutable_remote_files_preserved'] == 80
assert addon['plan']['sha256'] == '51189f505e55a7cdb5569631a8bce9a6c1b8df21910faec9a5237cc9a1b76372'
outer_path = HF / 'successor-publication-outer-01/closed.json'
assert hashlib.sha256(outer_path.read_bytes()).hexdigest() == '9e345a7f7b8c4778b7a03ba33bce842093e7ec812ccb697ccbf13a918a9d47a7'
outer = json.loads(outer_path.read_bytes())
assert outer['returncode'] == 0 and outer['input_pins_unchanged'] and outer['cleanup_errors'] == []
review_path = HF / 'successor-final-plan-review-01/review.json'
assert hashlib.sha256(review_path.read_bytes()).hexdigest() == 'e678c77b28183ef5a1da7b650d392ed5e10a02bf9780b5fdd79f6a3ff461bc34'
assert json.loads(review_path.read_bytes())['status'] == 'PASS'
verified = json.loads((HF / 'successor-publication-01/verified-files.json').read_bytes())
assert verified['commit'] == addon['commit'] and len(verified['files']) == 65
from huggingface_hub import HfApi
assert HfApi().repo_info('Publicus/codebase-ir-proof-index', repo_type='dataset', revision='main').sha == addon['commit']
root_children = {}
for line in git('ls-tree', parent).decode().splitlines():
    fields = line.split()
    if len(fields) >= 4 and fields[0] == '160000': root_children[fields[3]] = fields[2]
for name in ('external/ipfs_accelerate', 'external/ipfs_datasets', 'external/ipfs_kit'):
    root_children[name] = git('ls-tree', parent, name).decode().split()[2]
git('merge-base', '--is-ancestor', 'a3e7ea91cfbbf2e68d68b1362e0a22690cb09d97',
    root_children['external/ipfs_datasets'], cwd=BASE / 'external/ipfs_datasets')
root_children['external/ipfs_accelerate'] = child
pointer = {
    'schema': 'terminal-ir-final-verified-publication-pointer@1',
    'repo_id': 'Publicus/codebase-ir-proof-index', 'repo_type': 'dataset',
    'revision': addon['commit'],
    'url': 'https://huggingface.co/datasets/Publicus/codebase-ir-proof-index/commit/' + addon['commit'],
    'release_prefix': 'releases/20261004-terminal-codebase-ir-evidence-v1',
    'status': 'PUBLISHED_AND_VERIFIED_FOR_DECLARED_SCOPES',
    'bulk': {'revision': bulk['final_commit'], 'files': 76, 'bytes': 6836582999,
             'all_selected_files_verified': True, 'all_original_raw_bytes_published': False},
    'source_model_addition': {'revision': addon['commit'], 'files': 65, 'bytes': 13600880,
                             'prior_immutable_files_preserved': 80},
    'GitHub_root_parent': parent, 'canonical_child_gitlinks': root_children,
    'original_348_strict_inputs_unchanged': True, 'original_root_and_accelerator_HEAD_indexes_unchanged': True,
    'six_qualified_source_tests_and_protected_four_exact': True,
    'qualified_selector_and_ranker_tests': 30, 'qualified_reference_tests': 18,
    'captured_AST_selector_differential_cases': 1705,
    'selected_selector_ranker_native_Lean_checks': 4,
    'metadata': {'rows': 4216, 'families': 26, 'lake_packets': 82, 'original_exact_payloads_preserved': 4209},
    'authored_performance_fixture': {'requests': 16, 'strict_thresholds_passed': 8,
                                   'structural_clauses_passed': 4, 'input_byte_frame_passed': True,
                                   'native_Lean_calls': 2, 'finite_metric_theorems': 8,
                                   'false_control_genuinely_rejected': True},
    'qualification_limits': {
        'whole_Python_source_equivalence': 'OPEN', 'full_benchmark_task_satisfaction': 'OPEN',
        'asymptotic_optimizer_convergence': 'OPEN', 'global_autoencoder_convergence': 'OPEN',
        'all_32_governing_exits': 'OPEN', 'official_benchmark_score': None,
        'production_defaults': False, 'proof_planning_execution_completion_authority': False,
        'universal_secret_absence_claimed': False,
        'large_remote_content_verification': 'Committed LFS SHA256 and size; small files downloaded for exact SHA256',
        'scope_exclusions': 'Recorded in the physically reviewed archive manifest; no claim all raw source bytes published'},
    'selected_qualification_training_calls': 0, 'selected_publication_native_jobs': 0,
    'bulk_closure_sha256': hashlib.sha256((HF / 'bulk-publication-02/closed.json').read_bytes()).hexdigest(),
    'addon_closure_sha256': hashlib.sha256(addon_path.read_bytes()).hexdigest(),
    'addon_outer_closure_sha256': hashlib.sha256(outer_path.read_bytes()).hexdigest(),
    'final_plan_review_sha256': hashlib.sha256(review_path.read_bytes()).hexdigest(),
}
save(OUT / 'huggingface-publication-pointer.json', pointer)
selected.add(OUT / 'huggingface-publication-pointer.json')

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
summary = {'schema': 'terminal-ir-final-root-compact-preparation@1', 'status': 'FINAL_VERIFIED_METADATA_READY_FOR_ORDINARY_PUBLICATION',
           'current_parent': parent, 'proposed_accelerator_gitlink': child,
           'original_head_index_unchanged': True, 'original_child_head_index_unchanged': True,
           'original_348_strict_inputs_unchanged': True, 'six_qualified_source_tests_and_protected_four_exact': True,
           'selected_files': rows, 'selected_bytes': sum(row['bytes'] for row in rows),
           'omitted_large_binary_or_lock_files': omitted,
           'awaiting': [],
           'new_test_prover_model_native_SQL_calls': 0, 'new_proof_claims': False,
           'full_benchmark_and_asymptotic_convergence': 'OPEN', 'official_score': None,
           'production_defaults': False, 'elapsed_seconds': time.monotonic() - start}
save(OUT / 'selection-final-04.json', summary)
contents[str((OUT / 'selection-final-04.json').relative_to(BASE))] = (OUT / 'selection-final-04.json').read_bytes()
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
old_child = git('ls-tree', parent, 'external/ipfs_accelerate').decode().split()[2]
expected_changed = changed + (['external/ipfs_accelerate'] if old_child != child else [])
assert sorted(git('diff', '--name-only', parent, tree).decode().splitlines()) == sorted(expected_changed)
for name, data in contents.items(): assert git('show', tree + ':' + name) == data
assert git('rev-parse', 'HEAD').decode().strip() == 'fe18069df4203da9bddfb77b1ed41748f4d5fb4d'
assert hashlib.sha256((BASE / '.git/index').read_bytes()).hexdigest() == '80b0426031778d38c8b762a273739e08edbf2ce2b18690efb4f541fa6de120a4'
assert git('ls-remote', 'origin', 'refs/heads/main').decode().split()[0] == parent
commit = git('commit-tree', tree, '-p', parent,
             data=b'Close scoped Hugging Face publication and retain authored metric proof evidence\n').decode().strip()
branch = 'refs/heads/codex/terminal-ir-final-publication-20261005-04'
git('update-ref', branch, commit)
save(OUT / 'prepared-final-04.json', {'schema': 'terminal-ir-final-root-prepush@1',
    'parent': parent, 'tree': tree, 'commit': commit, 'private_branch': branch,
    'selected_files': len(contents), 'new_paths': len(changed), 'canonical_child_gitlinks': root_children,
    'HF_revision': addon['commit'], 'original_head_index_unchanged': True,
    'duration_seconds': time.monotonic() - start, 'ordinary_nonforce_push': True})
push_start = time.monotonic()
result = subprocess.run(['git', 'push', 'origin', commit + ':refs/heads/main'], cwd=BASE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
push = {'schema': 'terminal-ir-final-root-push@1', 'parent': parent, 'commit': commit,
        'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
        'elapsed_seconds': time.monotonic() - push_start, 'force': False}
save(OUT / 'push-final-04.json', push)
if result.returncode: raise RuntimeError('ordinary final root publication push rejected; exact attempt retained')
remote_main = git('ls-remote', 'origin', 'refs/heads/main').decode().split()[0]
assert remote_main == commit
remote_child = git('ls-remote', 'origin', 'refs/heads/main', cwd=ACC_CHECKOUT).decode().split()[0]
assert remote_child == child
assert git('ls-tree', commit, 'external/ipfs_accelerate').decode().split()[2] == child
assert git('ls-tree', commit, 'external/ipfs_datasets').decode().split()[2] == root_children['external/ipfs_datasets']
for name, data in contents.items(): assert git('show', commit + ':' + name) == data
for row in source['paths'] + source['protected4']:
    data = git('show', child + ':' + row['path'], cwd=ACC_CHECKOUT)
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
for row in strict:
    data = Path(row['path']).read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
assert git('rev-parse', 'HEAD').decode().strip() == 'fe18069df4203da9bddfb77b1ed41748f4d5fb4d'
assert hashlib.sha256((BASE / '.git/index').read_bytes()).hexdigest() == '80b0426031778d38c8b762a273739e08edbf2ce2b18690efb4f541fa6de120a4'
assert git('rev-parse', 'HEAD', cwd=BASE / 'external/ipfs_accelerate').decode().strip() == original['original_head']
assert hashlib.sha256(Path(original['original_index']['path']).read_bytes()).hexdigest() == original['original_index']['sha256']
assert HfApi().repo_info('Publicus/codebase-ir-proof-index', repo_type='dataset', revision='main').sha == addon['commit']
closed = {'schema': 'terminal-ir-final-root-publication-closed@1',
    'status': 'PUBLISHED_AND_REMOTE_MAIN_VERIFIED', 'commit': commit, 'parent': parent, 'tree': tree,
    'url': 'https://github.com/endomorphosis/lift_coding/commit/' + commit,
    'remote_main': remote_main, 'remote_accelerator_main': remote_child,
    'canonical_child_gitlinks': root_children, 'HF_revision': addon['commit'], 'HF_url': pointer['url'],
    'selected_files': len(contents), 'new_paths': len(changed), 'selected_bytes': summary['selected_bytes'],
    'source_and_receipt_blob_readbacks_exact': True, 'original_348_strict_inputs_unchanged': True,
    'six_qualified_source_tests_and_protected_four_exact': True,
    'original_root_accelerator_HEAD_indexes_unchanged': True, 'concurrent_root_features_preserved': True,
    'datasets_published_qualification_ancestor_preserved': True,
    'ordinary_nonforce_push': True, 'new_tests_provers_model_training_native_SQL_jobs': 0,
    'whole_source_full_task_asymptotic_and_global_convergence': 'OPEN',
    'all32_governing_exits': 'OPEN', 'official_benchmark_score': None, 'production_defaults': False,
    'qualification_and_archive_scope': pointer['qualification_limits'],
    'selection': {'path': str((OUT / 'selection-final-04.json').relative_to(BASE)),
                  'bytes': (OUT / 'selection-final-04.json').stat().st_size,
                  'sha256': hashlib.sha256((OUT / 'selection-final-04.json').read_bytes()).hexdigest()},
    'duration_seconds': time.monotonic() - start}
save(OUT / 'publication-final-closed-04.json', closed)
print(json.dumps({'status': closed['status'], 'commit': commit, 'parent': parent,
    'files': len(contents), 'selected_bytes': summary['selected_bytes'], 'child': child,
    'HF_revision': addon['commit'], 'duration_seconds': closed['duration_seconds'],
    'receipt_sha256': hashlib.sha256((OUT / 'publication-final-closed-04.json').read_bytes()).hexdigest()}))
