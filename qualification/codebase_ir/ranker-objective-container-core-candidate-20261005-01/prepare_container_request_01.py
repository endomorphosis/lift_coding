"""Unexecuted file-only producer for the guarded generic container request.

Reads and hashes evidence; the only subprocesses are read-only Git HEAD guards.
No original ranker, compiler, prover, scheduler, metadata, or model is invoked.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
COMMON = (10418, '3e10a1311636adbb14106437d499a9202a1a026950a43d766d955e6880083478')


def helpers():
    path = ROOT / 'container_core_file_helpers_01.py'
    if path.resolve(strict=True) != path or path.is_symlink():
        raise ValueError('canonical reviewed helper source required')
    with path.open('rb') as stream:
        raw = stream.read(COMMON[0] + 1)
    if len(raw) != COMMON[0] or hashlib.sha256(raw).hexdigest() != COMMON[1]:
        raise ValueError('reviewed standard-library helper source differs')
    namespace = {'__file__': str(path), '__name__': 'held_container_request_file_helpers'}
    exec(compile(raw, str(path), 'exec'), namespace)
    namespace['exact']({'path': str(path), 'bytes': COMMON[0], 'sha256': COMMON[1]})
    return namespace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-producer-sha256', required=True)
    args = parser.parse_args()
    if not __debug__ or re.fullmatch('[0-9a-f]{64}', args.expected_producer_sha256) is None:
        raise ValueError('unoptimized externally reviewed producer pin required')
    h = helpers()
    need, pin, fixed, document = [h[name] for name in ('need', 'pin', 'fixed', 'document')]
    own = pin(Path(__file__).resolve())
    need(own['sha256'] == args.expected_producer_sha256, 'reviewed request producer differs')
    h['core_source_gate']()
    request_raw, request_pin = fixed(h['Q5'] / 'preparation/request-v3.json',
        (561622, '8e9038a657519b35e769e911219dbe5ad4bf92833017663f8673d5ef2613fdd3'), True)
    seal_raw, seal_pin = fixed(h['Q5'] / 'file-only-seal-01.json',
        (86066, '874b51a3358dee5dbd18b70c66770f4e3fdf3553c2fac3fb644075c37273f43d'), True)
    qualified_raw, qualified_pin = fixed(h['Q5'] / 'qualified-review-01.json',
        (11167, '590163443db860ac03bc2d3fde0f07ac44626e8b6e7cc57a3d6c770c4da87f00'), True)
    inherited, seal, qualified = [h['parse'](raw) for raw in (request_raw, seal_raw, qualified_raw)]
    need(qualified['status'] == 'passed' and qualified['qualified_theorem_queries'] == 14
         and seal['review'] == qualified_pin and seal['scope_root'] == str(h['Q5'])
         and seal['regular_file_count'] == len(seal['files']) == 276
         and seal['regular_file_bytes'] == sum(row['bytes'] for row in seal['files']) == 78794802
         and seal['fixture_symlinks'] == seal['excluded_dependency_roots'] == [], 'complete Q5 qualification seal join required')
    wire = json.dumps(seal['files'], sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
    need(hashlib.sha256(wire).hexdigest() == seal['file_inventory_sha256'], 'Q5 inventory digest differs')
    observed = {str(path) for path in h['Q5'].rglob('*') if path.is_file()}
    need(not any(path.is_symlink() for path in h['Q5'].rglob('*'))
         and observed == {row['path'] for row in seal['files']} | {seal_pin['path']}, 'complete quiet Q5 regular census differs')
    need(inherited['proof_limits'] == h['NATIVE_LIMITS'] and inherited['root_request'] == h['ROOT_LEASE']
         and inherited['proof_pressure_limits'] == h['PRESSURE'] and inherited['outer_timeout_seconds'] == 120,
         'native/resource/outer bounds must remain unchanged')
    strict = {row['path']: row for row in inherited['strict_old_inputs']}
    need(len(strict) == len(inherited['strict_old_inputs']) == 2108, 'unique inherited strict guards required')
    additions = [*seal['files'], seal_pin]
    for root, mapping in ((h['P7'], h['P7_PINS']), (ROOT, h['CORE_PINS'])):
        for name, pair in mapping.items():
            additions.append(fixed(root / name, pair)[1])
    p7_census = {str(path) for path in h['P7'].rglob('*') if path.is_file()}
    need(not any(path.is_symlink() for path in h['P7'].rglob('*'))
         and p7_census == {str(h['P7'] / name) for name in h['P7_PINS']}, 'complete P7 three-file census differs')
    for row in additions:
        need(row['path'] not in strict or strict[row['path']] == row, 'overlapping historical guard differs')
        strict[row['path']] = row
    need(len(strict) == 2391 and len(inherited['protected_live_sources']) == 4, 'exact additive strict/live guard population differs')
    for row in [*strict.values(), *inherited['protected_live_sources']]:
        h['exact'](row)

    def guards():
        found = {}
        for role, cwd in (('root', h['WORKSPACE']), ('child', h['WORKSPACE'] / 'external/ipfs_accelerate')):
            wanted = qualified['original_checkout_guards'][role]
            head = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-C', str(cwd), 'rev-parse', 'HEAD'], text=True, timeout=30).strip()
            index = pin(wanted['index']['path'])
            need(head == wanted['head'] and index == wanted['index'], 'original checkout HEAD/index changed')
            found[role] = {'head': head, 'index': index}
        return found

    before = guards()
    readback = document(qualified['native_metadata_readback'])
    prior_metadata = readback['metadata_inputs']
    metadata = document(prior_metadata)
    need(len(metadata) == 32 and sum(len(rows) for rows in metadata.values()) == 4458, 'prior Q5 metadata context differs')
    request = dict(inherited)
    request.update(
        schema='terminal-ranker-objective-container-core-request@1',
        strict_old_inputs=[strict[path] for path in sorted(strict)],
        prior_metadata_inputs=prior_metadata,
        prior_objective_scalar_request=request_pin, prior_objective_scalar_seal=seal_pin,
        prior_objective_scalar_qualified_review=qualified_pin,
        independent_core_source_review=h['SOURCE_GATE'],
        original_checkout_guards=before,
        exact_native_mode=h['MODE'], exact_theorem_names=list(h['QUERIES']),
        native_retention_chunk_count_max=61, native_retention_aggregate_raw_bytes_max=3997696,
        new_proof_scope='Generic ordered map/zip/index/exact-real sum and partial mean; four primitive bridges only',
        candidate_compiled=False, candidate_native_qualified=False,
        forbidden_operations=['ranker_import', 'feature_prepare', 'ranker_fit', 'autoencoder_fit', 'native_ranker_objective',
                              'native_ranker_dot', 'trace_replay', 'optimizer_update', 'dependency_setup', 'metadata_hydration', 'pure_tests'],
        actual_new_native_jobs=0, actual_new_model_jobs=0, actual_new_test_cases=0,
        actual_new_metadata_jobs=0, actual_new_source_function_executions=0,
        preparation_status='file_only_prepared_native_execution_pending',
        generic_container_semantic_preservation_proved=False,
        objective_source_equivalence_proved=False, gradient_source_equivalence_proved=False,
        full_source_runtime_equivalence=False, binary64_error_bound_proved=False,
        native_Float_optimizer_convergence_proved=False, global_autoencoder_convergence_proved=False,
        full_task_satisfaction='unknown', official_benchmark_score=None,
        **h['AUTHORITY'],
    )
    h['verify_held']()
    need(guards() == before, 'original checkout changed during file-only request preparation')
    (ROOT / 'preparation').mkdir(exist_ok=True)
    (ROOT / 'evidence').mkdir(exist_ok=True)
    descriptor = h['write'](ROOT / 'preparation/request-v3.json', request)
    print(json.dumps({'status': request['preparation_status'], 'request': descriptor,
        'strict_old_inputs': len(strict), 'protected_live_sources': 4, 'native_jobs': 0, 'target_imports': 0}))


if __name__ == '__main__':
    main()
