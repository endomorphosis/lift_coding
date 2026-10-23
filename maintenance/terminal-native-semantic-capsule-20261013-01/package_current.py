"""Explicit public source packaging and isolated patch application checks."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

U = Path(__file__).resolve().parent
C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
os.umask(0o077)
baseline = json.loads((U / 'baseline-manifest.json').read_bytes())
package = U / 'review-package'
assert not package.exists()
package.mkdir(mode=0o700)
source_pins = []
def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
for item in baseline['new_sources']:
    source = Path(item['path'])
    assert source.is_file() and source.stat().st_mode & 0o777 == 0o644
    relative = source.relative_to(C)
    target = package / relative
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.write_bytes(source.read_bytes()); target.chmod(0o600)
    source_pins.append({'source': pin(source), 'packaged': pin(target), 'relative_path': str(relative)})
def git(args, directory):
    return subprocess.run(['git', *args], cwd=directory, check=True, timeout=20, capture_output=True).stdout
git(['init', '--quiet'], package)
git(['add', '--', *(item['relative_path'] for item in source_pins)], package)
patch = git(['diff', '--cached', '--binary', '--full-index', '--no-ext-diff'], package)
(U / 'stage-w.patch').write_bytes(patch); (U / 'stage-w.patch').chmod(0o600)
empty = U / 'patch-validation'; empty.mkdir(mode=0o700)
# An independent repository avoids an ancestor repository's subdirectory
# filtering silently skipping a patch with paths outside that prefix.
git(['init', '--quiet'], empty)
git(['apply', '--check', str(U / 'stage-w.patch')], empty)
git(['apply', str(U / 'stage-w.patch')], empty)
for item in source_pins:
    assert (empty / item['relative_path']).read_bytes() == Path(item['source']['path']).read_bytes()
report = {'schema': 'terminal-native-semantic-package@1', 'source_count': len(source_pins),
    'files': source_pins, 'patch': pin(U / 'stage-w.patch'), 'patch_check_passed': True,
    'patch_exact_apply_passed': True, 'commits_created': 0, 'pushes': 0,
    'original_repository_index_written': False, 'sealed_predecessor_mutated': False}
(U / 'package-report.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
(U / 'package-report.json').chmod(0o600)
print(json.dumps({'source_count': len(source_pins), 'patch_bytes': len(patch), 'patch_check_passed': True}))
