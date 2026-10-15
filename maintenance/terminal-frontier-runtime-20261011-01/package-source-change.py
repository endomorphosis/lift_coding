"""Save only this turn's changes against explicitly captured pre-edit bytes."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

p = Path(__file__).parent
checkout = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
relative = Path('benchmarks/agent_supervisor/container_coding')
initial = {r['path']: r for r in json.loads((p / 'baseline.json').read_text())['files']}
audit = {r['path']: r for r in json.loads((p / 'audit-baseline.json').read_text())['files']}
cache_file = Path('/home/barberb/lift_coding/maintenance/terminal-bounded-context-20261011-01/deployment-cache-baseline.json')
cache = {str(Path(r['path']).relative_to(checkout)): r for r in json.loads(cache_file.read_text())['files']}
names = ['terminal_deployment.py', 'test_terminal_deployment.py', 'terminal_context_audit.py',
         'test_terminal_context_audit.py', 'SUPERVISION_INTEGRATION.md']
rows, patch = [], []
for name in names:
    key = (relative / name).as_posix()
    path = checkout / key
    baseline = p / 'baseline' / key
    if key in initial:
        before_record = initial[key]
    elif key in audit:
        before_record = audit[key]
        baseline.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(before_record['snapshot'], baseline)
    else:
        before_record = cache[key]
        baseline.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(before_record['baseline'], baseline)
    before, after = baseline.read_bytes(), path.read_bytes()
    assert hashlib.sha256(before).hexdigest() == before_record['sha256']
    assert before != after
    rows.append({'path': key, 'before_sha256': hashlib.sha256(before).hexdigest(),
        'after_sha256': hashlib.sha256(after).hexdigest(), 'before_bytes': len(before), 'after_bytes': len(after)})
    patch.extend(difflib.unified_diff(before.decode().splitlines(keepends=True), after.decode().splitlines(keepends=True),
        fromfile='a/' + key, tofile='b/' + key))
(p / 'changes.patch').write_text(''.join(patch))
(p / 'source-manifest.json').write_text(json.dumps({'schema': 'terminal-frontier-runtime-source-change@1',
    'checkout': str(checkout), 'baseline_basis': 'Captured bytes before this turn; not repository HEAD',
    'files': rows, 'patch_sha256': hashlib.sha256((p / 'changes.patch').read_bytes()).hexdigest()}, indent=2, sort_keys=True) + '\n')
print(json.dumps({'changed_files': len(rows), 'patch_bytes': (p / 'changes.patch').stat().st_size}), flush=True)
