"""Targeted second pass after merge custody and auxiliary repo inventory."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cleanup_helpers', HERE / 'cleanup_root_worktrees.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
REPORT = HERE / 'additional-worktree-cleanup-results.json'


def main():
    if REPORT.exists():
        raise SystemExit('Existing mutation receipt; do not replay.')
    root = h.ROOT
    plans = [(root, root / 'artifacts/autoformalization-publication-20261004/current-main-joint-conditioning-01/publication-worktree',
              'refs/heads/codex/joint-conditioning-20261005-01', '8c02d655e2d086bd644a9011ea67325060ef87bc')]
    audit = json.loads((HERE / 'other-git-custody-audit.json').read_text())
    for rel, repo in audit.items():
        for w in repo['worktrees']:
            p = Path(w['worktree'])
            if w.get('locked') or w['status']['code'] or w['status']['stdout']:
                continue
            if w['ancestor']['code'] or w['resolved']['stdout'].strip() != str(p):
                continue
            # Canonical Git metadata entries and runtime-owned nested trees stay.
            if '.git/modules' in str(p) or 'data/agent_supervisor/' in str(p):
                continue
            plans.append((root / rel, p, w.get('branch'), w['HEAD']))
    report = {'started_at': h.now(), 'free_before': h.free(), 'operations': [], 'held': []}
    def save():
        REPORT.write_text(json.dumps(report, indent=2) + '\n')
    save()
    for repo, p, branch, head in plans:
        remote = h.git(repo, 'ls-remote', 'origin', 'refs/heads/main')
        if remote['returncode'] or not remote['stdout'].strip():
            report['held'].append({'path': str(p), 'remote': remote}); save(); continue
        remote_head = remote['stdout'].split()[0]
        checks = {'top': h.git(p, 'rev-parse', '--show-toplevel'),
                  'head': h.git(p, 'rev-parse', 'HEAD'),
                  'status': h.git(p, 'status', '--porcelain=v1', '--untracked-files=all', '--ignored'),
                  'ancestry': h.git(repo, 'merge-base', '--is-ancestor', head, remote_head)}
        references = h.proc_references(p)
        if (any(c['returncode'] for c in checks.values())
                or checks['top']['stdout'].strip() != str(p)
                or checks['head']['stdout'].strip() != head
                or checks['status']['stdout'] or references):
            report['held'].append({'path': str(p), 'checks': checks, 'process_references': references}); save(); continue
        op = {'repository': str(repo), 'path': str(p), 'branch': branch, 'head': head,
              'remote_main': remote_head, 'checks': checks, 'free_before': h.free()}
        report['operations'].append(op); save()
        op['remove'] = h.git(repo, 'worktree', 'remove', str(p))
        if op['remove']['returncode'] == 0:
            op['path_absent'] = not p.exists()
            if branch:
                op['delete_local_branch'] = h.git(h.OWNER if repo == root else repo, 'branch', '-d', branch.removeprefix('refs/heads/'))
        op['free_after'] = h.free(); save()
        print(json.dumps({'path': str(p), 'removed': op['remove']['returncode'] == 0}), flush=True)
    report['finished_at'] = h.now(); report['free_after'] = h.free()
    report['removed_count'] = sum(op['remove']['returncode'] == 0 for op in report['operations'])
    report['local_branches_removed'] = sum(op.get('delete_local_branch', {}).get('returncode') == 0 for op in report['operations'])
    save()
    print(json.dumps({k: report[k] for k in ['removed_count', 'local_branches_removed', 'free_before', 'free_after']}))


if __name__ == '__main__':
    main()
