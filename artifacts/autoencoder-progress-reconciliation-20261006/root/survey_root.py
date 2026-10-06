"""Read-only parent repository survey; fetch is an explicit caller operation."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/home/barberb/lift_coding')
OUT = ROOT / 'artifacts/autoencoder-progress-reconciliation-20261006/root'


def git(*args, cwd=ROOT, check=True):
    result = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', 'replace')[:512])
    return result


def data(*args, cwd=ROOT):
    return git(*args, cwd=cwd).stdout.decode('utf-8', 'replace').strip()


def worktrees():
    records = []
    for block in data('worktree', 'list', '--porcelain').split('\n\n'):
        record = {}
        for line in block.splitlines():
            key, _, value = line.partition(' ')
            record[key] = value if value else True
        if record:
            records.append(record)
    return records


def main():
    target = data('rev-parse', 'origin/main')
    remote = data('ls-remote', '--heads', 'origin')
    heads = {line.split()[1]: line.split()[0] for line in remote.splitlines()}
    before = worktrees()
    snapshots = []
    for tree in before:
        path = Path(tree['worktree'])
        result = git('status', '--porcelain=v1', '-z', cwd=path, check=False)
        record = dict(tree)
        if result.returncode:
            record.update(status_available=False, status_error=result.stderr.decode('utf-8', 'replace')[:512])
        else:
            status = result.stdout
            rows = [row.decode('utf-8', 'replace') for row in status.split(b'\0') if row]
            record.update(status_available=True, dirty_records=len(rows), status_sha256=hashlib.sha256(status).hexdigest(),
                relevant_dirty_records=[row for row in rows if any(word in row.lower() for word in
                    ('autoencod', 'formaliz', 'implementation_plan', 'ipfs_datasets', 'ipfs_accelerate', 'gitmodules'))])
        snapshots.append(record)
    refs = []
    for line in data('for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads', 'refs/remotes/origin').splitlines():
        name, commit = line.split()
        reachable = git('merge-base', '--is-ancestor', commit, target, check=False).returncode
        assert reachable in (0, 1)
        result = {'ref': name, 'commit': commit, 'ancestor_of_snapshot_main': reachable == 0}
        if reachable == 1 and any(word in name.lower() for word in
                ('autoencod', 'formaliz', 'decoder', 'alignment', 'source', 'ir-', 'wording', 'contrast', 'joint')):
            result['unmerged_log'] = data('log', '--format=%H %s', target + '..' + commit, '--max-count=40').splitlines()
            result['changed_paths'] = data('diff', '--name-only', target + '...' + commit).splitlines()
            result['patch_equivalence'] = data('cherry', target, commit).splitlines()
        refs.append(result)
    assert worktrees() == before
    assert data('rev-parse', 'origin/main') == target
    value = {'schema': 'autoencoder-parent-worktree-survey/v1', 'repository': str(ROOT), 'snapshot_main': target,
        'remote_heads': heads, 'remote_head_count': len(heads), 'local_and_origin_refs': refs, 'ref_count': len(refs),
        'worktrees': snapshots, 'worktree_count': len(snapshots), 'worktree_registry_unchanged': True,
        'ordinary_heads_or_indexes_modified': False, 'models_executed': False, 'training_executed': False,
        'proof_admission_granted': False, 'scope': 'Explicit snapshots; worktree statuses are observations, not atomic global currentness.'}
    (OUT / 'survey.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'main': target, 'remote_heads': len(heads), 'refs': len(refs), 'worktrees': len(snapshots),
        'dirty_worktrees': sum(row.get('dirty_records', 0) > 0 for row in snapshots)}))


if __name__ == '__main__':
    main()
