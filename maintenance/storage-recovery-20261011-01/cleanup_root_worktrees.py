"""Remove only explicitly audited, clean, merged root checkout duplicates."""
import datetime
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/home/barberb/lift_coding')
CAMPAIGN = ROOT / 'maintenance/storage-recovery-20261011-01'
OWNER = ROOT / '.worktrees/dual-bank-wording-adapter-root-20261007'
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
RECEIPT = CAMPAIGN / 'root-worktree-cleanup-results-02.json'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run(argv, timeout=120):
    p = subprocess.run(argv, env=ENV, capture_output=True, text=True, timeout=timeout)
    return {'argv': argv, 'returncode': p.returncode,
            'stdout': p.stdout, 'stderr': p.stderr}


def git(path, *args):
    return run(['git', '-C', str(path), *args])


def free():
    s = os.statvfs(ROOT)
    return s.f_bavail * s.f_frsize


def proc_references(path):
    hits = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            cwd = Path(os.readlink(proc / 'cwd'))
            if cwd == path or path in cwd.parents:
                hits.append({'pid': int(proc.name), 'kind': 'cwd', 'path': str(cwd)})
            # A parent working directory can own nested runtime worktrees.
            if cwd != ROOT and cwd not in ROOT.parents and cwd != path and cwd in path.parents:
                hits.append({'pid': int(proc.name), 'kind': 'active_parent', 'path': str(cwd)})
        except OSError:
            pass
        try:
            for fd in (proc / 'fd').iterdir():
                try:
                    target = Path(os.readlink(fd))
                    if target == path or path in target.parents:
                        hits.append({'pid': int(proc.name), 'kind': 'open_fd', 'path': str(target)})
                except OSError:
                    pass
        except OSError:
            pass
    return hits


def save(receipt):
    tmp = RECEIPT.with_suffix('.tmp')
    tmp.write_text(json.dumps(receipt, indent=2) + '\n')
    tmp.replace(RECEIPT)


def main():
    if RECEIPT.exists():
        raise SystemExit('Existing cleanup receipt: do not replay this mutation campaign.')
    audit = json.loads((CAMPAIGN / 'git-datasets-audit.json').read_text())['repositories']['root']
    sizes = {x['path']: x for x in json.loads((CAMPAIGN / 'root-merged-candidate-sizes.json').read_text())}
    remote = git(ROOT, 'ls-remote', 'origin', 'refs/heads/main')
    if remote['returncode'] or not remote['stdout'].strip():
        raise SystemExit('Cannot establish remote main custody.')
    remote_sha = remote['stdout'].split()[0]
    if git(ROOT, 'cat-file', '-e', remote_sha + '^{commit}')['returncode']:
        raise SystemExit('Remote main unavailable locally.')
    receipt = {'schema': 'targeted-root-worktree-cleanup/v1', 'started_at': now(),
               'free_before': free(), 'remote_main_witness': remote,
               'policy': 'No force, no canonical/locked/live/dirty/ignored/nested trees; retained commits are ancestors of observed remote main.',
               'operations': [], 'held': []}
    save(receipt)
    for w in audit['worktrees']:
        p = Path(w['path'])
        holds = [h for h in w.get('protect_reasons', []) if not h.startswith('top-level')]
        if p == ROOT or '20261011' in p.name or '20261011' in str(p.parent) or holds:
            continue
        if not w.get('clean_tracked_and_untracked') or w.get('ignored_entry_count'):
            continue
        if w.get('locked_reason') or w.get('nested_registered_worktrees'):
            continue
        if not w.get('relationship', {}).get('ancestor_of_local_origin_main'):
            continue
        checks = {
            'top': git(p, 'rev-parse', '--show-toplevel'),
            'head': git(p, 'rev-parse', 'HEAD'),
            'status': git(p, 'status', '--porcelain=v1', '--untracked-files=all', '--ignored'),
            'ancestry': git(ROOT, 'merge-base', '--is-ancestor', w['head'], remote_sha),
        }
        references = proc_references(p)
        if (any(v['returncode'] for v in checks.values())
                or checks['top']['stdout'].strip() != str(p)
                or checks['head']['stdout'].strip() != w['head']
                or checks['status']['stdout'] or references):
            receipt['held'].append({'path': str(p), 'checks': checks, 'process_references': references})
            save(receipt)
            continue
        op = {'path': str(p), 'branch': w.get('branch'), 'head': w['head'],
              'allocated_bytes_audit': sizes.get(str(p), {}).get('size'),
              'checks': checks, 'process_references': references, 'free_before': free(),
              'started_at': now()}
        # Record selection before the only filesystem-removal operation.
        receipt['operations'].append(op)
        save(receipt)
        op['remove'] = git(ROOT, 'worktree', 'remove', str(p))
        if op['remove']['returncode'] == 0:
            op['path_absent'] = not p.exists()
            if w.get('branch'):
                name = w['branch'].removeprefix('refs/heads/')
                # OWNER is a main-descending checkout, allowing conservative -d.
                op['delete_local_branch'] = git(OWNER, 'branch', '-d', name)
        op['free_after'] = free()
        op['finished_at'] = now()
        save(receipt)
        print(json.dumps({'path': str(p), 'removed': op['remove']['returncode'] == 0,
                          'free_after': op['free_after']}), flush=True)
    receipt['free_after'] = free()
    receipt['finished_at'] = now()
    receipt['removed_count'] = sum(x['remove']['returncode'] == 0 for x in receipt['operations'])
    receipt['local_branches_removed'] = sum(x.get('delete_local_branch', {}).get('returncode') == 0 for x in receipt['operations'])
    save(receipt)
    print(json.dumps({k: receipt[k] for k in ['removed_count', 'local_branches_removed', 'free_before', 'free_after']}), flush=True)


if __name__ == '__main__':
    main()
