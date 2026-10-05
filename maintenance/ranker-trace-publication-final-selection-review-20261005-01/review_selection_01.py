"""File/JSON/AST-only review of the frozen HF selection; no publisher execution."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
OWNER = WORKSPACE / 'maintenance/ranker-trace-publication-root-20261005-01'
SELECTION = OWNER / 'final-hf-selection-01.json'
SELECTION_SHA = 'a53a4b11ab8e5cf257ada4f7d0e8525aa4738516edd2cc2e86e281b3cab908e7'
PREFIX = 'releases/20261004-terminal-codebase-ir-evidence-v1'
NAMESPACE = PREFIX + '/successor-ranker-trace-v1/'
MUTABLE = {'README.md', PREFIX + '/publication-status.json'}


def signature(value):
    return tuple(getattr(value, 'st_' + key) for key in
                 ('dev', 'ino', 'mode', 'nlink', 'uid', 'gid', 'size', 'mtime_ns', 'ctime_ns'))


def pin(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        initial = os.fstat(fd)
        assert stat.S_ISREG(initial.st_mode) and initial.st_nlink == 1 and initial.st_size <= 16 * 1024**2
        digest, size = hashlib.sha256(), 0
        while block := os.read(fd, 1024**2):
            digest.update(block)
            size += len(block)
        assert size == initial.st_size
        assert signature(initial) == signature(os.fstat(fd)) == signature(path.lstat())
        return {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}
    finally:
        os.close(fd)


def body(path):
    return json.loads(Path(path).read_bytes())


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def main():
    selection_pin = pin(SELECTION)
    assert selection_pin['sha256'] == SELECTION_SHA and selection_pin['bytes'] == 14919
    selection = body(SELECTION)
    assert selection['schema'] == 'terminal-ranker-trace-final-HF-selection@1'
    assert selection['repo_id'] == 'Publicus/codebase-ir-proof-index'
    assert selection['expected_parent_commit'] == '580717c7b45e7162ce6f1b5e63309fc76b962b44'
    files = selection['files']
    by_remote = {row['remote']: row for row in files}
    by_path = {row['local']['path']: row['local'] for row in files}
    assert len(files) == len(by_remote) == len(by_path) == 38
    assert sum(row['local']['bytes'] for row in files) == 7810498
    assert {name for name in by_remote if not name.startswith(NAMESPACE)} == MUTABLE
    assert sum(name.startswith(NAMESPACE) for name in by_remote) == 36
    assert NAMESPACE + 'publication/metadata-scan-closed.json' not in by_remote
    for row in files:
        name = row['remote']
        assert not name.startswith('/') and '..' not in Path(name).parts and '\\' not in name
        assert pin(row['local']['path']) == row['local']
        if Path(row['local']['path']).suffix == '.py':
            ast.parse(Path(row['local']['path']).read_bytes())
    manifest = body(by_remote[NAMESPACE + 'manifest.json']['local']['path'])
    closure = body(selection['package_closure_and_review'][0]['path'])
    member_review = body(selection['package_closure_and_review'][1]['path'])
    assert closure['schema'] == 'ranker-trace-local-package-attempt@1' and closure['status'] == 'passed_local_frozen_package'
    assert member_review['schema'] == 'ranker-trace-full-decoded-member-file-only-review@1' and member_review['status'] == 'passed'
    for binding in selection['package_closure_and_review']:
        assert by_path[binding['path']] == pin(binding['path']) == binding
    assert closure['manifest'] == member_review['manifest'] == by_remote[NAMESPACE + 'manifest.json']['local']
    assert selection['qualified_package_shards'] == [
        {key: row[key] for key in ('path', 'bytes', 'sha256')} for row in manifest['data_shards']]
    for binding in selection['qualified_package_shards']:
        assert by_path[binding['path']] == pin(binding['path']) == binding
    assert len(selection['qualified_package_shards']) == 3
    assert manifest['file_count'] == member_review['decoded_members_verified'] == 208
    assert manifest['original_file_bytes'] == 45423129
    assert member_review['exact_202_semantic_outcome_facts_verified'] is True
    assert member_review['first_inconclusive_lean_attempt_retained'] is True
    assert member_review['sealed_leaves_verified_before_after'] == 203
    assert manifest['scan_hits'] == [] and closure['candidate_hits'] == closure['source_drift_count'] == 0
    status_pin = by_remote[PREFIX + '/publication-status.json']['local']
    status = body(status_pin['path'])
    readme_pin = by_remote['README.md']['local']
    readme = Path(readme_pin['path']).read_text()
    inputs = body(by_remote[NAMESPACE + 'publication/input-pins.json']['local']['path'])
    assert inputs['inputs'] == {'README.md': readme_pin, 'publication-status.json': status_pin}
    assert inputs['package_manifest'] == closure['manifest']
    assert inputs['package_review'] == selection['package_closure_and_review'][1]
    assert inputs['preparation_time_base_hf_revision'] == status['preparation_time_verified_hf_base_revision'] == selection['expected_parent_commit']
    assert status['ranker_trace_closed_package']['manifest'] == closure['manifest']
    assert status['ranker_trace_closed_package']['closure'] == selection['package_closure_and_review'][0]
    assert status['ranker_trace_closed_package']['independent_decoded_member_review'] == selection['package_closure_and_review'][1]
    assert wire(status['ranker_trace_closed_package']['data_shards']) == wire(manifest['data_shards'])
    assert status['ranker_trace_closed_package']['compressed_shard_bytes'] == sum(row['bytes'] for row in manifest['data_shards']) == 7139485
    qualification_pin = status['ranker_trace_qualification_binding']
    assert by_path[qualification_pin['path']] == pin(qualification_pin['path']) == qualification_pin
    assert wire(status['ranker_trace_qualification']) == wire(body(qualification_pin['path']))
    qualified = status['ranker_trace_qualification']
    assert (qualified['selected_unit_tests'], qualified['authenticated_states'], qualified['original_verification_optimizer_updates'],
            qualified['original_total_gradient_evaluations']) == (64, 129, 128, 131)
    assert (qualified['metadata_families'], qualified['metadata_rows'], qualified['prior_payload_rows_preserved_exactly']) == (29, 4348, 4216)
    assert (qualified['native_lean_invocations_total'], qualified['native_lean_prior_inconclusive_calls'],
            qualified['native_lean_final_qualified_checks']) == (3, 1, 2)
    assert qualified['complete_positive_olean_bytes'] == 58952
    prior_pin = status['prior_status_source']
    assert pin(prior_pin['path']) == prior_pin
    prior = body(prior_pin['path'])
    assert all(wire(status[key]) == wire(value) for key, value in prior.items() if key not in ('schema', 'status'))
    for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation',
                'asymptotic_optimizer_convergence_proved', 'global_optimizer_convergence_proved',
                'global_autoencoder_convergence_proved', 'historical_execution_origin_authenticated',
                'historical_training_provenance_authenticated', 'independent_pin_origin_authenticated',
                'whole_source_equivalence_proved', 'full_task_satisfaction_proved'):
        assert status[key] is False
    assert status['official_benchmark_score'] is None and status['full_task_satisfaction'] == 'unknown'
    assert qualified['all32_governing_RPI_exits'] == 'OPEN'
    assert status['new_ranker_trace_hf_revision'] is status['new_root_publication_commit'] is None
    assert status['publication_decoder_policy'] == {'container_max_bytes': 16 * 1024**2,
        'decoded_work_bytes': 512 * 1024**2, 'native_solver_artifact_admission_bounds_changed': False,
        'scope': 'publication archive scanning and decoded-member review only'}
    child = body(by_remote[NAMESPACE + 'publication/child-publication-closed.json']['local']['path'])
    compatibility = body(by_remote[NAMESPACE + 'publication/child-upstream-compatibility-source-review.json']['local']['path'])
    assert child['status'] == 'ordinary_fast_forward_push_verified' and child['published_commit_reachable_from_main'] is True
    assert child['published_commit'] == child['remote_main_after'] == child['fetched_main_after'] == inputs['verified_child_commit'] == 'fa51b32e8d3f296f4481344a5a61da9fd3ffd2a6'
    assert child['remote_main_before'] == child['base_main_commit'] == compatibility['fresh_child_main']
    assert child['qualified_review_sha256'] == qualification_pin['sha256']
    assert child['file_seal_sha256'] == status['ranker_trace_file_seal_binding']['sha256']
    assert len(child['changed_files']) == 2
    for row in child['changed_files']:
        source = by_remote[NAMESPACE + 'source/ipfs_accelerate/' + row['path']]['local']
        assert row['bytes'] == source['bytes'] and row['sha256'] == source['sha256']
    assert compatibility['status'] == 'passed_source_only_exact_dependency_bytes'
    assert all(row['match'] is True and row['qualified_source_sha256'] == row['fresh_child_main_or_selected_new_file_sha256'] for row in compatibility['checked_dependencies'])
    for snippet in ('208 selected files', '45,423,129 original file bytes', 'all 129 recorded states',
                    '128 verification updates', '131 native objective/gradient evaluations',
                    '4,348 payload rows in 29 families', 'three actual Lean invocations',
                    'Historical training execution and external pin origin remain unauthenticated',
                    'All 32 governing RPI exits remain OPEN', 'official benchmark score remains null'):
        assert snippet in readme
    assert manifest['closed_inputs'] == member_review['closed_inputs']
    assert all(pin(row['local']['path']) == row['local'] for row in files) and pin(SELECTION) == selection_pin
    target = ROOT / 'selection-card-receipt-review-01.json'
    assert str(target) not in by_path
    result = {'schema': 'ranker-trace-final-HF-selection-file-only-review@1', 'status': 'passed_no_blocking_findings',
        'selection': selection_pin, 'producer': pin(Path(__file__).resolve()),
        'selected_files_rehashed_before_after': 38, 'selected_file_bytes': 7810498,
        'new_namespace_destinations': 36, 'explicit_mutable_pointers': sorted(MUTABLE),
        'fixed_producer_scan_receipt_destination': NAMESPACE + 'publication/metadata-scan-closed.json',
        'expected_produced_upload_file_count_after_successful_scan': 39,
        'package_closure_and_member_review_exact': True, 'qualified_shards_exact': 3,
        'package_members': 208, 'package_original_bytes': 45423129,
        'cards_preserve_all_prior_status_fields_except_schema_and_status': True,
        'qualification_card_is_exact_type_preserved_copy_of_bound_review': True,
        'child_publication_and_dependency_compatibility_receipts_consistent': True,
        'original_128_replay_and_finite_integer_order_scope_preserved': True,
        'three_Lean_attempts_including_first_inconclusive_retained': True,
        'no_future_HF_or_root_commit_fabricated_in_cards': True,
        'prior145_files143_immutable_preservation_is_publisher_requirement_not_remote_read_in_this_review': True,
        'publication_decoder_512MiB_only_native_limits_unchanged': True,
        'blocking_findings': [], 'scan_success_and_fresh_parent_and_remote_verification_remain_required': True,
        'operations_this_review': {'file_JSON_AST_only': True, 'native_jobs': 0, 'test_repeats': 0,
            'archive_decodes': 0, 'classifier_calls': 0, 'credential_reads': 0, 'project_imports': 0,
            'network_calls': 0, 'git_calls': 0, 'uploads': 0},
        'all32_governing_RPI_exits': 'OPEN', 'proof_authority': False,
        'asymptotic_convergence_proved': False, 'historical_execution_origin_proved': False,
        'full_task_satisfaction': 'unknown', 'planner_activation': False, 'official_benchmark_score': None}
    with target.open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(pin(target), sort_keys=True))


if __name__ == '__main__':
    main()
