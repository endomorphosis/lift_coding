"""Bind actual package receipts by file/JSON reads only; performs no decoding."""
import hashlib
import json
import os
from pathlib import Path
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
PACKAGE = WORKSPACE / 'maintenance/ranker-trace-publication-package-20261005-01'
EXPECTED = {
    ROOT / 'final-source-review-03.json': '41b57a5606b12f4f87863cf3003848135c7625862c950467d17b6a2c4b661ddc',
    PACKAGE / 'package/manifest.json': '876343b329834a62a33e36a5279359f4486cdf332a689af72576b9062ff424f6',
    PACKAGE / 'closed.json': '5692071899b1bb31f4d32a384678b7d233c47c5a4e824935b570d853db8ed1ef',
    PACKAGE / 'package-review.json': 'e5e2dd4d4368e7096e494e1e2e9412561dc46ad6eb1b173b232ac03dd6d76ef2',
}


def signature(value):
    return {key: getattr(value, 'st_' + key) for key in
            ('dev', 'ino', 'mode', 'nlink', 'uid', 'gid', 'size', 'mtime_ns', 'ctime_ns')}


def pin(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        initial = os.fstat(fd)
        assert stat.S_ISREG(initial.st_mode) and initial.st_nlink == 1 and initial.st_size <= 16 * 1024**2
        digest, count = hashlib.sha256(), 0
        while block := os.read(fd, 1024**2):
            digest.update(block)
            count += len(block)
        assert count == initial.st_size
        assert signature(initial) == signature(os.fstat(fd)) == signature(path.lstat())
        return {'path': str(path), 'bytes': count, 'sha256': digest.hexdigest()}
    finally:
        os.close(fd)


def body(path):
    return json.loads(Path(path).read_bytes())


def main():
    before = {str(path): pin(path) for path in EXPECTED}
    assert all(before[str(path)]['sha256'] == expected for path, expected in EXPECTED.items())
    source = body(ROOT / 'final-source-review-03.json')
    manifest = body(PACKAGE / 'package/manifest.json')
    closure = body(PACKAGE / 'closed.json')
    review = body(PACKAGE / 'package-review.json')
    assert source['status'] == 'source_and_exact_file_bindings_reviewed_no_blocking_findings'
    for binding in source['sources_and_inputs'].values():
        assert pin(binding['path']) == binding
    assert (closure['schema'], closure['status']) == (
        'ranker-trace-local-package-attempt@1', 'passed_local_frozen_package')
    assert (review['schema'], review['status']) == (
        'ranker-trace-full-decoded-member-file-only-review@1', 'passed')
    assert closure['manifest'] == review['manifest'] == before[str(PACKAGE / 'package/manifest.json')]
    assert review['package_closure'] == before[str(PACKAGE / 'closed.json')]
    assert closure['candidate_hits'] == closure['source_drift_count'] == 0 and closure['cleanup_errors'] == []
    assert manifest['scan_hits'] == [] and manifest['file_count'] == 208 and manifest['original_file_bytes'] == 45423129
    assert manifest['status'] == 'closed_scanned_local_package_not_uploaded'
    assert manifest['closed_inputs'] == review['closed_inputs'] == source['sources_and_inputs'][
        str(WORKSPACE / 'maintenance/ranker-trace-publication-source-plan-20261005-01/closed-inputs.json')]
    assert manifest['final_selection'] == source['sources_and_inputs'][
        str(WORKSPACE / 'maintenance/ranker-trace-publication-source-plan-20261005-01/final-selection.json')]
    assert manifest['builder'] == source['sources_and_inputs'][
        str(WORKSPACE / 'maintenance/ranker-trace-publication-source-plan-20261005-01/build_package.py')]
    assert review['reviewer'] == source['sources_and_inputs'][
        str(WORKSPACE / 'maintenance/ranker-trace-publication-source-plan-20261005-01/review_package.py')]
    selection = body(manifest['final_selection']['path'])
    selected = {item['path']: item for item in selection['files']}
    files = manifest['files']
    assert len(files) == len({item['source_path'] for item in files}) == 208
    assert {item['source_path'] for item in files} == set(selected)
    for row in files:
        selected_row = selected[row['source_path']]
        assert row['bytes'] == selected_row['bytes'] and row['sha256'] == selected_row['sha256']
        assert row['source_stat'] == selected_row['stat'] == signature(Path(row['source_path']).lstat())
        assert row['path'] == row['member'] == str(Path(row['source_path']).relative_to(WORKSPACE))
        assert row['scan_hits'] == []
        assert pin(row['source_path']) == {key: selected_row[key] for key in ('path', 'bytes', 'sha256')}
    shards = manifest['data_shards']
    assert len(shards) == len(review['decoded_tar_shards']) == 3
    assert sum(row['members'] for row in shards) == review['decoded_members_verified'] == 208
    for row, checked in zip(shards, review['decoded_tar_shards']):
        assert pin(row['path']) == {key: row[key] for key in ('path', 'bytes', 'sha256')}
        assert row['scan_hits'] == [] and row['decoded_per_file_readback_verified'] is True
        assert row['decoded_tar_bytes'] <= 16 * 1024**2
        assert checked == {'archive': row['archive'], 'decoded_tar_bytes': row['decoded_tar_bytes'],
                           'members_verified': row['members']}
        assert sum(item['archive'] == row['archive'] for item in files) == row['members']
    assert sum(row['decoded_tar_bytes'] for row in shards) == 45762560
    assert manifest['actual_verification_decode_bytes'] == review['actual_file_only_review_decoded_bytes'] == 45762560
    assert manifest['actual_aggregate_decoded_work_bytes'] == 136948249
    assert manifest['actual_recursive_classifier_decoded_bytes'] == 91185689
    assert manifest['actual_aggregate_decoded_work_bytes'] == (
        manifest['actual_recursive_classifier_decoded_bytes'] + manifest['actual_verification_decode_bytes'])
    assert manifest['actual_aggregate_decoded_work_bytes'] <= 512 * 1024**2
    expected_seal = {'explicit_additions': 11, 'sealed_durable_leaves_selected': 197,
                     'sealed_file_count_rehashed': 203, 'sealed_lock_bindings_rehashed': 6}
    assert manifest['seal_binding_before'] == manifest['seal_binding_after'] == expected_seal
    assert (review['sealed_leaves_verified_before_after'], review['sealed_excluded_lock_bindings_verified_before_after'],
            review['selected_files_verified_before_after']) == (203, 6, 208)
    assert review['exact_202_semantic_outcome_facts_verified'] is True
    assert review['first_inconclusive_lean_attempt_retained'] is True
    assert manifest['exact_available_cached_credential_veto'] is True
    assert manifest['bounded_complete_PEM_classifier_veto'] is True and manifest['universal_secret_free_claim'] is False
    for item in (manifest, review, closure):
        assert item['remote_mutations'] == 0
    for item in (manifest, review):
        assert item['proof_authority'] is item['execution_authority'] is item['completion_authority'] is False
        assert item['asymptotic_optimizer_convergence_proved'] is False and item['all32_governing_RPI_exits'] == 'OPEN'
    assert not (PACKAGE / 'staging').exists()
    assert all(pin(path) == before[str(path)] for path in EXPECTED)
    result = {'schema': 'ranker-trace-independent-actual-package-receipt-join@1', 'status': 'passed_file_only_receipt_join',
        'producer': pin(Path(__file__).resolve()), 'inputs': before,
        'source_review_clearance': before[str(ROOT / 'final-source-review-03.json')],
        'actual_package_closure_and_independent_member_review_bound': True,
        'same208_selected_members_and_shards_bound': True, 'sealed203_before_after_bound': True,
        'semantic202_facts_and_prior_inconclusive_attempt_bound': True,
        'shards': shards, 'source_regular_files_rehashed': 208,
        'declared_producer_aggregate_decoded_work_bytes': 136948249,
        'declared_member_reviewer_decode_bytes': 45762560,
        'publication_aggregate_decode_limit_bytes': 512 * 1024**2, 'per_container_limit_bytes': 16 * 1024**2,
        'decode_reports_are_bound_here_actual_decoding_was_by_other_owned_producers': True,
        'blocking_findings': [], 'operations_this_join': {'file_and_json_reads_only': True, 'native_jobs': 0,
            'project_imports': 0, 'test_repeats': 0, 'archive_decodes': 0, 'classifier_calls': 0,
            'credential_reads': 0, 'network_calls': 0, 'git_calls': 0, 'uploads': 0},
        'native_limits_unchanged': True, 'historical_origin_proved': False,
        'proof_authority': False, 'asymptotic_convergence_proved': False, 'full_task_satisfaction': 'unknown',
        'all32_governing_RPI_exits': 'OPEN', 'planner_activation': False, 'official_benchmark_score': None}
    target = ROOT / 'actual-package-receipt-join-01.json'
    with target.open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(pin(target), sort_keys=True))


if __name__ == '__main__':
    main()
