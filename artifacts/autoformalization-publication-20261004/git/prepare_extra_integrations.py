"""Prepare owned helper-repository main integrations; never push a remote."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent
RUN = OUT / 'extra-integrations-01'
ROOT = OUT.parents[2]
INTEGRATOR = OUT.parent / 'integrate_main.py'
INTEGRATOR_SHA = '98a07d90178b724ba28aeed8f7bc82e374ab0c93b172ff231b13f2283147e8a3'
SELECTION = OUT / 'snapshot_import_selection.json'
SELECTION_SHA = 'b5785c2bfafd54320c1c5b7b98db2c568e7cfa1618decfcb377085f5bcfc8b0a'
SEVEN = {'lift_coding', 'ipfs_datasets_py', 'ipfs_accelerate_py', 'ipfs_kit_py',
         'Mcp-Plus-Plus', 'hallucinate_app', 'swissknife'}
MAX_BLOB = 100 * 1024**2
ENV = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0',
       'GIT_MERGE_AUTOEDIT': 'no'}
for _key in ['GIT_INDEX_FILE', 'GIT_DIR', 'GIT_WORK_TREE']:
    ENV.pop(_key, None)


def pin(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode() + b'\n'
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return pin(path)


def git(repo, *args, allowed=(0,), data=None, timeout=120):
    result = subprocess.run(['git', '-c', 'gc.auto=0', '-c', 'core.fsmonitor=false',
                             '-C', str(repo), *args], env=ENV, input=data,
                            capture_output=True, timeout=timeout, check=False)
    if result.returncode not in allowed:
        raise RuntimeError('Git operation failed: ' + args[0] + ', exit=' + str(result.returncode)
                           + ', stderr_sha256=' + hashlib.sha256(result.stderr).hexdigest())
    return result


def text(repo, *args, **kwargs):
    return git(repo, *args, **kwargs).stdout.decode().strip()


def selected_tree(repo, head):
    selected, excluded = [], []
    for entry in git(repo, 'ls-tree', '-r', '-z', head).stdout.split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        relative = os.fsdecode(name)
        basename = Path(relative).name.lower()
        if kind != 'blob':
            excluded.append({'path': relative, 'reason': 'gitlink_or_nonblob'})
            continue
        if basename.startswith(('.env', 'credentials')) or basename in {
            'id_rsa', 'id_ed25519', '.netrc', '.git-credentials',
        } or Path(relative).suffix.lower() in {'.pem', '.key', '.p12', '.pfx'}:
            excluded.append({'path': relative, 'reason': 'credential_filename_no_bytes_read'})
            continue
        size = int(text(repo, 'cat-file', '-s', oid))
        if size > MAX_BLOB:
            excluded.append({'path': relative, 'reason': 'oversized_existing_blob_not_read', 'bytes': size})
            continue
        data = git(repo, 'cat-file', 'blob', oid).stdout
        if len(data) != size:
            raise ValueError('canonical blob size changed')
        selected.append({'path': relative, 'state': 'present', 'mode': mode,
                         'sha256': hashlib.sha256(data).hexdigest()})
    return selected, excluded


def oversized_new_blobs(repo, tip):
    remote_heads = text(repo, 'for-each-ref', '--format=%(objectname)', 'refs/remotes/origin').splitlines()
    data = ('\n'.join([tip, *['^' + item for item in sorted(set(remote_heads))]]) + '\n').encode()
    objects = git(repo, 'rev-list', '--objects', '--stdin', data=data).stdout.splitlines()
    names = {}
    for item in objects:
        oid, _, name = item.partition(b' ')
        names.setdefault(oid, os.fsdecode(name))
    if not names:
        return []
    metadata = git(repo, 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)',
                   data=b'\n'.join(names) + b'\n').stdout.splitlines()
    big = []
    for item in metadata:
        oid, kind, size = item.split()
        if kind == b'blob' and int(size) > MAX_BLOB:
            big.append({'oid': oid.decode(), 'path': names[oid], 'bytes': int(size)})
    return big


def main():
    source = INTEGRATOR.read_bytes()
    selection_bytes = SELECTION.read_bytes()
    if hashlib.sha256(source).hexdigest() != INTEGRATOR_SHA:
        raise ValueError('frozen integration owner changed')
    if hashlib.sha256(selection_bytes).hexdigest() != SELECTION_SHA:
        raise ValueError('snapshot selection changed')
    spec = importlib.util.spec_from_file_location('verified_extra_integrator', INTEGRATOR)
    owner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = owner
    exec(compile(source, str(INTEGRATOR), 'exec'), owner.__dict__)
    selection = json.loads(selection_bytes)
    RUN.mkdir(mode=0o700)
    (RUN / 'repositories').mkdir(mode=0o700)
    base = ROOT / '.worktrees/publication-extras-20261004'
    base.mkdir(mode=0o700)
    receipts = []
    save(RUN / 'execution_plan.json', {
        'schema': 'owned-extra-integration-execution-plan/v1',
        'runner_binding': pin(Path(__file__)), 'integrator_binding': pin(INTEGRATOR),
        'snapshot_selection_binding': pin(SELECTION),
        'canonical_current_complete_tree_authority': True,
        'gitlinks_and_credential_filenames_excluded_from_source_byte_read': True,
        'remote_main_preferred_when_present_master_only_when_main_absent': True,
        'origin_push_authorized_for_this_runner': False,
    })
    for origin, role in selection['targets'].items():
        name = origin.rsplit('/', 1)[1]
        if name in SEVEN:
            continue
        directory = RUN / 'repositories' / name
        directory.mkdir(mode=0o700)
        repo = Path(role['canonical_worktree'])
        index_path = Path(text(repo, 'rev-parse', '--git-path', 'index'))
        if not index_path.is_absolute():
            index_path = repo / index_path
        before = {'head': text(repo, 'rev-parse', 'HEAD'),
                  'branch': text(repo, 'symbolic-ref', '-q', 'HEAD', allowed=(0, 1)),
                  'index_binding': pin(index_path),
                  'status': git(repo, 'status', '--porcelain', '--untracked-files=normal').stdout.decode()}
        if before['status']:
            raise ValueError('extra canonical source is no longer clean')
        remote = text(repo, 'remote', 'get-url', 'origin')
        if owner.normalized_origin(remote) != origin:
            raise ValueError('extra representative remote differs')
        fetched = git(repo, 'fetch', '--recurse-submodules=no', '--no-tags',
                      '--no-auto-maintenance', 'origin', '+refs/heads/*:refs/remotes/origin/*')
        remote_heads = {}
        for row in git(repo, 'ls-remote', '--heads', 'origin', 'refs/heads/main',
                       'refs/heads/master').stdout.splitlines():
            oid, ref = row.decode().split()
            remote_heads[ref] = oid
        baseline_ref = 'origin/main' if 'refs/heads/main' in remote_heads else 'origin/master'
        baseline = remote_heads['refs/heads/' + baseline_ref.split('/')[1]]
        if text(repo, 'rev-parse', '--verify', 'refs/remotes/' + baseline_ref) != baseline:
            raise ValueError('selected remote baseline advanced between fetch and listing')
        selected_files, exclusions = selected_tree(repo, before['head'])
        heads = [{'oid': item['oid'], 'kind': item['kind']} for item in role['selected_heads']]
        heads.append({'oid': before['head'], 'kind': 'canonical_current_source'})
        unique = []
        seen = set()
        for item in reversed(heads):
            if item['oid'] not in seen:
                unique.append(item)
                seen.add(item['oid'])
        heads = list(reversed(unique))
        worktree = base / name
        plan = {'canonical_repository': str(repo), 'normalized_origin': origin,
                'baseline_remote_ref': baseline_ref, 'origin_main_sha256_or_git_oid': baseline,
                'fresh_worktree': str(worktree),
                'integration_branch': 'publication/extra-main-20261004/' + name,
                'heads': heads,
                'authoritative_source': {'snapshot_commit': before['head'], 'selected_files': selected_files}}
        plan_binding = save(directory / 'plan.json', plan)
        save(directory / 'preparation.json', {
            'schema': 'owned-extra-integration-preparation/v1', 'original_active_state': before,
            'fresh_origin_baseline': baseline, 'baseline_ref': baseline_ref,
            'selected_remote_head_listing': remote_heads,
            'fetch_stdout_sha256': hashlib.sha256(fetched.stdout).hexdigest(),
            'fetch_stderr_sha256': hashlib.sha256(fetched.stderr).hexdigest(),
            'submodule_recursion': False, 'automatic_gc': False,
            'canonical_source_exclusions': exclusions, 'plan_binding': plan_binding,
            'origin_push_performed': False,
        })
        prepared = directory / 'integration'
        prepared.mkdir(mode=0o700)
        owner.integrate(plan, prepared)
        report = json.loads((prepared / 'prepared.json').read_bytes())
        big = oversized_new_blobs(repo, report['integrated_tip'])
        after = {'head': text(repo, 'rev-parse', 'HEAD'),
                 'branch': text(repo, 'symbolic-ref', '-q', 'HEAD', allowed=(0, 1)),
                 'index_binding': pin(index_path),
                 'status': git(repo, 'status', '--porcelain', '--untracked-files=normal').stdout.decode()}
        if before != after:
            raise ValueError('original extra checkout state changed')
        if pin(INTEGRATOR)['sha256'] != INTEGRATOR_SHA or pin(SELECTION)['sha256'] != SELECTION_SHA:
            raise ValueError('selected integration input changed')
        receipt = save(directory / 'qualification.json', {
            'schema': 'owned-extra-integration-push-readiness/v1',
            'normalized_origin': origin, 'canonical_repository': str(repo),
            'fresh_worktree': str(worktree), 'integrated_tip': report['integrated_tip'],
            'baseline_remote_ref': baseline_ref, 'baseline_origin_oid': baseline,
            'prepared_binding': pin(prepared / 'prepared.json'), 'plan_binding': plan_binding,
            'original_checkout_before': before, 'original_checkout_after': after,
            'original_checkout_index_head_branch_files_preserved': True,
            'all_selected_heads_ancestors': report['all_selected_heads_ancestors'],
            'newly_reachable_blobs_over_100MiB_vs_all_fetched_origin_refs': big,
            'new_blob_inventory_eligible': not big,
            'eligible_for_root_prepublication_review': not big and report['eligible_for_root_prepublication_review'],
            'origin_push_performed': False, 'force_push_used': False,
        })
        receipts.append(receipt)
        print(json.dumps({'origin': origin, 'qualification_binding': receipt,
                          'selected_heads': len(heads), 'new_oversized_blob_count': len(big)}, sort_keys=True), flush=True)
    final = save(RUN / 'results.json', {
        'schema': 'owned-extra-integrations-prepared/v1', 'created_utc': datetime.now(UTC).isoformat(),
        'repository_count': len(receipts), 'qualification_bindings': receipts,
        'runner_binding': pin(Path(__file__)), 'origin_push_performed': False,
    })
    print(json.dumps({'results_binding': final}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
