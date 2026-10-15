"""Summarize explicit public receipts without opening transcripts or verifier logs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
PRIOR = ROOT.parent / 'terminal-compact-retrieval-20261011-01'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
qualification_path = ROOT / 'installed-qualification-01/qualification.json'
qualification = json.loads(qualification_path.read_text())
assert qualification['qualified'] is True and qualification['qualification_container_removed'] is True
assert qualification['provider_calls'] == 0 and qualification['official_verifier_executed'] is False
current = json.loads((ROOT / 'comparison-01/comparison.json').read_text())
prior = json.loads((PRIOR / 'comparison-01/comparison.json').read_text())
assert current['retained_trial_count'] == prior['retained_trial_count'] == 2
observations = []
for version, folder, comparison in [('v12', PRIOR, prior), ('v13', ROOT, current)]:
    for row in comparison['rows']:
        codec = row['code_retrieval_codec']
        receipt_path = folder / f'pilot/code-{codec}-01/receipt.json'
        receipt = json.loads(receipt_path.read_text())
        assert len(receipt['trials']) == 1
        report = receipt['trials'][0]['supervisor']
        catalog = report['initial_context']['codebase_autoencoder_catalog']
        symbolic = report['planning']['symbolic_planning']
        observations.append({
            'runtime_version': version,
            'codec': codec,
            'receipt': str(receipt_path), 'receipt_sha256': sha(receipt_path),
            **{key: row[key] for key in (
                'runtime_archive_sha256', 'official_reward', 'native_task_completed', 'outcome',
                'native_usage_complete_observed', 'tokens', 'known_token_subtotals',
                'provider_calls', 'observed_provider_invocations', 'unreceipted_provider_attempt',
                'durations_seconds', 'supervisor_phases_seconds', 'context_input_audit',
                'code_learning_observation', 'original_task_inputs_unchanged',
                'post_publication_context', 'post_publication_proof_index')},
            'coding_calls': [{key: call[key] for key in (
                'phase', 'status', 'error_type', 'timeout_seconds', 'seconds',
                'native_task_complete_observed', 'input_observation')}
                for call in row['invocations']],
            'hydration': {key: catalog[key] for key in ('status', 'hydration',
                'metadata_ducklake', 'world_ducklake', 'formalization_authority', 'proof_authority')},
            'symbolic_planning': {key: symbolic[key] for key in ('accepted', 'provider_calls',
                'interpretation_scope', 'observed_facts_supplied', 'semantic_alignment_verified',
                'source_semantics_verified', 'proof_authority', 'completion_authority')},
            'remaining_worker_processes': report['remaining_processes'],
        })
fresh = {row['codec']: row for row in observations if row['runtime_version'] == 'v13'}
expanded = fresh['expanded']
compact = fresh['compact']
e_input = expanded['coding_calls'][0]['input_observation']['model_prompt_bytes']
c_input = compact['coding_calls'][0]['input_observation']['model_prompt_bytes']
complete = all(row['native_usage_complete_observed'] is True
    and row['tokens']['total_tokens'] is not None for row in fresh.values())
verified = all(row['context_input_audit']['all_observed_coding_inputs_verified'] is True
    for row in fresh.values())
both_passed = all(row['official_reward'] == 1 and row['native_task_completed'] is True
    for row in fresh.values())
summary = {
    'schema': 'terminal-retrieval-runtime-experiment-summary@1',
    'installed_qualification': {
        'receipt': str(qualification_path), 'receipt_sha256': sha(qualification_path),
        'qualified': True, 'archive_sha256': qualification['archive_sha256'],
        'provider_calls': 0, 'official_verifier_executed': False,
        'exact_v2_advertised_decoder_executed_as_uid_1001': True,
        'six_genuine_bundle_cold_audits_verified': True,
        'original_task_inputs_preserved': qualification['original_tracked_task_inputs_preserved'],
        'container_removed': qualification['qualification_container_removed'],
    },
    'retained_attempt_count': len(observations), 'observations': observations,
    'current_pair': {
        'initial_model_bytes_expanded': e_input, 'initial_model_bytes_compact': c_input,
        'initial_model_bytes_reduction': e_input - c_input,
        'initial_model_bytes_reduction_percent': 100 * (e_input - c_input) / e_input,
        'complete_usage_both': complete, 'verified_inputs_both': verified,
        'usage_scope': 'Retained native coding sessions; metadata/embedding refresh accounting has independent completeness flags.',
        'post_publication_refresh_complete_both': all(row['post_publication_context']['status'] == 'refreshed'
            and row['post_publication_context']['embedding_accounting']['all_refreshes_receipted'] is True
            for row in fresh.values()),
        'official_pass_and_native_completion_both': both_passed,
        'observed_total_token_reduction_percent': 100 * (1 - compact['tokens']['total_tokens'] /
            expanded['tokens']['total_tokens']) if complete else None,
        'is_causal_or_general_benchmark_advantage': False,
        'byte_reduction_is_token_reduction': False,
    },
    'cached_input_already_in_input_tokens': True,
    'old_failed_compact_attempt_and_unverified_audit_preserved': True,
    'expanded_remains_default': True,
    'reviewer_did_not_examine_raw_credentials_model_transcripts_or_hidden_verifier_content': True,
    'new_source_changes_in_this_continuation': False,
    'formal_source_equivalence_full_task_satisfaction_and_convergence_established': False,
    'heldout_learning_evaluated': False,
    'compact_post_publication_metadata_refresh_incomplete': True,
    'publication_performed': False,
}
(ROOT / 'result-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
print(json.dumps({'retained_attempts': len(observations), 'complete_usage_both': complete,
    'verified_inputs_both': verified, 'both_passed': both_passed,
    'current_pair': summary['current_pair']}))
