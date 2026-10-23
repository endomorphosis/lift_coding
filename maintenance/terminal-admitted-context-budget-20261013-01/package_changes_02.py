"""Package only nine explicit reviewed Python changes; leave source index alone."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

A = Path(__file__).resolve().parent
C = A / 'checkout'
OUT = A / 'review-package-02'
os.umask(0o077)
OUT.mkdir(mode=0o700)
MODIFIED = [
    'benchmarks/agent_supervisor/container_coding/container_worker_deployment.py',
    'ipfs_accelerate_py/agent_supervisor/entrypoints/admitted_benchmark_runtime.py',
    'ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py',
    'ipfs_accelerate_py/agent_supervisor/todo_daemon/supervisor_runtime.py',
]
NEW = [
    'ipfs_accelerate_py/agent_supervisor/runtime/checked_context_dispatch.py',
    'ipfs_accelerate_py/agent_supervisor/runtime/checked_observer_budget.py',
    'test/api/test_checked_context_dispatch.py',
    'test/api/test_checked_context_native_integration.py',
    'test/api/test_checked_observer_budget.py',
]

def run(args, cwd=C):
    return subprocess.run(args, cwd=cwd, capture_output=True, check=True)

def pin(p):
    raw = p.read_bytes()
    return {'path': str(p), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

before_index = pin(C / '.git/index')
base = run(['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
patch = run(['git', 'diff', '--binary', 'HEAD', '--', *MODIFIED]).stdout
for rel in NEW:
    r = subprocess.run(['git', 'diff', '--no-index', '--binary', '--', '/dev/null', rel], cwd=C, capture_output=True)
    assert r.returncode == 1 and not r.stderr
    patch += r.stdout
patch_path = OUT / 'change.patch'
patch_path.write_bytes(patch)
scratch = OUT / 'apply-check'
scratch.mkdir(mode=0o700)
sources = []
for rel in MODIFIED + NEW:
    p = C / rel
    current = p.read_bytes()
    record = {'relative_path': rel, 'new': rel in NEW, 'current': pin(p),
              'source_mode': oct(stat.S_IMODE(p.stat().st_mode))}
    assert not p.stat().st_mode & 0o111
    if rel in MODIFIED:
        old = run(['git', 'show', 'HEAD:' + rel]).stdout
        q = scratch / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_bytes(old)
        q.chmod(0o644)
        record['baseline'] = {'bytes': len(old), 'sha256': hashlib.sha256(old).hexdigest()}
    sources.append(record)
run(['git', 'init', '-q'], scratch)
run(['git', 'add', '--all'], scratch)
run(['git', '-c', 'user.name=AA review fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'Exact four source bases'], scratch)
run(['git', 'apply', '--check', str(patch_path)], scratch)
run(['git', 'apply', str(patch_path)], scratch)
for row in sources:
    p = scratch / row['relative_path']
    assert p.read_bytes() == (C / row['relative_path']).read_bytes()
    assert not p.stat().st_mode & 0o111
    row['applied'] = pin(p)
run(['git', 'diff', '--check'], scratch)
assert pin(C / '.git/index') == before_index
assert run(['git', 'rev-parse', 'HEAD']).stdout.decode().strip() == base
report = {'schema': 'terminal-admitted-context-source-review-package@1', 'qualified': True,
          'base_commit': base, 'files': len(sources), 'modified': len(MODIFIED), 'new': len(NEW),
          'patch': pin(patch_path), 'sources': sources, 'exact_scratch_application': True, 'git_executable_modes_match': True, 'full_permission_bits_preserved_by_git_claimed': False,
          'source_index_unchanged': True, 'source_index_pin': before_index,
          'production_promoted': False, 'project_pushes': 0,
          'scope': 'Isolated source/test patch over the AA source projection. No private runtime artifacts or Git metadata in the patch.'}
(A / 'review-package-02.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
print(json.dumps({'qualified': True, 'files': len(sources), 'patch': pin(patch_path)}))
