"""Source/JSON/file-only independent publication gate review; executes no helper."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
PLAN_ROOT = WORKSPACE / 'maintenance/ranker-trace-publication-source-plan-20261005-01'
ROOT_AUDIT = WORKSPACE / 'maintenance/ranker-trace-publication-root-20261005-01'
QUALIFIER = WORKSPACE / 'qualification/codebase_ir/ranker-trace-authentication-20261005-01'
EXPECTED = {
    PLAN_ROOT / 'build_package.py': '06a88576368b2b232b8f9bd8ee27462277215d805572a74639304d4cd882685f',
    PLAN_ROOT / 'review_package.py': '1e7bc7f14d336147018d7b64af225c4eb9ba87c7398bfc96eec7a08d708855e8',
    PLAN_ROOT / 'plan.json': '35d622515486464e4a215af5420fa83c82b12bd1f2c938069698bc615cd53a9a',
    PLAN_ROOT / 'required-facts.json': '256f52449c65b8c7e477349af63d1dad6cbc24b73949fd957a6b63499ce47833',
    PLAN_ROOT / 'final-selection.json': '41c1338ba0463d1f4ae7c409e8e820ed4d6bf7b099bced4c5db27b659a4e7390',
    PLAN_ROOT / 'closed-inputs.json': '93b6fde44a3439c1fd6b59a65286ebc66bc4ce47dda12fe801f659d08fb006c3',
    ROOT_AUDIT / 'verify_closed_qualification.py': '6cdfb1454d0b870cd32a0a68c0b2ce32602982cc12c00c1224c88e81ba072120',
    ROOT_AUDIT / 'independent-qualified-join-01.json': '2850d5e7598e84b1696faa447cb45da92f897b6764ae97a03f457912758ad712',
    ROOT_AUDIT / 'prepare_publication_metadata.py': 'ac90a026b3dec72592cfb9f82df7081018851426e6c4325c6ca9a44428373154',
}


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def signature(info):
    return {key: getattr(info, 'st_' + key) for key in
            ('dev', 'ino', 'mode', 'nlink', 'uid', 'gid', 'size', 'mtime_ns', 'ctime_ns')}


def pin(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= 16 * 1024**2
        digest, count = hashlib.sha256(), 0
        while block := os.read(fd, 1024**2):
            digest.update(block); count += len(block)
        assert count == before.st_size and signature(before) == signature(os.fstat(fd)) == signature(path.lstat())
        return {'path': str(path), 'bytes': count, 'sha256': digest.hexdigest()}
    finally:
        os.close(fd)


def body(path):
    return json.loads(Path(path).read_bytes())


def pointer(value, path):
    for field in path.strip('/').split('/') if path else []:
        field = field.replace('~1', '/').replace('~0', '~')
        value = value[int(field)] if type(value) is list else value[field]
    return value


def check_population(closure, selected, seal):
    sealed = seal['files']
    assert len(sealed) == len({row['path'] for row in sealed}) == 203
    assert hashlib.sha256(wire(sealed)).hexdigest() == seal['file_inventory_sha256']
    for row in sealed:
        assert pin(row['path']) == row
    additions = closure['explicit_additions']
    assert len(additions) == len({row['path'] for row in additions}) == 11
    for row in additions:
        assert pin(row['path']) == row
    locks = {row['path'] for row in selected['exclusions']}
    assert len(locks) == 6 and all(row['kind'] == 'transient_lock' for row in selected['exclusions'])
    assert locks == {row['path'] for row in sealed if row['path'].endswith('.lock')}
    for row in selected['exclusions']:
        assert signature(Path(row['path']).lstat()) == row['stat'] and row['stat']['size'] == 0
    expected = ({row['path'] for row in sealed} - locks) | {row['path'] for row in additions}
    assert len(expected) == len(selected['files']) == 208
    assert {row['path'] for row in selected['files']} == expected
    for row in selected['files']:
        assert pin(row['path']) == {key: row[key] for key in ('path', 'bytes', 'sha256')}
        assert signature(Path(row['path']).lstat()) == row['stat']
    for row in selected['directories']:
        assert signature(Path(row['path']).lstat()) == row['stat']
    discovered = {str(path) for scope in map(Path, closure['scopes']) for path in scope.rglob('*') if path.is_file()}
    assert discovered == {row['path'] for row in sealed} | {row['path'] for row in additions if
        any(Path(row['path']).is_relative_to(Path(scope)) for scope in closure['scopes'])}
    assert sum(row['bytes'] for row in selected['files']) == 45423129 < 64 * 1024**2


def main():
    observed = {str(path): pin(path) for path in EXPECTED}
    assert all(observed[str(path)]['sha256'] == expected for path, expected in EXPECTED.items())
    for path in EXPECTED:
        if path.suffix == '.py': ast.parse(path.read_bytes())
    closure, selected = body(PLAN_ROOT / 'closed-inputs.json'), body(PLAN_ROOT / 'final-selection.json')
    policy, plan = body(PLAN_ROOT / 'required-facts.json'), body(PLAN_ROOT / 'plan.json')
    assert closure['schema'] == 'ranker-trace-publication-closed-inputs@1' and closure['source_and_artifacts_quiet'] is True
    assert selected['schema'] == 'ranker-trace-publication-final-selection@1'
    assert closure['final_selection'] == observed[str(PLAN_ROOT / 'final-selection.json')]
    assert wire(closure['required_facts']) == wire(policy) and len(policy) == 202
    documents = {}
    for name, row in closure['documents'].items():
        assert pin(row['path']) == row
        documents[name] = body(row['path'])
    for fact in policy:
        assert wire(pointer(documents[fact['document']], fact['pointer'])) == wire(fact['equals'])
    seal = documents['file_seal']
    check_population(closure, selected, seal)
    auth, meta, review = documents['native_authentication'], documents['metadata_readback'], documents['qualified_review']
    assert (auth['checked_trace_rows'], len(auth['authenticated_states']), auth['optimizer_replay_updates'],
            auth['gradient_evaluations'], review['selected_unit_tests']) == (129, 129, 128, 131, 64)
    assert len(meta['family_counts']) == 29 and meta['row_count'] == 4348 and review['prior_payload_rows_preserved_exactly'] == 4216
    assert type(meta['fresh_process_readback']) is dict and meta['fresh_process_readback']['verified'] is True
    assert documents['positive_lean_check']['status'] == 'passed' and documents['negative_lean_check']['status'] == 'rejected'
    assert documents['inconclusive_lean_check']['status'] == 'inconclusive' and documents['inconclusive_lean_check']['output_truncated'] is True
    assert review['native_lean_invocations_total'] == 3 and review['native_lean_final_qualified_checks'] == 2
    assert plan['receipt_protocol']['package_closure_status'] == 'passed_local_frozen_package'
    assert plan['receipt_protocol']['independent_review_status'] == 'passed'
    assert plan['publication_decode_profile']['aggregate_decoded_work_bytes'] == 512 * 1024**2
    assert plan['publication_decode_profile']['per_decoded_container_bytes'] == 16 * 1024**2
    check_population(closure, selected, seal)
    assert all(pin(path) == observed[str(path)] for path in EXPECTED)
    result = {'schema': 'ranker-trace-independent-publication-source-gate-review@1',
        'status': 'source_and_exact_file_bindings_reviewed_no_blocking_findings', 'source_only': True,
        'sources_and_inputs': observed, 'reviewer_source': pin(Path(__file__).resolve()),
        'qualification_review': closure['documents']['qualified_review'], 'qualification_seal': closure['documents']['file_seal'],
        'native_source_pins': closure['source_pins'], 'sealed_leaves_rehashed_before_after': 203,
        'selected_regular_files_rehashed_before_after': 208, 'selected_regular_file_bytes': 45423129,
        'sealed_empty_locks_bound_but_not_archived': 6, 'exact_explicit_additions': 11,
        'type_preserved_observed_semantic_facts_checked': 202, 'blocking_findings': [],
        'resolved_findings': ['Multiple complete GNU tar shards respect the16MiB decoded-container bound.',
            'Explicit publication-only512MiB decoding profile covers recursive scans and charged manual readback.',
            'Seal inventory digest uses original compact JSON without trailing newline.',
            'Supplemental scanner accepts exact ordered package-closure and member-review schema/status pairs.',
            'Producer metadata-scan receipt destination is reserved outside the scanned root selection.',
            'Root supplemental scanner dictionary-update syntax corrected and independently AST parsed.',
            'Builder failure retention requires output ownership established by exclusive mkdir.'],
        'source_findings': {'all203_sealed_inputs_and_only_fixed_additions': True,
            'six_excluded_locks_still_verified': True, 'first_inconclusive_lean_attempt_retained': True,
            'counts64_tests129_states128_updates131_gradients_bound': True,
            'metadata29_families4348_rows4216_prior_payloads_bound': True,
            'fresh_process_readback_dictionary_verified_true_bound': True,
            'original_training_corpus_separate_from_expanded_step_profile': True,
            'frozen_recursive_classifier_and_exact_cached_credential_veto': True,
            'bounded_complete_PEM_veto_and_no_candidate_value_output': True,
            'all_selected_bytes_and_helper_builder_pins_checked_before_after': True,
            'failed_owned_packaging_outputs_retained_private': True,
            'supplemental_scan_failure_retention_starts_after_output_ownership': True,
            'root_publisher02_requires_external_planSHA_fresh_parent_immutable_preservation': True},
        'publication_profile': plan['publication_decode_profile'],
        'native_solver_and_metadata_limits_unchanged': True,
        'semantic_scope': 'Finite original native replay, exact integer order of authenticated rounded observations, and native storage integrity only.',
        'historical_execution_origin_authenticated': False, 'independent_pin_origin_authenticated': False,
        'whole_source_runtime_equivalence_proved': False, 'asymptotic_optimizer_convergence_proved': False,
        'binary64_error_bound_proved': False, 'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN',
        'planner_activation': False, 'official_benchmark_score': None, 'proof_authority': False,
        'operations_this_review': {'native_jobs': 0, 'test_repeats': 0, 'classifier_calls': 0,
            'archive_decodes': 0, 'credential_reads': 0, 'network_calls': 0, 'git_calls': 0, 'uploads': 0},
        'actual_local_classification_member_review_and_publication_not_executed_by_this_review': True}
    target = ROOT / 'final-source-review-03.json'
    with target.open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False); stream.write('\n')
    print(json.dumps(pin(target), sort_keys=True))


if __name__ == '__main__':
    main()
