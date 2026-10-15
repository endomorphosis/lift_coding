"""Remove three stale merged copies whose ignored files are caches/empty locks."""
import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cleanup_helpers', HERE / 'cleanup_root_worktrees.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
REPORT = HERE / 'root-cache-only-worktree-cleanup-results.json'
TARGETS = {'.doep-monitor-recovery', 'doep031-sealed-readmission-portfolio', 'pctdd-native-entry-1789010527'}


def main():
    if REPORT.exists():
        raise SystemExit('Existing mutation receipt: do not replay.')
    audit = json.loads((HERE / 'git-datasets-audit.json').read_text())['repositories']['root']
    remote = h.git(h.ROOT, 'ls-remote', 'origin', 'refs/heads/main')
    assert remote['returncode'] == 0
    main_head = remote['stdout'].split()[0]
    report = {'started_at': h.now(), 'remote_main': main_head, 'free_before': h.free(),
              'operations': [], 'held': [],
              'process_visibility_limit': 'Inaccessible/exited /proc entries do not establish absence; positive process references, locks and Git state fence each candidate.'}
    def save():
        REPORT.write_text(json.dumps(report, indent=2) + '\n')
    save()
    for w in audit['worktrees']:
        p = Path(w['path'])
        if p.name not in TARGETS:
            continue
        checks = {'top': h.git(p, 'rev-parse', '--show-toplevel'),
                  'head': h.git(p, 'rev-parse', 'HEAD'),
                  'status': h.git(p, 'status', '--porcelain=v1', '--untracked-files=all', '--ignored'),
                  'ancestry': h.git(h.ROOT, 'merge-base', '--is-ancestor', w['head'], main_head)}
        references = h.proc_references(p)
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit() or int(proc.name) == os.getpid():
                continue
            try:
                # Compare in memory; never disclose command lines or other arguments.
                if os.fsencode(str(p)) in (proc / 'cmdline').read_bytes():
                    references.append({'pid': int(proc.name), 'kind': 'command_path_reference', 'path': str(p)})
            except OSError:
                pass
        reasons = []
        ignored = []
        for line in checks['status']['stdout'].splitlines():
            if not line.startswith('!! '):
                reasons.append('Tracked or untracked changes'); continue
            rel = line[3:]
            parts = Path(rel).parts
            if '__pycache__' in parts or (parts and parts[0] in {'.pytest_cache', '.ruff_cache'}):
                ignored.append({'path': rel, 'kind': 'regenerable_cache'}); continue
            if rel.startswith('external/.') and rel.endswith('.bootstrap.lock'):
                lock = p / rel
                if not lock.is_symlink() and lock.is_file() and lock.stat().st_size == 0:
                    ignored.append({'path': rel, 'kind': 'empty_bootstrap_lock'}); continue
            reasons.append('Unknown ignored payload: ' + rel)
        if (any(c['returncode'] for c in checks.values())
                or checks['top']['stdout'].strip() != str(p)
                or checks['head']['stdout'].strip() != w['head']
                or w.get('locked_reason') or w.get('nested_registered_worktrees') or references or reasons):
            report['held'].append({'path': str(p), 'checks': checks, 'references': references, 'reasons': reasons}); save(); continue
        op = {'path': str(p), 'branch': w['branch'], 'head': w['head'], 'checks': checks,
              'ignored_custody': ignored, 'references': references, 'free_before': h.free()}
        report['operations'].append(op); save()
        op['remove'] = h.git(h.ROOT, 'worktree', 'remove', str(p))
        if op['remove']['returncode'] == 0:
            op['path_absent'] = not p.exists()
            op['delete_local_branch'] = h.git(h.OWNER, 'branch', '-d', w['branch'].removeprefix('refs/heads/'))
        op['free_after'] = h.free(); save()
        print(json.dumps({'path': str(p), 'removed': op['remove']['returncode'] == 0}), flush=True)
    report['finished_at'] = h.now(); report['free_after'] = h.free()
    report['removed_count'] = sum(o['remove']['returncode'] == 0 for o in report['operations'])
    report['local_branches_removed'] = sum(o.get('delete_local_branch', {}).get('returncode') == 0 for o in report['operations'])
    save()
    print(json.dumps({k: report[k] for k in ['removed_count', 'local_branches_removed', 'free_before', 'free_after']}))


if __name__ == '__main__':
    main()
