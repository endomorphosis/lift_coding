"""Prepare root publication history in a fresh worktree with batched merges.

The two selected implementation owners stay byte-for-byte unchanged. This
producer imports no model code and does not push or modify original indexes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
BASE = ROOT / 'artifacts/autoformalization-publication-20261004/canonical_git'
PUBLICATION = BASE.parent
OWNER = PUBLICATION / 'integrate_main.py'
OWNER_SHA = '98a07d90178b724ba28aeed8f7bc82e374ab0c93b172ff231b13f2283147e8a3'
BATCH = PUBLICATION / 'resume_batched_integration_v2.py'
BATCH_SHA = '8aec173c135351a62f97ee334f5a66aa1902dfa569f1caa9bb3f5c8f9f30001c'


def binding(path):
    data = Path(path).read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def load(path, digest, name):
    if binding(path)['sha256'] != digest:
        raise ValueError('selected frozen helper changed: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def git(*args):
    result = subprocess.run(['git', '-c', 'gc.auto=0', '-c', 'submodule.recurse=false',
                             '-C', str(ROOT), *args], capture_output=True,
                            env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'}, timeout=180)
    if result.returncode:
        raise ValueError('root source metadata operation failed: ' + result.stderr.decode('utf-8', 'replace')[-3000:])
    return result.stdout


def prepare(snapshot, expected, execute):
    owner = load(OWNER, OWNER_SHA, 'root_frozen_integration_owner')
    batch = load(BATCH, BATCH_SHA, 'root_frozen_batch_owner')
    if binding(snapshot)['sha256'] != expected:
        raise ValueError('externally selected canonical snapshot report changed')
    source = json.loads(snapshot.read_bytes())
    if source['repository'] != str(ROOT) or source['name'] != 'root':
        raise ValueError('exact current root canonical snapshot required')
    original_head = git('rev-parse', 'HEAD').decode().strip()
    index_path = Path(os.fsdecode(git('rev-parse', '--git-path', 'index').strip()))
    if not index_path.is_absolute():
        index_path = ROOT / index_path
    original_index = binding(index_path)
    origin = owner.normalized_origin(git('remote', 'get-url', 'origin').decode().strip())
    if origin != 'github.com/endomorphosis/lift_coding':
        raise ValueError('exact owned root origin required')
    git('fetch', '--no-tags', '--no-prune', '--recurse-submodules=no', '--no-auto-maintenance',
        'origin', '+refs/heads/*:refs/remotes/origin/*')
    baseline = git('rev-parse', 'origin/main').decode().strip()
    live = git('ls-remote', '--heads', 'origin', 'refs/heads/main').decode().strip().split()
    if live != [baseline, 'refs/heads/main']:
        raise ValueError('root main advanced after selected fetch')
    refs = {}
    superseded = []
    for line in git('for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads',
                    'refs/remotes/publication-history-20261004',
                    'refs/remotes/publication-wip-20261004').decode().splitlines():
        ref, oid = line.split()
        if ref.startswith('refs/heads/publication/main-'):
            continue
        if ref.startswith('refs/heads/publication/canonical-current-root-20261004/'):
            if oid != 'ef9c8e4d94d9d427d1bd60168e9bd6d0a15cfe38':
                raise ValueError('unexpected superseded publication-only source head')
            superseded.append({'ref': ref, 'oid': oid, 'reason': 'Unpublished preparer-generated snapshot inadvertently included new HF staging; original ref is retained locally.'})
            continue
        refs.setdefault(oid, []).append(ref)
    refs.pop(source['snapshot_commit'], None)
    heads = [{'oid': oid, 'kind': 'preserved_history_or_worktree', 'selected_refs': names}
             for oid, names in sorted(refs.items())]
    heads.append({'oid': source['snapshot_commit'], 'kind': 'canonical_current_source',
                  'selected_refs': [source['snapshot_ref']]})
    destination = BASE / 'main-preparation-root-03'
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    plan = {'schema': 'canonical-leaf-main-integration-plan/v1', 'canonical_repository': str(ROOT),
            'normalized_origin': origin, 'baseline_remote_ref': 'origin/main',
            'origin_main_sha256_or_git_oid': baseline,
            'fresh_worktree': str(ROOT / '.worktrees/publication-main-20261004/root-03'),
            'integration_branch': 'publication/main-20261004/root-03', 'heads': heads,
            'authoritative_source': {'snapshot_commit': source['snapshot_commit'],
                                     'selected_files': source['selected_files']},
            'published_gitlinks': [], 'publication_only_superseded_source_heads_excluded': superseded,
            'integration_helper_binding': binding(OWNER),
            'batch_merge_helper_binding': binding(BATCH), 'canonical_snapshot_report_binding': binding(snapshot),
            'original_head': original_head, 'original_index_binding': original_index,
            'origin_push_authorized_for_driver': False, 'training_authorized_for_driver': False}
    plan_pin = owner.save(destination / 'plan.json', plan)
    print(json.dumps({'plan_binding': plan_pin, 'heads': len(heads), 'baseline': baseline}), flush=True)
    if not execute:
        return
    worktree = Path(plan['fresh_worktree'])
    if worktree.exists():
        raise ValueError('fresh root integration worktree required')
    worktree.parent.mkdir(parents=True, exist_ok=True)
    owner.run(ROOT, ['worktree', 'add', '-b', plan['integration_branch'], str(worktree), baseline])
    prior, output = destination / 'empty-prior', destination / 'integration-fast-01'
    prior.mkdir(mode=0o700)
    output.mkdir(mode=0o700)
    batch.resume(owner, plan, prior, output)
    if git('rev-parse', 'HEAD').decode().strip() != original_head or binding(index_path) != original_index:
        raise ValueError('original root HEAD or index changed')
    owner.save(destination / 'original-preservation.json', {
        'schema': 'canonical-root-original-state-preservation/v1', 'original_head': original_head,
        'original_index_binding': original_index, 'original_head_and_index_preserved': True,
        'plan_binding': plan_pin, 'prepared_binding': binding(output / 'prepared.json'),
        'origin_push_executed': False, 'training_executed': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--snapshot-sha', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    prepare(args.snapshot, args.snapshot_sha, args.execute)


if __name__ == '__main__':
    main()
