#!/usr/bin/env python3
"""Check preserved artifacts and applicability without changing source indexes."""
import base64
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
OUT = Path(__file__).resolve().parent
manifest = json.loads((OUT / 'manifest.json').read_text())
checks = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


for artifact in manifest['outputs']:
    raw = (OUT / artifact['path']).read_bytes()
    assert len(raw) == artifact['bytes'] and sha(raw) == artifact['sha256']
    checks.append({'artifact': artifact['path'], 'hash_and_size': True})
for repo in manifest['repositories']:
    source = ROOT / repo['source_path']
    with tempfile.TemporaryDirectory(prefix='.verify-index-', dir=OUT) as temporary:
        environment = dict(os.environ, GIT_INDEX_FILE=str(Path(temporary) / 'index'))
        subprocess.run(['git', '-C', str(source), 'read-tree', repo['base_commit']], env=environment, capture_output=True, check=True)
        subprocess.run(['git', '-C', str(source), 'apply', '--cached', '--check', str(OUT / (repo['name'] + '.patch'))], env=environment, capture_output=True, check=True)
    checks.append({'repository': repo['name'], 'patch_applies_to_exact_base': True})
    for file in repo['files']:
        before = subprocess.check_output(['git', '-C', str(source), 'show', repo['base_commit'] + ':' + file['path']])
        after = (source / file['path']).read_bytes()
        assert sha(before) == file['base_sha256'] and sha(after) == file['result_sha256']
        checks.append({'repository': repo['name'], 'path': file['path'], 'base_and_retained_result_hashes': True})
        if file['preservation'].endswith('.byte-edits.json'):
            recipe = json.loads((OUT / file['preservation']).read_text())
            assert sha(before) == recipe['base_sha256']
            rebuilt = before
            for edit in reversed(recipe['edits']):
                offset = edit['offset']
                rebuilt = rebuilt[:offset] + base64.b64decode(edit['insert_base64']) + rebuilt[offset + edit['delete_bytes']:]
            assert rebuilt == after and sha(rebuilt) == recipe['result_sha256']
            checks.append({'repository': repo['name'], 'path': file['path'], 'secret_free_recipe_exact_reconstruction': True})
result = {'schema': 'third-party-preservation-verification/v1', 'checks_passed': len(checks),
          'source_repository_indexes_modified': False, 'source_worktrees_modified': False,
          'model_or_behavioral_execution': False, 'checks': checks}
print(json.dumps(result, indent=2, sort_keys=True))
