"""Join retained qualification, accounting and actual treatment observations."""
import hashlib
import json
from pathlib import Path

p = Path(__file__).parent
comparison = json.loads((p / 'comparison/comparison.json').read_text())
qualification = json.loads((p / 'installed-qualification-01/qualification.json').read_text())
assert qualification['qualified'] and qualification['qualification_container_removed']
rows = {}
for row in comparison['rows']:
    mode = row['intent_requirements_transport']
    assert mode not in rows and mode in ('expanded', 'compact')
    assert row['official_reward'] == 1 and row['native_task_completed'] is True
    assert row['native_usage_complete_observed'] is True and not row['unreceipted_provider_attempt']
    assert row['code_retrieval_transport'] == 'full' and row['semantic_transport'] == 'native'
    assert row['runtime_archive_sha256'] == qualification['archive_sha256']
    tokens = row['tokens']
    assert tokens['input_tokens'] + tokens['output_tokens'] == tokens['total_tokens']
    assert 0 <= tokens['cached_input_tokens'] <= tokens['input_tokens']
    path = next((p / 'pilot' / ('intent-' + mode + '-01') / 'jobs').glob('*/fix-code-vulnerability__*/agent/supervisor-result.json'))
    report = json.loads(path.read_text())
    calls = report['provider_invocations']
    assert len(calls) == 1 and calls[0]['phase'] == 'coding' and report['remaining_processes'] == 0
    assert report['implementation_route'] == 'model_router'
    call = calls[0]
    public = call['public_instruction']
    assert public['source_bytes'] == 3873 and public['source_sha256'] == '89b1abdf0af19399f720233b5cdf6b2e8e0ff7b6e3fe3e2a3af0d4d298a8641a'
    assert call['doctor_residual_context']['candidate_only'] is True
    if mode == 'compact':
        projection = public['intent_requirements_projection']
        assert public['schema'].endswith('@6')
        assert projection['transport'] == projection['requested_transport'] == 'compact'
        assert projection['canonical_roundtrip_verified'] is True
        assert projection['selected_block_bytes'] < projection['expanded_block_bytes']
        assert all(projection[key] is False for key in ('proof_authority', 'execution_authority', 'completion_authority'))
    initial = report['initial_context']['codebase_autoencoder']
    catalog = report['initial_context']['codebase_autoencoder_catalog']
    assert initial['proof_authority'] is False and catalog['formalization_authority'] is False
    rows[mode] = {'official_reward': row['official_reward'], 'native_task_completed': row['native_task_completed'],
        'remaining_processes': 0, 'coding_invocations': 1, 'planning_invocations': 0,
        'tokens': tokens, 'native_usage_complete_observed': True,
        'model_prompt_bytes': call['model_prompt_bytes'], 'model_prompt_sha256': call['model_prompt_sha256'],
        'native_capsule_prompt_bytes': call['native_prompt_bytes'], 'native_prompt_sha256': call['native_prompt_sha256'],
        'public_instruction_block_bytes': public['block_bytes'], 'public_instruction_schema': public['schema'],
        'actual_intent_projection': public.get('intent_requirements_projection'),
        'context_input_audit': row['context_input_audit'], 'phases_seconds': report['phases'],
        'initial_code_autoencoder': {'epochs': initial['epochs_completed'], 'checkpoint_sha256': initial['checkpoint_sha256'],
            'before_reconstruction_loss': initial['metrics']['before_reconstruction_loss'],
            'after_reconstruction_loss': initial['metrics']['after_reconstruction_loss'],
            'holdout_evaluated': initial['metrics']['holdout_evaluated'], 'proof_authority': initial['proof_authority']},
        'initial_catalog_hydration': {'status': catalog['status'], 'hydration': catalog['hydration'],
            'metadata_ducklake': catalog['metadata_ducklake'], 'world_ducklake': catalog['world_ducklake']},
        'post_publication_autoencoder': report['post_publication_autoencoder'],
        'report_path': str(path), 'report_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
assert set(rows) == {'expanded', 'compact'}
expanded, compact = rows['expanded'], rows['compact']
saved = expanded['tokens']['total_tokens'] - compact['tokens']['total_tokens']
summary = {'schema': 'terminal-intent-observed-token-comparison@1',
    'runtime_archive_sha256': qualification['archive_sha256'], 'source_change_manifest': 'source-manifest.json',
    'qualification': 'installed-qualification-01/qualification.json', 'validation': 'validation.json',
    'protocol': 'intent-comparison-protocol.json', 'comparison': 'comparison/comparison.json', 'modes': rows,
    'observed_total_token_difference': saved,
    'observed_total_token_reduction_percent': 100 * saved / expanded['tokens']['total_tokens'],
    'observed_model_prompt_byte_difference': expanded['model_prompt_bytes'] - compact['model_prompt_bytes'],
    'cached_input_is_subset_not_additional_tokens': True,
    'runs_executed_concurrently_in_independent_containers': True,
    'per_run_workers': 1, 'runtime_dependencies_and_source_controls_equal': True,
    'fresh_task_and_world_identities_preserved': True,
    'exact_model_input_independently_reconstructed': False,
    'input_audit_limitation': 'Both production three-second exact-input audits timed out; reported prompt hashes/sizes and compact native roundtrip do not replace those audits.',
    'causal_token_efficiency_claimed': False, 'general_benchmark_advantage_claimed': False,
    'general_source_to_model_equivalence_claimed': False, 'general_model_convergence_claimed': False,
    'scope': 'One observed task pair with actual coding transport, complete native cumulative usage, independent official reward and native supervisor completion; setup shares host resources.'}
(p / 'token-reduction-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
print(json.dumps({'observed_token_difference': saved, 'observed_reduction_percent': summary['observed_total_token_reduction_percent'],
                  'both_official_reward_one': True, 'both_native_completed': True}), flush=True)
