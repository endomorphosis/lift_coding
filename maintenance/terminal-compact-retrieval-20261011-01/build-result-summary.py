"""Project public receipt counters; never open model or verifier transcripts."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
comparison = json.loads((ROOT / 'comparison-01/comparison.json').read_text())
rows = {r['code_retrieval_codec']: r for r in comparison['rows']}
assert set(rows) == {'expanded', 'compact'} and comparison['retained_trial_count'] == 2
receipts = {}
observations = []
for codec, row in rows.items():
    path = ROOT / f'pilot/code-{codec}-01/receipt.json'
    receipt = json.loads(path.read_text())
    assert len(receipt['trials']) == 1
    report = receipt['trials'][0]['supervisor']
    catalog = report['initial_context']['codebase_autoencoder_catalog']
    symbolic = report['planning']['symbolic_planning']
    receipts[codec] = {'path': str(path), 'sha256': sha(path)}
    observations.append({
        'codec': codec,
        **{k: row[k] for k in ('official_reward', 'native_task_completed', 'outcome',
            'native_usage_complete_observed', 'tokens', 'known_token_subtotals',
            'provider_calls', 'observed_provider_invocations', 'unreceipted_provider_attempt',
            'durations_seconds', 'supervisor_phases_seconds', 'context_input_audit',
            'code_learning_observation', 'original_task_inputs_unchanged')},
        'coding_inputs': [call['input_observation'] for call in row['invocations'] if call['phase'] == 'coding'],
        'coding_calls': [{k: call[k] for k in ('phase', 'status', 'error_type', 'timeout_seconds',
            'seconds', 'native_task_complete_observed')} for call in row['invocations']],
        'hydration': {k: catalog[k] for k in ('status', 'hydrated', 'hydration',
            'metadata_ducklake', 'world_ducklake', 'formalization_authority', 'proof_authority')},
        'symbolic_planning': {k: symbolic[k] for k in ('accepted', 'provider_calls',
            'interpretation_scope', 'observed_facts_supplied', 'semantic_alignment_verified',
            'source_semantics_verified', 'proof_authority', 'completion_authority')},
        'driver_returncode': receipt['trials'][0]['agent_context']['metadata']['driver_returncode'],
        'remaining_worker_processes': report['remaining_processes'],
    })
expanded_input = rows['expanded']['invocations'][0]['input_observation']['model_prompt_bytes']
compact_input = rows['compact']['invocations'][0]['input_observation']['model_prompt_bytes']
summary = {
    'schema': 'terminal-compact-retrieval-result-summary@1',
    'runtime_archive_sha256': '63a7bc22b825b43f9e523a53c31ed3ea7ac7d6ce6a6d92f83b5f36da4a57dab6',
    'receipts': receipts,
    'comparison_sha256': sha(ROOT / 'comparison-01/comparison.json'),
    'observations': observations,
    'complete_initial_model_input_bytes': {
        'expanded': expanded_input, 'compact': compact_input,
        'reduction_bytes': expanded_input - compact_input,
        'reduction_percent': 100 * (expanded_input - compact_input) / expanded_input,
        'includes_decoder_guidance_residual_literal_instruction_and_workspace_advisory': True,
        'is_cumulative_token_savings': False,
    },
    'cached_input_already_in_input_tokens': True,
    'compact_complete_usage_unknown': True,
    'failed_attempt_retained': True,
    'causal_or_benchmark_advantage_claimed': False,
    'compact_recommended_as_default': False,
    'pilot_original_compact_input_audit_remains_unverified': True,
    'no_model_transcript_or_hidden_verifier_content_read': True,
    'followup_fixes_not_present_in_tested_runtime': True,
    'followup_source_manifest_sha256': sha(ROOT / 'source-manifest-final.json'),
    'unsupported_claims': [
        'Whole-program source-to-model semantic equivalence',
        'Natural-language intent semantic equivalence or complete task satisfaction',
        'Formal or asymptotic convergence from finite transductive reconstruction loss',
        'Held-out security/generalization accuracy',
        'Token savings or a causal codec effect from this single unequal-outcome pair',
        'Historical checkpoint freshness after publishing a source successor',
    ],
}
(ROOT / 'result-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
print(json.dumps({'result': str(ROOT / 'result-summary.json'),
    'expanded_total_tokens': rows['expanded']['tokens']['total_tokens'],
    'compact_known_subtotal': rows['compact']['known_token_subtotals']['total_tokens'],
    'model_input_reduction_percent': summary['complete_initial_model_input_bytes']['reduction_percent']}))
