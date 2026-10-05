"""Freeze the final upload scan or authorized single-parent HF publication."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path('/home/barberb/lift_coding')
R = Path(__file__).resolve().parent
S = ROOT / 'maintenance/ranker-convergence-publication-20261005-01'
HF = ROOT / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
PARENT = '8b7b8c896749e0ca3884114cedbed782a88f4702'

def pin(path):
    path = Path(path).absolute()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode)
        digest = hashlib.sha256()
        size = 0
        while block := os.read(fd, 8 * 1024 ** 2):
            digest.update(block)
            size += len(block)
        identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
        assert identity(before) == identity(os.fstat(fd)) == identity(path.stat())
        return {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}
    finally:
        os.close(fd)

def load(path, expected=None):
    path = Path(path)
    before = pin(path)
    raw = path.read_bytes()
    assert len(raw) == before['bytes'] and hashlib.sha256(raw).hexdigest() == before['sha256']
    if expected is not None:
        assert before == expected
    return json.loads(raw)

def main():
    if not __debug__:
        raise RuntimeError('optimized Python would disable frozen publication gates')
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('final-upload-scan', 'hf-publication'))
    parser.add_argument('--expected-plan-sha256', required=True)
    args = parser.parse_args()
    plan_pin = pin(R / 'hf-plan-01.json')
    assert plan_pin['sha256'] == args.expected_plan_sha256
    plan = load(plan_pin['path'], plan_pin)
    assert plan['expected_parent_commit'] == PARENT
    assert 0 < len(plan['files']) <= 100
    outer = load(R / 'package-review-outer-02/closed.json')
    assert outer['status'] == 'closed_phase' and outer['returncode'] == 0 and outer['input_pins_unchanged']
    assert outer['cleanup_errors'] == []
    package_review = load(S / 'package-review-01.json')
    assert package_review['status'] == 'passed'
    previous = load(R / 'package-review-invocation-02.json')
    expected = {x['path']: x for x in previous['pinned_inputs']}
    for item in plan['files']:
        descriptor = item['local']
        if descriptor['path'] in expected:
            assert expected[descriptor['path']] == descriptor
        expected[descriptor['path']] = descriptor
    own = pin(__file__)
    for path in (R / 'hf-plan-01.json', R / 'prepare_hf_plan_01.py', R / 'scan_final_upload_01.py',
                 S / 'package-review-01.json', R / 'package-review-outer-01/closed.json',
                 R / 'package-review-outer-02/closed.json', HF / 'run_frozen_publication_phase.py',
                 HF / 'publish_successor_evidence_02.py', Path(__file__)):
        descriptor = pin(path)
        expected[descriptor['path']] = descriptor
    assert expected[str(HF / 'run_frozen_publication_phase.py')]['sha256'] == '8d9955df76155f75326fdda8039119bacab9bad3ca71306f241be9b2124d01b8'
    assert expected[str(HF / 'publish_successor_evidence_02.py')]['sha256'] == '670e064a8222ce1b0c962e202985974741a9a4476630b0541c7ec880b32009f2'
    if args.phase == 'final-upload-scan':
        argv = ['/usr/bin/python3.12', '-B', str(R / 'scan_final_upload_01.py'),
                '--expected-plan-sha256', plan_pin['sha256'], '--expected-files', str(len(plan['files']))]
        scope = 'none_complete_local_upload_scan_only'
        wall = 180
    else:
        scan_pin = pin(R / 'final-upload-scan-01.json')
        scan = load(scan_pin['path'], scan_pin)
        assert scan['status'] == 'passed' and scan['candidate_hits'] == 0 and scan['plan'] == plan_pin
        assert scan['selected_files'] == len(plan['files'])
        scan_outer = load(R / 'final-upload-scan-outer-01/closed.json')
        assert scan_outer['status'] == 'closed_phase' and scan_outer['returncode'] == 0 and scan_outer['input_pins_unchanged']
        for path in (R / 'final-upload-scan-01.json', R / 'final-upload-scan-outer-01/closed.json'):
            descriptor = pin(path)
            expected[descriptor['path']] = descriptor
        assert not (R / 'hf-publication-01').exists()
        argv = ['/usr/bin/env', 'HF_HUB_DISABLE_XET=1', 'HF_HUB_ENABLE_HF_TRANSFER=0',
                '/home/barberb/.local/bin/python', '-B', str(HF / 'publish_successor_evidence_02.py'),
                '--plan', plan_pin['path'], '--expected-plan-sha256', plan_pin['sha256'],
                '--expected-parent-commit', PARENT, '--output', str(R / 'hf-publication-01')]
        scope = 'authorized_single_CAS_successor_commit_Publicus_codebase_ir_proof_index_only'
        wall = 900
    observed = [pin(path) for path in sorted(expected)]
    assert observed == [expected[x] for x in sorted(expected)], 'frozen or protected input drift'
    assert pin(__file__) == own
    invocation = {'schema': 'terminal-ir-frozen-publication-phase-invocation@1',
                  'phase': 'ranker-convergence-' + args.phase + '-01', 'remote_mutation_scope': scope,
                  'argv': argv, 'cwd': str(ROOT), 'wall_seconds': wall, 'pinned_inputs': observed,
                  'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
                  'planner_activation': False}
    target = R / (args.phase + '-invocation-01.json')
    with target.open('xb') as stream:
        stream.write((json.dumps(invocation, sort_keys=True, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'invocation': pin(target), 'selected_files': len(plan['files']),
                      'pinned_inputs': len(observed)}, sort_keys=True))

if __name__ == '__main__':
    main()
