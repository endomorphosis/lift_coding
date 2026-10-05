"""Read-only inherited guard verification and one new source-slice request."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.with_name('ranker-real-convergence-20261005-01')

def pin(path):
    path = Path(path).absolute()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode)
        digest = hashlib.sha256()
        total = 0
        while block := os.read(fd, 8 * 1024 ** 2):
            digest.update(block)
            total += len(block)
        identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
        assert identity(before) == identity(os.fstat(fd)) == identity(path.stat())
        return {'path': str(path), 'bytes': total, 'sha256': digest.hexdigest()}
    finally:
        os.close(fd)

def load(path, expected):
    assert pin(path)['sha256'] == expected
    raw = Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    return json.loads(raw)

def main():
    if not __debug__:
        raise RuntimeError('optimized Python would disable request guards')
    prior_request = load(PRIOR / 'preparation/request-v3.json', '1d7d6efb49bb951d0cf2470d8b93d79a73e25cbd42961624ca263ee40314e458')
    seal = load(PRIOR / 'file-only-seal-01.json', '6ee7b5d675777e8cc9744c9072ee7f885cb8fc47a9204c1a40d9724632012648')
    qualified = load(PRIOR / 'qualified-review-01.json', 'eebf40b5de2822faef1293a62578da208b582131e44c8a1f3e0d060071b6d0e7')
    strict = {x['path']: x for x in prior_request['strict_old_inputs']}
    for descriptor in [*seal['files'], pin(PRIOR / 'file-only-seal-01.json')]:
        if descriptor['path'] in strict:
            assert strict[descriptor['path']] == descriptor
        strict[descriptor['path']] = descriptor
    for descriptor in strict.values():
        assert pin(descriptor['path']) == descriptor
    for descriptor in prior_request['protected_live_sources']:
        assert pin(descriptor['path']) == descriptor
    workspace = ROOT.parents[2]
    for role, cwd in (('root', workspace), ('child', workspace / 'external/ipfs_accelerate')):
        guard = qualified['original_checkout_guards'][role]
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd, text=True).strip() == guard['head']
        assert pin(guard['index']['path']) == guard['index']
    metadata = pin(PRIOR / 'evidence/metadata-convergence-01/metadata-inputs.json')
    assert metadata['sha256'] == 'c0f5ab88db02ff6b59d36f5dbce63c99a8fc09414f2eedbab6c4116241881f41'
    assert sum(map(len, load(metadata['path'], metadata['sha256']).values())) == 4417
    request = dict(prior_request)
    request.update(schema='terminal-ranker-supported-source-slices-request@1',
                   strict_old_inputs=[strict[name] for name in sorted(strict)],
                   prior_metadata_inputs=metadata,
                   prior_convergence_seal=pin(PRIOR / 'file-only-seal-01.json'),
                   prior_convergence_review=pin(PRIOR / 'qualified-review-01.json'),
                   new_proof_scope='Typed arithmetic compiler and exact-real finite-list dot/update AST slices only',
                   forbidden_operations=['ranker_import', 'feature_prepare', 'ranker_fit', 'autoencoder_fit',
                                         'native_ranker_objective', 'native_ranker_dot', 'trace_replay', 'optimizer_update'],
                   source_interpreter_semantics_proved=False, full_source_runtime_equivalence=False,
                   binary64_error_bound_proved=False, native_Float_optimizer_convergence_proved=False,
                   global_autoencoder_convergence_proved=False, full_task_satisfaction='unknown',
                   planner_activation=False, official_benchmark_score=None,
                   proof_authority=False, execution_authority=False, completion_authority=False)
    (ROOT / 'preparation').mkdir(exist_ok=True)
    (ROOT / 'evidence').mkdir(exist_ok=True)
    target = ROOT / 'preparation/request-v3.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(request, sort_keys=True, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'request': pin(target), 'strict_old_inputs': len(strict),
                      'protected_live_sources': len(request['protected_live_sources']), 'new_native_jobs': 0}))

if __name__ == '__main__':
    main()
