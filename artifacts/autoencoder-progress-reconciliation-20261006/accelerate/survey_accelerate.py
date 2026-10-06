#!/usr/bin/env python3
"""Read-only Git/source survey; writes only one fresh bounded metadata artifact.

No checkout, index, model, training, database, Hub or provider is opened or changed.
Fetch is deliberately external to this reproducible observation recipe. Git refs
are captured before/after; active worktrees are observations, not merge approval.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / '.worktrees/contextual-legal-runtime-accelerate-20261006'
AUDITOR = ROOT / 'scripts/review_autoencoder_progress.py'
RELEVANT = re.compile(r'autoencoder|decoder|formaliz|proof.?index|model.?manager|source384|codebase|intent|ir-|ir_|supervisor|planner|planning|semantic|terminal', re.I)
SELECTED = (
 'agent/contextual-legal-runtime-supervisor-20261006', 'agent/contextual-state-registration-20261006',
 'agent/supervisor-decoder-contract-20261006', 'codex/ir-persistent-catalog-20261004',
 'integration/ir-persistent-catalog-20261004-reviewed', 'agent/supervisor-profile-recovery-20261004',
 'agent/supervisor-intent-replay-20261005', 'agent/supervisor-multitask-profile-20261005',
 'agent/supervisor-task-context-20261005', 'codex/terminal-planning-schema-20261006',
 'codex/terminal-context-dictionary-20261006', 'codex/terminal-ir-publication-20261004-accelerate-01',
 'codex/terminal-suite-publication-20261004', 'codex/terminal-supervisor-contracts-20261004',
)
PATHS = (
 'ipfs_accelerate_py/model_catalog/sources/ir_persistent.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/task_ir_selection.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/task_ir_checkpoint.py',
 'benchmarks/agent_supervisor/container_coding/terminal_multitask_context.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/intent_advisor_selection.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/intent_autoencoder_advisor.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/source384_repository_context.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/source384_config.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/codebase_autoencoder.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/codebase_autoencoder_index.py',
 'ipfs_accelerate_py/agent_supervisor/planning/intent_symbolic_planning.py',
 'ipfs_accelerate_py/agent_supervisor/proof/ir_registry.py',
 'ipfs_accelerate_py/agent_supervisor/proof/ir_adapters.py',
 'ipfs_accelerate_py/agent_supervisor/proof/proof_scope_index.py',
 'ipfs_accelerate_py/agent_supervisor/objectives/ir_learning_campaign_contracts.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/codex_planning_schema.py',
 'docs/agent_supervisor/contextual_ir_checkpoint_recovery.md',
 'docs/agent_supervisor/intent_autoencoder_preplanning.md',
 'docs/agent_supervisor/terminal_symbolic_capabilities.md',
 'docs/architecture/repository_proof_index_and_codebase_ir.todo.md',
 'docs/architecture/proof_grounded_ir_learning/final_report.md',
)


def command(arguments, cwd=REPO, *, okay=(0,), timeout=60):
    result = subprocess.run(arguments, cwd=cwd, capture_output=True, timeout=timeout,
        env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    if result.returncode not in okay:
        raise ValueError('read-only command failed: ' + ' '.join(arguments[:3]) + ' (' + str(result.returncode) + ')')
    return result.returncode, result.stdout


def git(*args, cwd=REPO, okay=(0,)):
    return command(['git', '--literal-pathspecs', *args], cwd, okay=okay)[1]


def file_pin(path):
    path = Path(path)
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if identity(before) != identity(after):
        raise ValueError('evidence changed while read')
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def refs():
    raw = git('for-each-ref', '--format=%(refname)%00%(objectname)%00%(committerdate:iso-strict)%00%(subject)',
              'refs/heads', 'refs/remotes/origin')
    rows = []
    for line in raw.decode().splitlines():
        name, commit, date, subject = line.split('\0', 3)
        rows.append({'ref': name, 'commit': commit, 'date': date, 'subject': subject})
    return rows


def worktrees():
    records = []
    for block in git('worktree', 'list', '--porcelain').decode().strip().split('\n\n'):
        record = {}
        for line in block.splitlines():
            key, _, value = line.partition(' ')
            record[key] = value if value else True
        records.append(record)
    return records


def branch_relation(item, target):
    row = dict(item)
    behind, ahead = map(int, git('rev-list', '--left-right', '--count', target + '...' + item['commit']).decode().split())
    row.update(main_commits_absent_from_branch=behind, branch_commits_absent_from_main=ahead,
        relevant_name_or_subject=bool(RELEVANT.search(item['ref'] + ' ' + item['subject'])),
        history_status='same_commit' if ahead == behind == 0 else 'reachable_from_main' if ahead == 0 else 'unmerged_committed_history',
        readiness='not_assessed_by_git_ancestry')
    if row['relevant_name_or_subject'] and ahead:
        raw = git('diff', '--name-status', target, item['commit'])
        names = raw.decode(errors='replace').splitlines()
        row['main_tree_difference_count'] = len(names)
        row['relevant_tree_differences'] = [name for name in names if RELEVANT.search(name)][:512]
        row['relevant_tree_differences_capped'] = len([name for name in names if RELEVANT.search(name)]) > 512
    return row


def status(record):
    row = dict(record)
    path = Path(record['worktree'])
    if not path.is_dir():
        row.update(status='path_missing', dirty=None)
        return row
    try:
        before = git('rev-parse', 'HEAD', cwd=path).decode().strip()
        raw = git('status', '--porcelain=v1', '-z', '--untracked-files=all', cwd=path)
        tokens = raw.split(b'\0')
        entries, i = [], 0
        while i < len(tokens):
            value = tokens[i]; i += 1
            if not value:
                continue
            code, relative = value[:2].decode(), value[3:].decode(errors='replace')
            entry = {'status': code, 'path': relative}
            if 'R' in code or 'C' in code:
                if i < len(tokens):
                    entry['old_path'] = tokens[i].decode(errors='replace'); i += 1
            if RELEVANT.search(relative) and Path(relative).suffix in ('.py', '.md', '.json'):
                candidate = path / relative
                if candidate.is_file() and not candidate.is_symlink() and candidate.stat().st_size <= 512*1024:
                    entry['working_file_pin'] = file_pin(candidate)
            entries.append(entry)
        ending = git('rev-parse', 'HEAD', cwd=path).decode().strip()
        row.update(observed_head=before, closing_head=ending, head_stable=before == ending,
            dirty=bool(entries), dirty_entry_count=len(entries), dirty_entries=entries[:4096],
            dirty_entries_capped=len(entries)>4096, relevant_dirty_entries=[e for e in entries if RELEVANT.search(e['path'])][:512],
            status='observed_only', worktree_mutated=False)
    except Exception as error:
        row.update(status='observation_refused', error=type(error).__name__, dirty=None)
    return row


def branch_retention(name, target, auditor):
    choices = ['refs/remotes/origin/' + name, 'refs/heads/' + name]
    source = None
    for candidate in choices:
        value = command(['git', 'rev-parse', '--verify', '--end-of-options', candidate + '^{commit}'], okay=(0, 128))
        if value[0] == 0:
            source = value[1].decode().strip(); break
    if source is None:
        return {'branch': name, 'status': 'ref_missing'}
    merge_base = git('merge-base', source, target).decode().strip()
    delta = git('diff', '--name-only', merge_base, source).decode().splitlines()
    # When source is an ancestor, merge-base is itself: use its own last relevant
    # implementation changes rather than claiming an empty delta proves retention.
    if not delta:
        delta = git('log', '-20', '--format=', '--name-only', source).decode().splitlines()
    selected = sorted(set(path for path in delta if path.endswith(('.py', '.md'))
        and not '/evidence/' in path and (path.startswith(('ipfs_accelerate_py/', 'benchmarks/', 'test/', 'tests/', 'docs/agent_supervisor/', 'docs/architecture/')))))
    existing = []
    for path in selected:
        if git('ls-tree', source, '--', path):
            existing.append(path)
    if not existing:
        return {'branch': name, 'source_commit': source, 'status': 'no_selected_source_paths', 'scope': 'not an effective tree qualification'}
    cap = existing[:128]
    review = auditor.review(REPO, source, target, cap)
    return {'branch': name, 'source_commit': source, 'selected_paths': len(existing), 'selection_capped': len(existing)>128,
        'selection_rule': 'non-evidence Python/Markdown changed paths; recent20-commit fallback for ancestor source', 'effective_tree_review': review}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh metadata output required')
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    initial_refs, initial_worktrees = refs(), worktrees()
    target = git('rev-parse', 'origin/main^{commit}').decode().strip()
    owner_head = git('rev-parse', 'HEAD').decode().strip()
    owner_status = git('status', '--porcelain=v1').decode()
    remote = git('ls-remote', '--heads', 'origin').decode().splitlines()
    remote_heads = [{'commit': line.split()[0], 'ref': line.split()[1]} for line in remote]
    with ThreadPoolExecutor(max_workers=6) as pool:
        relations = list(pool.map(lambda row: branch_relation(row, target), initial_refs))
        states = list(pool.map(status, initial_worktrees))
    spec = importlib.util.spec_from_file_location('_readonly_effective_tree_auditor', AUDITOR)
    auditor = importlib.util.module_from_spec(spec); spec.loader.exec_module(auditor)
    with ThreadPoolExecutor(max_workers=4) as pool:
        retention = list(pool.map(lambda name: branch_retention(name, target, auditor), SELECTED))
    source_entries = {path: auditor.path_entry(REPO, target, path) for path in PATHS}
    gitlinks = git('ls-tree', target).decode().splitlines()
    gitlinks = [line for line in gitlinks if line.startswith('160000 ')]
    historical = []
    for path in (ROOT/'implementation_plan/docs/58-autoencoder-progress-integration-2026-10-06.md', AUDITOR,
                 ROOT/'artifacts/autoencoder-integration-review-20261006/findings/evidence-matrix.json'):
        if path.is_file():
            historical.append(file_pin(path))
    ending_refs = refs()
    ending_worktrees = worktrees()
    closing_status = git('status', '--porcelain=v1').decode()
    result = {'schema': 'accelerate-autoencoder-progress-reconciliation/v1', 'observed_at_utc': start,
        'completed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'repository': str(REPO),
        'target_origin_main_commit': target, 'owner_head': owner_head, 'owner_clean_before': not owner_status,
        'owner_clean_after': not closing_status, 'owner_head_unchanged': owner_head == git('rev-parse','HEAD').decode().strip(),
        'refs_before': initial_refs, 'refs_after': ending_refs, 'refs_unchanged': initial_refs == ending_refs,
        'remote_heads_observed': remote_heads, 'local_and_tracking_relations': relations,
        'worktrees': states, 'worktree_registry_unchanged': initial_worktrees == ending_worktrees,
        'selected_effective_tree_reviews': retention, 'current_integration_source_entries': source_entries,
        'nested_gitlinks': gitlinks, 'prior_review_inputs': historical,
        'published_codex_structured_planning_commit': '82671e6c8411875cb9919e3a71b07831548c0aeb',
        'scope': 'Read-only history, effective-tree and worktree observations. Dirty work is active/unqualified; committed unmerged work still needs review. No model or proof qualification.',
        'operations': {'models_loaded': False, 'training_executed': False, 'database_opened': False,
            'huggingface_updated': False, 'checkout_index_or_worktree_mutated': False,
            'remote_heads_read_only_query': True, 'artifact_metadata_written': True},
        'script_pin': file_pin(Path(__file__).resolve())}
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False); handle.write('\n')
    print(json.dumps({'output': str(args.output), 'pin': file_pin(args.output), 'refs': len(initial_refs),
        'remote_heads':len(remote_heads), 'worktrees':len(states), 'dirty_worktrees':sum(row.get('dirty') is True for row in states),
        'selected_retention_reviews':len(retention), 'refs_unchanged':result['refs_unchanged']}), flush=True)


if __name__ == '__main__':
    main()
