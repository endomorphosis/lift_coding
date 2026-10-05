"""Freeze bounded publication argv and already observed, regular input bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path('/home/barberb/lift_coding')
S = ROOT / 'maintenance/ranker-convergence-publication-20261005-01'
R = ROOT / 'maintenance/ranker-convergence-publication-root-20261005-01'
P = ROOT / 'maintenance/ranker-convergence-publication-package-20261005-01'
HF = ROOT / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
EXPECTED_CLOSURE = '3721e16edddb301d9832001995fb9e685226cb9665852b31732bb148f8e7cdab'

def pin(path):
    path = Path(path).absolute()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode), str(path)
        digest = hashlib.sha256()
        total = 0
        while block := os.read(fd, 8 * 1024 ** 2):
            digest.update(block)
            total += len(block)
        after = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        assert identity(before) == identity(after) == identity(path.stat())
        return {'path': str(path), 'bytes': total, 'sha256': digest.hexdigest()}
    finally:
        os.close(fd)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('package', 'package-review'))
    parser.add_argument('--input-review-receipt', type=Path, required=True)
    parser.add_argument('--expected-input-review-sha256', required=True)
    args = parser.parse_args()
    receipt_pin = pin(args.input_review_receipt)
    assert receipt_pin['sha256'] == args.expected_input_review_sha256
    receipt = json.loads(args.input_review_receipt.read_bytes())
    assert receipt['status'] == 'passed_file_only_final_publication_input_review', receipt['status']
    assert not receipt.get('issues', []), 'independent review issues'
    closure = pin(S / 'closed-inputs.json')
    assert closure['sha256'] == EXPECTED_CLOSURE
    previous = json.loads((ROOT / 'maintenance/ranker-curvature-publication-root-20261005-01/package-invocation-01.json').read_bytes())
    expected = {x['path']: {k: x[k] for k in ('path', 'bytes', 'sha256')} for x in previous['pinned_inputs']}
    selected = json.loads((S / 'final-selection.json').read_bytes())
    for item in selected['files']:
        descriptor = {k: item[k] for k in ('path', 'bytes', 'sha256')}
        if descriptor['path'] in expected:
            assert expected[descriptor['path']] == descriptor
        expected[descriptor['path']] = descriptor
    for path in (S / 'closed-inputs.json', S / 'plan.json', S / 'final-selection.json',
                 Path(__file__), args.input_review_receipt,
                 args.input_review_receipt.parent / 'review_inputs.py',
                 HF / 'run_frozen_publication_phase.py'):
        expected[str(path.absolute())] = pin(path)
    if args.phase == 'package':
        assert not P.exists(), 'package output must be new'
        argv = ['/usr/bin/python3.12', '-B', str(S / 'build_package.py'), '--closed-inputs',
                closure['path'], '--expected-closed-inputs-sha256', closure['sha256'], '--output', str(P)]
    else:
        package_closure = json.loads((P / 'closed.json').read_bytes())
        assert package_closure['status'] == 'passed_local_frozen_package'
        manifest_pin = pin(P / 'package/manifest.json')
        assert manifest_pin == package_closure['manifest']
        manifest = json.loads(Path(manifest_pin['path']).read_bytes())
        for item in manifest['data_shards']:
            descriptor = pin(item['path'])
            assert descriptor['bytes'] == item['bytes'] and descriptor['sha256'] == item['sha256']
            expected[descriptor['path']] = descriptor
        expected[manifest_pin['path']] = manifest_pin
        expected[str(P / 'closed.json')] = pin(P / 'closed.json')
        argv = ['/usr/bin/python3.12', '-B', str(S / 'review_package.py'), '--closed-inputs',
                closure['path'], '--expected-closed-inputs-sha256', closure['sha256'],
                '--manifest', manifest_pin['path'], '--expected-manifest-sha256', manifest_pin['sha256'],
                '--expected-builder-sha256', expected[str(S / 'build_package.py')]['sha256'],
                '--output', str(P / 'package-review-01.json')]
    observed = [pin(path) for path in sorted(expected)]
    assert observed == [expected[x] for x in sorted(expected)], 'publication or protected input drift'
    invocation = {'schema': 'terminal-ir-frozen-publication-phase-invocation@1',
                  'phase': 'ranker-convergence-' + args.phase + '-01',
                  'remote_mutation_scope': 'none_local_bounded_archive_and_review_only',
                  'argv': argv, 'cwd': str(ROOT), 'wall_seconds': 180, 'pinned_inputs': observed,
                  'proof_authority': False, 'execution_authority': False,
                  'completion_authority': False, 'planner_activation': False}
    target = R / (args.phase + '-invocation-01.json')
    with target.open('xb') as stream:
        stream.write((json.dumps(invocation, sort_keys=True, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'invocation': pin(target), 'pinned_input_count': len(observed),
                      'pinned_input_bytes': sum(x['bytes'] for x in observed)}, sort_keys=True))

if __name__ == '__main__':
    main()
