"""Summarize sealed scoped tests and saved public CLI outputs; no new replay."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

STAGE = Path(__file__).resolve().parent


def load(name):
    return json.loads((STAGE / name).read_text())


def pin(name):
    raw = (STAGE / name).read_bytes()
    return {'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def cases(name):
    root = ET.parse(STAGE / name).getroot()
    cases = root.findall('.//testcase')
    assert all(not any(case.find(kind) is not None for kind in ('failure', 'error', 'skipped')) for case in cases)
    ids = {(case.attrib['classname'], case.attrib['name']) for case in cases}
    assert len(ids) == len(cases)
    return ids


def main():
    inspector = load('inspector-validation.json')
    ledger = load('session-ledger-reader-validation-03.json')
    public = load('public-cli-qualification-01/qualification.json')
    fixture = load('public-native-fixture-02/summary.json')
    independent = load('final-independent-review.json')
    downstream = load('session-ledger-downstream-review.json')
    source = load('source-manifest.json')
    preservation = load('preservation-check.json')
    inspector_cases = cases('inspector-validation-03.xml')
    ledger_cases = cases('session-ledger-reader-tests-03.xml')
    assert len(inspector_cases) == 53 and len(ledger_cases) == 42
    assert not inspector_cases & ledger_cases
    assert public['qualified'] and ledger['qualified'] and preservation['all_checks_passed']
    assert independent['decision'] == 'no_blocker_within_qualified_host_inspection_scope'
    assert downstream['review_passed'] and not downstream['blocking_findings']
    successful = [call for call in public['calls'] if call['returncode'] == 0]
    refusals = [call for call in public['calls'] if call['returncode'] == 2]
    assert len(successful) == 5 and len(refusals) == 6
    facts = load('public-cli-qualification-01/native-facts-page-1.json')
    totals = {'successful_outputs': len(successful),
        'successful_complete_cli_output_bytes': sum(call['stdout_bytes'] for call in successful),
        'sum_independent_local_tool_output_tokens': sum(call['local_tokens'] for call in successful),
        'successful_calls_seconds': sum(call['seconds'] for call in successful),
        'invalid_requests_refused': len(refusals),
        'all_calls_wall_seconds': public['seconds']}
    assert totals['successful_complete_cli_output_bytes'] == 28318
    assert totals['sum_independent_local_tool_output_tokens'] == 9851
    result = {
        'schema': 'bounded-source-inspection-and-native-ledger-result@1',
        'stage': str(STAGE),
        'outcome': 'Bounded host source/fact CLI qualified against current native public Bottle retrieval, and the existing native usage reader now attaches a bounded pure session ledger.',
        'changed_source_files': source['files'],
        'source_patch': {key: source[key] for key in ('patch_path', 'patch_bytes', 'patch_sha256', 'patch_applies_cleanly_to_captured_baseline', 'applied_changed_bytes_match_checkout')},
        'tests': {
            'inspector_latest_unique_passed': 53, 'native_reader_latest_unique_passed': 42,
            'combined_unique_latest_passed': 95, 'latest_failed': 0, 'latest_errors': 0, 'latest_skipped': 0,
            'legacy_equivalence_cases': ledger['legacy_equivalence']['cases'],
            'legacy_fields_canonical_byte_identical': True,
            'historical_inspector_failure_retained': inspector['historical_failure'],
            'prior_and_repeated_tests_not_added_to_latest_count': True,
            'whole_repository_test_pass_claimed': False},
        'public_native_metadata': {
            'source_bytes': 175565, 'source_sha256': fixture['source_sha256'],
            'literal_instruction_sha256': fixture['instruction_sha256'],
            'permitted_files': ['bottle.py'], 'native_symbols': fixture['native_symbols'],
            'native_fact_rows_replayed': fixture['native_fact_rows_replayed'],
            'vectors': fixture['vectors'], 'fresh_ducklake_projection': fixture['fresh_ducklake_projection'],
            'hydration_scope': 'Fresh source-derived AST/native symbol vectors, source/fact replay, one metadata vector catalog and path-to-symbol links. DuckLake projects the catalog/links, not complete behavioral contracts or proof objects.',
            'separate_complete_kg_contract_or_proof_tables_qualified': False,
            'native_index_id': fixture['native_index_id'], 'native_query_id': fixture['native_query_id'],
            'native_result_id': fixture['native_result_id'],
            'fixture_prepare_seconds': fixture['seconds'],
            'protected_public_capture': fixture['public_capture_repository_and_inspector_input_permissions'],
            'preliminary_fixture_01': 'Retained before permission correction; not a positively qualified inspector input. Fixture02 is the protected current public qualification.'},
        'source_inspection': {
            'api': 'inspect_code_source',
            'module': 'ipfs_accelerate_py.agent_supervisor.runtime.code_source_inspection',
            'qualification': totals, 'cases': public['cases'],
            'literal_query_hits': public['literal_query_hits'],
            'inspected_nominated_symbol_count': 2,
            'native_facts_hydrated_for_static_file': facts['bindings']['native_fact_counts'],
            'header_targets_nominated': False,
            'non_nominated_header_symbol_refused': True,
            'complete_serialized_stdout_capped': True,
            'explicit_identity_and_budget_bound_continuation': True,
            'selected_source_bytes_and_fact_sets_exactly_reconstructed': True,
            'original_fixture_bytes_and_witnesses_unchanged': True,
            'unrelated_metadata_owner_activated': False,
            'source_authentication_or_immutable_custody_claimed': False},
        'native_reader_ledger': {
            'integration_in_checkout_source': True,
            'records': 'Already parsed exact selected bounded native reader population; no additional rollout reader.',
            'legacy_schema': ledger['legacy_schema_preserved'],
            'attachment': ledger['ledger_attachment'],
            'qualified_status_scope': ledger['qualified_status_scope'],
            'unavailable_usage_zeroed': False,
            'tool_or_model_turn_token_attribution_claimed': False,
            'billing_or_completion_authority_added': False,
            'whole_log_retention_guaranteed': False,
            'whole_log_limit_caveat': 'Downstream existing 8MB worker-log and 64MiB comparison-population bounds can still refuse a whole receipt; the attachment cap is not a universal retention guarantee.'},
        'independent_review': {
            'host_inspector_no_blocker': True,
            'reader_downstream_no_blocker': True,
            'scopes': ['Frozen code/test and saved public output/source checks.', 'Read-only reader downstream compatibility and bound review.']},
        'preservation': {
            'prior_unchanged_pin_checks': preservation['prior_unchanged_pin_checks'],
            'beginning_source_checks': len(preservation['beginning_source_checks']),
            'all_passed': True, 'prior_stage_artifacts_and_sources_unchanged': True,
            'one_expected_reader_delta_original_bytes_retained': True,
            'original_dirty_checkout_or_git_index_mutated': False},
        'limits': {
            'local_tokenizer': public['local_tokenizer'],
            'public_cli_scope': load('qualification-environment.json')['public_cli_environment_scope'],
            'native_real_session_census_qualified': False,
            'coding_prompt_inspector_integration': False,
            'installed_worker_or_runtime_archive_qualified': False,
            'hard_native_session_budget_enforced': False,
            'provider_calls': 0, 'target_module_imports': 0, 'training_steps': 0, 'prover_invocations': 0,
            'provider_total_token_reduction_established': False,
            'learned_codebase_ir_trained': False,
            'lean_projection_compiled': False,
            'source_semantic_equivalence_proved': False,
            'model_convergence_proved': False, 'task_satisfaction_proved': False,
            'task_reward_evaluated': False, 'remote_publication_performed': False},
        'remaining_work': load('next-work.json')['milestones'],
        'source_nomination_review': load('source-nomination-review.json'),
        'draft_history': {
            'retained_result': pin('result-summary-draft-01.json'),
            'reason': 'Initial result retained; final result includes the concrete read-only source-nomination/planning seam review.'},
        'evidence': [pin(name) for name in (
            'source-manifest.json', 'preservation-check.json', 'inspector-validation.json',
            'inspector-validation-03.xml', 'session-ledger-reader-validation-03.json',
            'session-ledger-reader-tests-03.xml', 'session-ledger-reader-legacy-equivalence-03.json',
            'public-native-fixture-02/summary.json', 'public-cli-qualification-01/qualification.json',
            'qualification-environment.json', 'final-independent-review.json',
            'session-ledger-downstream-review.json', 'source-nomination-review.json', 'next-work.json')]
    }
    with (STAGE / 'result-summary.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'latest_unique_passed': 95, 'public_successful_outputs': len(successful),
        'public_refusals': len(refusals), 'prior_unchanged_pin_checks': preservation['prior_unchanged_pin_checks'],
        'provider_calls': 0, 'result_sha256': pin('result-summary.json')['sha256']}))


if __name__ == '__main__':
    main()
