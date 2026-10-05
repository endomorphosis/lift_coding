"""Scan every exact new upload file with the previously qualified classifier."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import types

ROOT = Path(__file__).resolve().parent
HF = ROOT.parent / 'terminal-ir-publication-20261004-01/huggingface'
HELPERS = {
    'archive': (HF / 'build_evidence_archive_02.py', 'f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036'),
    'classifier': (HF / 'classify_and_prepare_public_archive_07.py', 'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8')}

def pin(path):
    path = Path(path).absolute()
    assert path.resolve(strict=True) == path and not path.is_symlink()
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
    assert identity(before) == identity(after) and len(raw) == before.st_size
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def load(name):
    path, expected = HELPERS[name]
    descriptor = pin(path)
    assert descriptor['sha256'] == expected
    raw = path.read_bytes()
    assert len(raw) == descriptor['bytes'] and hashlib.sha256(raw).hexdigest() == descriptor['sha256']
    module = types.ModuleType('held_convergence_upload_' + name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module

def main():
    if not __debug__:
        raise RuntimeError('optimized Python would disable scan gates')
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-plan-sha256', required=True)
    parser.add_argument('--expected-files', required=True, type=int)
    args = parser.parse_args()
    own = pin(__file__)
    plan_path = ROOT / 'hf-plan-01.json'
    plan_pin = pin(plan_path)
    assert plan_pin['sha256'] == args.expected_plan_sha256
    plan_raw = plan_path.read_bytes()
    assert len(plan_raw) == plan_pin['bytes'] and hashlib.sha256(plan_raw).hexdigest() == plan_pin['sha256']
    plan = json.loads(plan_raw)
    assert plan['schema'] == 'terminal-ir-successor-evidence-publication-plan@1'
    assert plan['expected_parent_commit'] == '8b7b8c896749e0ca3884114cedbed782a88f4702'
    expected = [row['local'] for row in plan['files']]
    assert 0 < len(expected) == args.expected_files <= 100
    assert all(pin(row['path']) == row for row in expected)
    archive, classifier = load('archive'), load('classifier')
    scanner = archive.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in archive.PATTERNS if name != 'private_key_pem']
    budget = classifier.Budget(seconds=180, decoded_bytes=1024 ** 3,
                               container_bytes=16 * 1024 ** 2, members=10000, depth=6)
    rows = []
    with tempfile.TemporaryDirectory(prefix='convergence-final-upload-scan-', dir=ROOT) as directory:
        for item in plan['files']:
            inspection = classifier.Classifier(scanner, budget, Path(directory))
            with Path(item['local']['path']).open('rb') as stream:
                inspection.inspect(stream)
            assert not inspection.hits, 'selected upload rejected by credential/container classifier'
            rows.append({'remote': item['remote'], 'local': item['local'],
                         'scan_counts': dict(inspection.counts), 'candidate_hits': 0})
    budget.check()
    assert pin(plan_path) == plan_pin and pin(__file__) == own
    assert all(pin(row['path']) == row for row in expected)
    for path, expected_sha in HELPERS.values():
        assert pin(path)['sha256'] == expected_sha
    result = {'schema': 'ranker-convergence-exact-final-upload-scan@1', 'status': 'passed',
              'plan': plan_pin, 'scanner': own, 'files': rows, 'selected_files': len(rows),
              'selected_bytes': sum(row['local']['bytes'] for row in rows), 'candidate_hits': 0,
              'aggregate_decoded_bytes': budget.decoded, 'recursive_members': budget.members,
              'bounded_complete_container_and_PEM_scan': True, 'exact_available_cached_credential_veto': True,
              'universal_secret_free_claim': False, 'remote_mutations': 0, 'new_native_qualification_jobs': 0,
              'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
              'helper_pins': {name: pin(path) for name, (path, _) in HELPERS.items()}}
    output = ROOT / 'final-upload-scan-01.json'
    with output.open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'receipt': pin(output), 'selected_files': len(rows), 'candidate_hits': 0,
                      'aggregate_decoded_bytes': budget.decoded}))

if __name__ == '__main__':
    main()
