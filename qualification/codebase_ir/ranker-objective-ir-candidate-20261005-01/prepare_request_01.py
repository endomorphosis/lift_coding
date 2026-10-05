"""Freeze the additive objective-scalar request without executing target code.

All previous qualification files remain guarded. This producer permits no new
fits, feature preparation, ranker evaluation, or training replay. Native proof
limits and resource policy are inherited exactly from the qualified request.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.with_name('ranker-source-semantics-20261005-01')


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read_pin(path, *, capture=False):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode), 'regular source required')
        if capture:
            need(before.st_size <= 32 * 1024**2, 'JSON capture exceeded cap')
        blocks, total, digest = [], 0, hashlib.sha256()
        while block := os.read(fd, 1024**2):
            total += len(block)
            need(total <= before.st_size, 'input grew during read')
            digest.update(block)
            if capture:
                blocks.append(block)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda info: tuple(getattr(info, name) for name in fields)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and total == before.st_size, 'input changed during read')
        return b''.join(blocks), {'path': str(path), 'bytes': total, 'sha256': digest.hexdigest()}
    finally:
        os.close(fd)


def load(path, expected_sha):
    raw, descriptor = read_pin(path, capture=True)
    need(descriptor['sha256'] == expected_sha, 'parsed bytes differ from expected digest')
    return json.loads(raw), descriptor


def guards(qualified):
    workspace = ROOT.parents[2]
    result = {}
    for role, cwd in (('root', workspace), ('child', workspace / 'external/ipfs_accelerate')):
        expected = qualified['original_checkout_guards'][role]
        head = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', 'rev-parse', 'HEAD'], cwd=cwd, text=True).strip()
        index = read_pin(Path(expected['index']['path']))[1]
        need(head == expected['head'] and index == expected['index'], 'original checkout changed')
        result[role] = {'head': head, 'index': index}
    return result


def main():
    request, request_pin = load(PRIOR / 'preparation/request-v3.json', '4858034f642fcedd31d7b243d65156eade84332e8401578df12e0c8f30c30861')
    seal, seal_pin = load(PRIOR / 'file-only-seal-01.json', '21a459ac9bfcf399132943708e32445c93cb66fa0fab8fb2878beeb01dcf8b65')
    qualified, review_pin = load(PRIOR / 'qualified-review-01.json', '39c403afd19b5972a28281813c23fdd13eddea1c32fa63747b4dd3258b07e550')
    need(qualified['status'] == 'passed' and seal['review'] == review_pin and seal['regular_file_count'] == len(seal['files']) == 299,
         'qualified prior review/seal join required')
    before = guards(qualified)
    strict = {row['path']: row for row in request['strict_old_inputs']}
    need(len(strict) == len(request['strict_old_inputs']) == 1808, 'unique inherited guard population required')
    for row in [*seal['files'], seal_pin]:
        need(row['path'] not in strict or strict[row['path']] == row, 'overlapping old descriptor differs')
        strict[row['path']] = row
    for row in [*strict.values(), *request['protected_live_sources']]:
        need(read_pin(Path(row['path']))[1] == row, 'old protected descriptor changed')
    readback, readback_pin = load(Path(qualified['native_metadata_readback']['path']), qualified['native_metadata_readback']['sha256'])
    need(readback_pin == qualified['native_metadata_readback'], 'metadata readback descriptor differs')
    metadata_pin = readback['metadata_inputs']
    metadata, actual_metadata = load(Path(metadata_pin['path']), metadata_pin['sha256'])
    need(actual_metadata == metadata_pin and len(metadata) == 32 and sum(map(len, metadata.values())) == 4440, 'prior hydrated metadata differs')
    need(request['proof_limits'] == {'wall_seconds': 20, 'cpu_seconds': 20, 'output_bytes': 65536, 'workspace_bytes': 16777216} and
         request['root_request'] == {'cpu_slots': 1, 'memory_mb': 2048, 'child_process_slots': 4} and
         request['proof_pressure_limits'] == {'memory_percent': 2.0, 'cpu_percent': 50.0, 'io_percent': 10.0},
         'native proof and resource limits must remain unchanged')
    new_request = dict(request)
    new_request.update(
        schema='terminal-ranker-objective-scalar-IR-request@1',
        strict_old_inputs=[strict[name] for name in sorted(strict)],
        prior_metadata_inputs=metadata_pin,
        prior_source_slice_seal=seal_pin, prior_source_slice_review=review_pin,
        prior_source_slice_request=request_pin,
        new_proof_scope='Generic partial exact-real scalar compiler; pinned stable-loss and sign-split probability leaves only',
        forbidden_operations=['ranker_import', 'feature_prepare', 'ranker_fit', 'autoencoder_fit', 'native_ranker_objective',
                              'native_ranker_dot', 'trace_replay', 'optimizer_update'],
        objective_source_equivalence_proved=False, gradient_source_equivalence_proved=False,
        source_interpreter_semantics_proved=False, full_source_runtime_equivalence=False,
        binary64_error_bound_proved=False, native_Float_optimizer_convergence_proved=False,
        global_autoencoder_convergence_proved=False, full_task_satisfaction='unknown', planner_activation=False,
        official_benchmark_score=None, proof_authority=False, execution_authority=False, completion_authority=False,
    )
    for path, descriptor in ((PRIOR / 'preparation/request-v3.json', request_pin), (PRIOR / 'file-only-seal-01.json', seal_pin),
                             (PRIOR / 'qualified-review-01.json', review_pin), (Path(readback_pin['path']), readback_pin),
                             (Path(metadata_pin['path']), metadata_pin)):
        need(read_pin(path)[1] == descriptor, 'parsed input changed before request closure')
    need(guards(qualified) == before, 'original checkout changed during preparation')
    (ROOT / 'preparation').mkdir(exist_ok=True)
    (ROOT / 'evidence').mkdir(exist_ok=True)
    target = ROOT / 'preparation/request-v3.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(new_request, sort_keys=True, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': 'prepared_file_only', 'request': read_pin(target)[1], 'strict_old_inputs': len(strict),
                      'protected_live_sources': len(request['protected_live_sources']), 'native_jobs': 0, 'target_imports': 0}))


if __name__ == '__main__':
    main()
