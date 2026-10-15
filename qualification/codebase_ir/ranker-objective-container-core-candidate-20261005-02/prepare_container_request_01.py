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
COMMON = (17601, '815bec62dd2c8de4073b389dbdf62827c4a639d4f6a3e08e5e79ef83ccffff3a')


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
    parser.add_argument('--failed-v1-seal', required=True, type=Path)
    parser.add_argument('--expected-failed-v1-seal-sha256', required=True)
    args = parser.parse_args()
    if not __debug__ or any(re.fullmatch('[0-9a-f]{64}', value) is None for value in
            (args.expected_producer_sha256, args.expected_failed_v1_seal_sha256)):
        raise ValueError('unoptimized externally reviewed producer pin required')
    h = helpers()
    need, pin, fixed, document = [h[name] for name in ('need', 'pin', 'fixed', 'document')]
    own = pin(Path(__file__).resolve())
    need(own['sha256'] == args.expected_producer_sha256, 'reviewed request producer differs')
    h['core_source_gate']()
    seal_pin = pin(args.failed_v1_seal)
    need(seal_pin['sha256'] == args.expected_failed_v1_seal_sha256, 'externally reviewed failed-v1 seal differs')
    strict_rows, inherited, failed_seal, failed_review = h['complete_guard_union'](seal_pin)
    qualified_pin = inherited['prior_objective_scalar_qualified_review']
    need(qualified_pin == {'path': str(h['Q5'] / 'qualified-review-01.json'), 'bytes': 11167,
        'sha256': '590163443db860ac03bc2d3fde0f07ac44626e8b6e7cc57a3d6c770c4da87f00'},
        'unchanged qualified checkout/metadata context source required')
    qualified = document(qualified_pin)
    need(qualified['status'] == 'passed' and qualified['qualified_theorem_queries'] == 14,
         'prior objective scalar qualification context differs')
    for row in [*strict_rows, *inherited['protected_live_sources']]:
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
        strict_old_inputs=strict_rows,
        prior_metadata_inputs=prior_metadata,
        prior_failed_container_request=h['V1_REQUEST'], prior_failed_container_seal=seal_pin,
        prior_failed_container_review=failed_seal['review'],
        prior_failed_container_native_attempts=1, prior_failed_container_qualified_queries=0,
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
    h['validate_guard_union'](request)
    h['verify_held']()
    need(guards() == before, 'original checkout changed during file-only request preparation')
    (ROOT / 'preparation').mkdir(exist_ok=True)
    (ROOT / 'evidence').mkdir(exist_ok=True)
    descriptor = h['write'](ROOT / 'preparation/request-v3.json', request)
    print(json.dumps({'status': request['preparation_status'], 'request': descriptor,
        'strict_old_inputs': len(strict_rows), 'protected_live_sources': 4, 'native_jobs': 0, 'target_imports': 0}))


if __name__ == '__main__':
    main()
