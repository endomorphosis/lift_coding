"""Preserve one concurrently advanced source checkout without changing its HEAD."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
HELPER = OUT / 'snapshot_and_import.py'
HELPER_SHA = '8d41b21e88c562a8705a2ff6bdf05b4ccf0bd43f2c3913d35db32699b0fcf698'
PRIOR = OUT / 'snapshot-import-recovery-01'
RUN = OUT / 'snapshot-changed-head-recovery-02'
WORKTREE = '/home/barberb/lift_coding/.worktrees/terminal-suite-publication-20261004'
ORPHAN = '/home/barberb/lift_coding/.worktrees/pctdd-g9-orphan-recovery'


def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    data = HELPER.read_bytes()
    if hashlib.sha256(data).hexdigest() != HELPER_SHA:
        raise ValueError('frozen helper differs')
    spec = importlib.util.spec_from_file_location('verified_changed_head_snapshot', HELPER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(data, str(HELPER), 'exec'), module.__dict__)
    plan_file = PRIOR / 'plan.json'
    plan = json.loads(plan_file.read_bytes())
    item = next(x for x in plan['snapshot_worktrees'] if x['worktree'] == WORKTREE)
    blocked_file = next(f for f in (PRIOR / 'snapshots').glob('*.json')
                        if json.loads(f.read_bytes()).get('worktree') == WORKTREE)
    orphan_file = next(f for f in (PRIOR / 'failures').glob('*.json')
                       if json.loads(f.read_bytes()).get('worktree') == ORPHAN)
    frozen = [binding(path) for path in [HELPER, plan_file, blocked_file, orphan_file, OUT / 'snapshot_changed_head_recovery.py', OUT / 'snapshot-changed-head-recovery-01/plan.json']]
    blocked = json.loads(blocked_file.read_bytes())
    if blocked['status'] != 'blocked_captured_head_changed':
        raise ValueError('expected preserved cutoff block')
    RUN.mkdir(mode=0o700)
    for name in ['snapshots', 'created-source-commits', 'temporary-indexes']:
        (RUN / name).mkdir(mode=0o700)
    module.RUN = RUN
    original_git = module.git

    def git_no_gc(path, *args, **kwargs):
        return original_git(path, '-c', 'gc.auto=0', *args, **kwargs)

    module.git = git_no_gc

    def fetch_nonrecursive(target, source_common, commit, ref):
        existing = module.text_git(target, 'rev-parse', '--verify', ref, allowed=(0, 128))
        if existing and existing != commit:
            raise ValueError('publication ref already selects different content')
        if not existing:
            module.git(target, 'fetch', '--recurse-submodules=no', '--no-tags',
                       '--no-write-fetch-head', '--no-auto-maintenance',
                       str(source_common), commit + ':' + ref)
        if module.text_git(target, 'rev-parse', '--verify', ref) != commit:
            raise ValueError('imported snapshot changed')
        module.text_git(target, 'cat-file', '-e', commit + '^{commit}')
        return {'target_worktree': str(target), 'source_common_dir': str(source_common),
                'commit': commit, 'ref': ref, 'commit_verified': True,
                'force_used': False, 'origin_push_performed': False,
                'submodule_recursion': False, 'automatic_gc': False}

    module.fetch_ref = fetch_nonrecursive
    fresh = dict(item)
    fresh['head'] = module.text_git(Path(WORKTREE), 'rev-parse', 'HEAD')
    target = Path(plan['target_roles'][fresh['normalized_origin']]['canonical_worktree'])
    preparation = {
        'schema': 'changed-source-cutoff-recovery-plan/v1',
        'original_plan_and_failure_bindings': frozen,
        'runner_binding': binding(Path(__file__)),
        'original_captured_head': item['head'],
        'blocked_observed_head': blocked['observed_head'],
        'fresh_captured_head': fresh['head'],
        'fresh_snapshot_item': fresh,
        'missing_marker_worktree': ORPHAN,
        'missing_marker_disposition': 'physical_source_checkout_unavailable_only_data_directory_remains',
        'missing_marker_wholesale_deletion_snapshot_created': False,
        'missing_marker_source_files_recreated': False,
        'captured_missing_marker_head': '4e2562338314599c09b4898c5154cfc70f140c5f',
        'concurrent_cutoff_disclosed': True,
        'active_source_indexes_heads_branches_not_modified': True,
        'origin_push_performed': False,
    }
    module.save(RUN / 'plan.json', preparation)
    orphan_item = next(x for x in plan['snapshot_worktrees'] if x['worktree'] == ORPHAN)
    orphan_target = Path(plan['target_roles'][orphan_item['normalized_origin']]['canonical_worktree'])
    module.text_git(orphan_target, 'cat-file', '-e', preparation['captured_missing_marker_head'] + '^{commit}')
    selected = module.snapshot(fresh, target, 1)
    result = json.loads(Path(selected['path']).read_bytes())
    if result['status'] not in {'source_snapshot_created', 'no_meaningful_source_tree_change'}:
        raise ValueError('fresh source cutoff was not stable')
    for pin in frozen:
        if binding(Path(pin['path'])) != pin:
            raise ValueError('preserved cutoff evidence changed')
    output = module.save(RUN / 'results.json', {
        'schema': 'changed-source-cutoff-recovery-results/v1',
        'snapshot_receipt_binding': selected,
        'prior_evidence_preserved': True,
        'unavailable_orphan_historical_head_reachable_in_canonical_target': True,
        'origin_push_performed': False, 'main_merge_performed': False,
    })
    print(json.dumps(output, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
