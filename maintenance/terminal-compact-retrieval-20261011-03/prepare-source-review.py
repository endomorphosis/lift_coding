"""Create a patch against this continuation's captured public source bytes."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

G = Path(__file__).parent
CHECKOUT = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
baseline = json.loads((G / 'baseline-manifest.json').read_text())
paths = {row['path'] for row in baseline['files']}
paths.update(('ipfs_accelerate_py/agent_supervisor/runtime/code_retrieval_wire_delivery.py',
              'test/api/test_code_retrieval_wire_delivery.py',
              'test/api/test_router_materialized_retrieval.py'))
patch_parts, changed = [], []
for relative in sorted(paths):
    original = G / 'baseline' / relative
    current = CHECKOUT / relative
    before = original.read_bytes() if original.exists() else b''
    after = current.read_bytes()
    if before == after:
        continue
    if relative.endswith('.py'):
        ast.parse(after, filename=relative)
    patch_parts.extend(difflib.unified_diff(before.decode().splitlines(keepends=True),
        after.decode().splitlines(keepends=True), fromfile='a/' + relative if original.exists() else '/dev/null',
        tofile='b/' + relative))
    changed.append({'path': relative, 'before_sha256': hashlib.sha256(before).hexdigest() if original.exists() else None,
        'sha256': hashlib.sha256(after).hexdigest(), 'bytes': len(after), 'absent_before': not original.exists()})
patch = G / 'changes.patch'
patch.write_text(''.join(patch_parts))
with tempfile.TemporaryDirectory(prefix='wire-review-') as directory:
    temporary = Path(directory)
    shutil.copytree(G / 'baseline', temporary, dirs_exist_ok=True)
    subprocess.run(['/usr/bin/git', 'apply', '--check', str(patch)], cwd=temporary, check=True, capture_output=True)
    subprocess.run(['/usr/bin/git', 'apply', str(patch)], cwd=temporary, check=True, capture_output=True)
    for row in changed:
        assert (temporary / row['path']).read_bytes() == (CHECKOUT / row['path']).read_bytes()
receipt = {'schema': 'materialized-wire-source-review-manifest@1', 'checkout': str(CHECKOUT),
    'patch_basis': 'Exact source bytes captured at the beginning of this continuation, including older dirty overlays.',
    'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(), 'patch_bytes': patch.stat().st_size,
    'patch_applies_cleanly_to_captured_baseline': True, 'applied_changed_bytes_match_checkout': True,
    'all_changed_python_syntax_checked': True, 'original_dirty_checkout_or_git_index_mutated': False, 'files': changed}
(G / 'source-manifest.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps({'changed_files': len(changed), 'patch_bytes': receipt['patch_bytes'],
    'patch_sha256': receipt['patch_sha256'], 'scratch_apply_check': True}), flush=True)
