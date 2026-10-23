"""Recompute native T1 receipt arithmetic without importing project packages.

Usage: python reconcile_native_usage.py --output /a/new/result.json
Loads only the exact hash-reviewed, standard-library-only arithmetic module.
Never reads raw rollouts or starts a provider/runtime.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
ALLOWED = {'__future__', 'hashlib', 're', 'collections.abc', 'pathlib', 'typing'}

def read_verified(path, expected):
    p = Path(path).absolute()
    if p.resolve() != p or not p.is_relative_to('/home/barberb/lift_coding'):
        raise ValueError('Unexpected source root or symlink')
    if p.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('Evidence read bound exceeded')
    data = p.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Input differs from inspected bytes: ' + str(p))
    return data

def main():
    args = argparse.ArgumentParser()
    args.add_argument('--output', required=True, type=Path)
    target = args.parse_args().output
    recorded = json.loads((BASE / 'audit/native_usage_reconciliation.json').read_text())
    raw = read_verified(recorded['native_source_path'], recorded['native_source_sha256'])
    tree = ast.parse(raw)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(a.name in ALLOWED for a in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0 and node.module in ALLOWED
    module_name = 'offline_hash_reviewed_usage_arithmetic'
    spec = importlib.util.spec_from_file_location(module_name, recorded['native_source_path'])
    module = importlib.util.module_from_spec(spec)
    # Execute exact inspected bytes, avoiding a second unsynchronized source read.
    exec(compile(raw, recorded['native_source_path'], 'exec'), module.__dict__)
    results = []
    for arm in recorded['results']:
        receipt = json.loads(read_verified(arm['input_path'], arm['input_sha256']))
        invocations = receipt['trials'][0]['supervisor']['provider_invocations']
        projection = module.reconcile_router_cumulative_usage(invocations)
        if projection != arm['projection']:
            raise ValueError('Fresh arithmetic differs from retained audit projection')
        results.append({**arm, 'projection': projection})
    result = {**recorded, 'results': results, 'reproduction_matches': True}
    with target.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    target.chmod(0o600)
    print(json.dumps({'matched': True, 'arms': len(results), 'output': str(target)}))

if __name__ == '__main__':
    os.umask(0o077)
    main()
