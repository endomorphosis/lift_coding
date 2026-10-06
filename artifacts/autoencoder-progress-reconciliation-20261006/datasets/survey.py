#!/usr/bin/env python3
"""Read-only datasets branches/worktrees/effective-source reconciliation.

Only Git metadata/source blobs and local statuses are read. Live remote heads
are queried, without fetch, merges, checkouts, resets or index writes. Reuses the
workspace's pure effective-tree auditor rather than treating ancestry as code
retention. Writes only this artifact directory.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / '.worktrees/contextual-legal-runtime-datasets-20261006'
OUT = ROOT / 'artifacts/autoencoder-progress-reconciliation-20261006/datasets'
AUDITOR = ROOT / 'scripts/review_autoencoder_progress.py'
PREFIX = 'ipfs_datasets_py/logic/formalization/autoencoder/'
RELEVANT = re.compile(r'autoencoder|decoder|alignment|source-v2|legal|ir-|publication|local-source|active-tests|training-publish', re.I)
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')


def git(*args, cwd=REPO, check=True, timeout=45):
    result = subprocess.run(['git', '--no-optional-locks', '-C', str(cwd), *args],
        capture_output=True, env=ENV, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[:2000])
    return result


def pin(path):
    path = Path(path)
    if not path.is_file():
        return None
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def remote_heads():
    rows = git('ls-remote', '--heads', 'origin').stdout.decode().splitlines()
    return [dict(ref=line.split('\t')[1], commit=line.split('\t')[0]) for line in rows]


def worktrees():
    blocks = git('worktree', 'list', '--porcelain').stdout.decode().strip().split('\n\n')
    values = []
    for block in blocks:
        item = {}
        for line in block.splitlines():
            key, _, value = line.partition(' ')
            item[key] = value if value else True
        values.append(item)
    return values


def status(path):
    data = git('status', '--porcelain=v1', '-z', '--untracked-files=all', cwd=path).stdout
    parts, result, index = data.split(b'\0'), [], 0
    while index < len(parts) and parts[index]:
        item = parts[index].decode(errors='surrogateescape')
        row = dict(status=item[:2], path=item[3:])
        if 'R' in row['status'] or 'C' in row['status']:
            index += 1; row['previous_path'] = parts[index].decode(errors='surrogateescape')
        result.append(row); index += 1
    return result


def witness_worktree(entry):
    path = Path(entry['worktree'])
    result = dict(registration=entry, registered_path=str(path))
    if not path.exists():
        return dict(result, present=False)
    try:
        actual = Path(git('rev-parse', '--show-toplevel', cwd=path).stdout.decode().strip())
        index_path = Path(git('rev-parse', '--path-format=absolute', '--git-path', 'index', cwd=path).stdout.decode().strip())
        head_before = git('rev-parse', 'HEAD', cwd=path).stdout.decode().strip()
        index_before = pin(index_path)
        dirty_before = status(path)
        branch = git('symbolic-ref', '--quiet', '--short', 'HEAD', cwd=path, check=False).stdout.decode().strip() or None
        head_after = git('rev-parse', 'HEAD', cwd=path).stdout.decode().strip()
        dirty_after = status(path)
        index_after = pin(index_path)
        result.update(present=True, effective_worktree_path=str(actual), branch=branch,
            head_before=head_before, head_after=head_after, dirty_files_before=dirty_before,
            dirty_files_after=dirty_after, dirty_count=len(dirty_after),
            relevant_dirty_files=[row for row in dirty_after if RELEVANT.search(row['path'])
                and row['path'].endswith(('.py', '.md', '.json', '.yaml', '.yml', '.toml'))],
            index_pin_before=index_before, index_pin_after=index_after,
            stable_at_read_endpoints=head_before == head_after and dirty_before == dirty_after and index_before == index_after)
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as error:
        result.update(error=str(error)[:1500], inspected=False)
    return result


def refs():
    data = git('for-each-ref', '--format=%(refname)%00%(objectname)%00%(committerdate:iso-strict)%00%(subject)').stdout.decode()
    return [dict(zip(('ref', 'commit', 'committer_time', 'subject'), line.split('\0', 3))) for line in data.splitlines()]


def ancestor(source, target):
    result = git('merge-base', '--is-ancestor', source, target, check=False)
    assert result.returncode in (0, 1)
    return result.returncode == 0


def count_difference(source, target):
    counts = git('rev-list', '--left-right', '--count', target+'...'+source).stdout.decode().strip().split()
    return dict(target_only_commits=int(counts[0]), source_only_commits=int(counts[1]))


def source_paths(revision):
    result = git('ls-tree', '-r', '--name-only', revision, '--', PREFIX,
        'docs/autoencoders', 'scripts/ops/autoencoder', 'tests/unit/logic/formalization/autoencoder',
        'ipfs_datasets_py/logic/intent_ir/autoencoder.py',
        'ipfs_datasets_py/logic/security_ir/autoencoder.py',
        'ipfs_datasets_py/logic/software_contracts/semantic_index/explicit_git_decoder_profile.py').stdout.decode().splitlines()
    keep = []
    expressions = re.compile(r'(contextual_legal_ir|ir_(cell|decoder|model|original)|source_checkpoint_continuation|source_training_v2|'
        r'paraphrase|normative|prospective_wording|generated_scalar|source_fidelity|progress_integration|four_width|'
        r'gte_aligned|decoder_interface|clause_source_context|source_value_decoder_experiment|explicit_git_decoder_profile|autoencoder\.py$)')
    for path in result:
        if path.endswith(('.py', '.md')) and expressions.search(path):
            keep.append(path)
    return keep


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    remote_before = remote_heads()
    target = next(row['commit'] for row in remote_before if row['ref'] == 'refs/heads/main')
    assert git('cat-file', '-e', target+'^{commit}', check=False).returncode == 0
    refs_before = refs(); registry_before = worktrees()
    with ThreadPoolExecutor(max_workers=4) as executor:
        observed_worktrees = list(executor.map(witness_worktree, registry_before))
    local_heads = [row for row in refs_before if row['ref'].startswith('refs/heads/')]
    live_heads = [{**row, 'ref': 'live-origin/'+row['ref'][len('refs/heads/'):]} for row in remote_before]
    unique = sorted({row['commit'] for row in local_heads+live_heads})
    with ThreadPoolExecutor(max_workers=4) as executor:
        reachability = dict(zip(unique, executor.map(lambda commit: ancestor(commit, target), unique)))
    branches = []
    for row in local_heads+live_heads:
        branches.append(dict(row, reachable_from_main=reachability[row['commit']],
            relevant_name=bool(RELEVANT.search(row['ref'])),
            ahead_behind_main=count_difference(row['commit'], target)))
    spec = importlib.util.spec_from_file_location('readonly_effective_tree_auditor', AUDITOR)
    auditor = importlib.util.module_from_spec(spec); spec.loader.exec_module(auditor)
    selected = {row['commit']:row for row in branches if row['relevant_name']}
    def effective(row):
        paths = source_paths(row['commit'])
        if not paths:
            return dict(source_revision=row['commit'], selected_paths=0, counts={})
        result = auditor.review(REPO, row['commit'], target, paths)
        result['source_refs'] = [branch['ref'] for branch in branches if branch['commit']==row['commit']]
        name = 'effective-'+row['commit'][:12]+'.json'
        (OUT/name).write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
        return dict(source_revision=row['commit'], source_refs=result['source_refs'],
            source_history_reachable_from_target=result['source_history_reachable_from_target'],
            selected_paths=len(paths), counts=result['counts'], receipt_pin=pin(OUT/name),
            missing_paths=[entry['path'] for entry in result['paths'] if entry['status']=='missing'],
            modified_paths=[entry['path'] for entry in result['paths'] if entry['status']=='modified'])
    with ThreadPoolExecutor(max_workers=3) as executor:
        effective_reviews = list(executor.map(effective, selected.values()))
    remote_after = remote_heads(); registry_after = worktrees(); refs_after = refs()
    studies = json.loads((ROOT/'artifacts/autoencoder-integration-review-20261006/findings/evidence-matrix.json').read_text())
    new_changed = git('diff', '--name-status', '39f25777', target).stdout.decode().splitlines()
    new_log = git('log', '--format=%H%x00%cI%x00%s', '39f25777..'+target).stdout.decode().splitlines()
    report = dict(schema='datasets-autoencoder-progress-reconciliation-survey/v1',
        completed=True, observed_at_utc=datetime.now(timezone.utc).isoformat(),
        repository=str(REPO), live_GitHub_origin=git('remote','get-url','origin').stdout.decode().strip(),
        main_snapshot_commit=target, live_GitHub_heads_before=remote_before, live_GitHub_heads_after=remote_after,
        remote_heads_stable_at_endpoints=remote_before==remote_after,
        all_local_refs_before=refs_before, all_local_refs_after=refs_after,
        local_refs_stable_at_endpoints=refs_before==refs_after,
        worktree_registry_before=registry_before, worktree_registry_after=registry_after,
        worktree_registry_stable_at_endpoints=registry_before==registry_after,
        worktrees=observed_worktrees, branches=branches,
        local_branch_count=len(local_heads), live_GitHub_head_count=len(remote_before),
        registered_worktree_count=len(registry_before),
        branches_not_reachable_main=[row for row in branches if not row['reachable_from_main']],
        effective_source_reviews=effective_reviews,
        existing_effective_tree_auditor_pin=pin(AUDITOR), script_pin=pin(__file__),
        prior_sixteen_study_matrix_pin=pin(ROOT/'artifacts/autoencoder-integration-review-20261006/findings/evidence-matrix.json'),
        prior_study_ids=[row['id'] for row in studies['entries']],
        newer_main_since_contextual39f25777=dict(commits=new_log, changed_files=new_changed),
        operations=dict(GitHub_ls_remote=True, git_fetch=False, git_index_writes=False,
            merges=False, checkouts=False, resets=False, source_or_asset_edits=False,
            model_encoder_training_execution=False, catalogs_or_HF_mutation=False),
        preserved_dirty_tree_scope='Read-only endpoint observations; concurrent agents can change their own worktrees. No status read permits restoration or merging an active dirty tree.',
        qualification=False)
    target_path=OUT/'survey.json';target_path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(survey_pin=pin(target_path),main=target,GitHub_heads=len(remote_before),
        local_branches=len(local_heads),registered_worktrees=len(registry_before),
        dirty_worktrees=sum(row.get('dirty_count',0)>0 for row in observed_worktrees),
        unstable_worktrees=[row['registered_path'] for row in observed_worktrees if row.get('stable_at_read_endpoints') is False],
        unreachable_branches=[row['ref'] for row in report['branches_not_reachable_main']],
        effective_missing_counts=[{'commit':row['source_revision'],'missing':row['counts'].get('missing',0)}
            for row in effective_reviews if row['counts'].get('missing')]),sort_keys=True))


if __name__=='__main__':
    main()
