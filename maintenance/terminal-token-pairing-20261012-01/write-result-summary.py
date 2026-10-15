"""Publish the Q result only from explicit final validation receipts."""
import hashlib
import json
from pathlib import Path

Q = Path(__file__).resolve().parent


def load(name):
    return json.loads((Q / name).read_bytes())


def pin(name):
    path = Q / name
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


actual = load('actual-harbor-token-pair-01/qualification.json')
resume = actual['named_report_export']['reports']['resume']
pair = resume['token_comparison']
focused = load('focused-validation.json')
preserved = load('preservation-check.json')
assert actual['qualified'] is True and actual['fresh_container_removed'] is True
assert actual['environment_call_counts'] == {'start': 1, 'stop': 1}
assert pair['qualified'] is True and pair['schema'] == 'terminal-input-token-comparison@1'
assert pair['measurements']['expanded']['tokens'] == 33873
assert pair['measurements']['compact']['tokens'] == 26285
assert pair['tokens_saved'] == 7588 and pair['token_reduction_fraction'] == 7588 / 33873
assert pair['provider_usage_measured'] is False and pair['provider_invocations_created'] == 0
assert focused['qualified'] is True and focused['distinct_executed_passed_cases'] == 100
assert preserved['all_checks_passed'] is True and len(preserved['checks']) == 1760
reviews = ['static-runtime-independent-review.json', 'focused-validation-independent-review.json',
    'focused-aggregation-independent-review.json', 'actual-token-comparison-independent-review.json',
    'actual-lifecycle-independent-review.json', 'package-independent-review.json']
for name in reviews:
    value = load(name)
    assert value.get('review_passed', value.get('qualified', value.get('passed'))) is True, name
    assert not value.get('blocking_findings', value.get('blockers', [])), name
sources = load('source-manifest.json')
value = {'schema': 'terminal-token-pair-result-summary@1', 'qualified': True,
    'increment': 'Measure complete rendered router task input tokens from one exact native observer capture.',
    'source_changes': sources['files'],
    'behavior': ['Default context-audit replay keeps its existing output and role.',
        'Optional private capture exposes verified replay components and final witness guards only to the local comparator.',
        'One genuine compact observation is independently replayed; the expanded counterfactual uses the same signed source, requirements, catalog, residual and workspace.',
        'Pinned local BPE bytes, vocabulary, pattern and special-token table determine whole-string counts with exact UTF-8 roundtrip.',
        'Final state/public artifact witnesses are rechecked after both counts; no packet contents or synthetic provider observations are exported.'],
    'measurement': {**{key: pair[key] for key in ('measurements', 'tokens_saved', 'token_reduction_fraction',
        'byte_savings', 'tokenizer', 'transports', 'input_scope', 'excluded_usage', 'bindings', 'checks')},
        'observed_arm': 'compact', 'counterfactual_arm': 'expanded', 'expanded_arm_dispatched': False,
        'local_input_token_savings_established': True, 'provider_native_tokenizer_equivalence_established': False,
        'token_comparison_seconds': resume['token_comparison_seconds'],
        'comparison_is_separate_after_driver_stop': True, 'comparison_in_official_agent_budget_claimed': False},
    'validation': {'distinct_final_focused_passes': 100, 'skipped': 0, 'errors': 0, 'failures': 0,
        'duplicate_cases': 0, 'original_capture_count': 1, 'new_source_count': 2,
        'preservation_checks': 1760, 'sealed_prior_entries_rechecked': 77,
        'prior_logical_row_occurrences_rechecked': 1667,
        'runtime_archive_source_members': 2, 'test_members_excluded': 1,
        'actual_imported_modules_joined_to_archive': len(actual['installed_import_provenance']['records']),
        'source_immutability_throughout_test_execution_proved': False,
        'unit_ordering_admission_and_catalog_stubs_are_labeled': True,
        'fresh_actual_installed_signed_replay_qualified': True},
    'actual_lifecycle': {'environment_start_count': 1, 'environment_stop_delete_count': 1,
        'fresh_container_removed': True, 'observer_lifecycle_qualified': actual['lifecycle']['qualified'],
        'exact_rendered_input_replay_verified': actual['rendered_model_input_replay_verified'],
        'capture_unchanged_after_stop': resume['observer_stop']['capture_unchanged_after_stop'],
        'original_bottle_preserved': actual['original_bottle_preserved'], 'original_head_ancestor': actual['old_head_ancestor'],
        'active_budget': resume['active_budget'], 'whole_qualification_seconds': actual['seconds'],
        'controller_agent_processing_seconds': actual['lifecycle']['controller_agent_processing_seconds'],
        'setup_seconds': actual['lifecycle']['setup_seconds'], 'teardown_seconds': actual['lifecycle']['teardown_seconds'],
        'task_completed': actual['lifecycle']['task_completed'], 'native_task_state': resume['task_state']},
    'training_observation': {key: resume['codebase_autoencoder'][key] for key in
        ('domain', 'source_count', 'sample_count', 'epochs_completed', 'receipt_sha256', 'checkpoint_sha256', 'authority')},
    'training_metrics': {key: resume['codebase_autoencoder']['metrics'][key] for key in
        ('before_reconstruction_loss', 'after_reconstruction_loss', 'epochs', 'native_kernel_calls',
            'seed', 'microbatch_count', 'training_scope', 'holdout_evaluated')},
    'claims_not_established': {'provider_total_session_token_savings': False, 'provider_usage_or_billing_complete': False,
        'full_task_satisfaction': False, 'source_to_model_equivalence': False, 'global_model_convergence': False,
        'official_whole_wall_budget': False, 'learned_IR_or_retrieval_is_proof': False},
    'limitations': ['This is one public Bottle task and one pinned local tokenizer; no population-wide advantage is claimed.',
        'The expanded arm is a checked counterfactual from the same capture, not an independently dispatched observation.',
        'Provider harness/system context, tools, retries, output and other turns are outside the measured packet.',
        'Requirements-context CID is reconstructed and checked by the signed loader/audit, but the safe export lacks a second independent scalar CID for a direct post-deletion equality check.',
        'Agent active-processing accounting excludes report publication and comparison; no official whole-entrypoint wall qualification.',
        'Training loss improved in finite transductive training; no holdout, source equivalence or convergence theorem was established.'],
    'evidence': [pin(name) for name in ['baseline-manifest.json', 'final-source-pins.json', 'source-manifest.json',
        'patch-qualification.json', 'runtime-archive/manifest.json', 'runtime-archive-verification.json',
        'focused-validation.json', 'preservation-check.json', 'actual-harbor-token-pair-01/qualification.json',
        *reviews, 'next-work.json']],
    'proof_authority': False, 'execution_authority': False, 'completion_authority': False}
assert value['validation']['actual_imported_modules_joined_to_archive'] == 24
with (Q / 'result-summary.json').open('x') as stream:
    stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')
print(json.dumps({'qualified': True, 'tokens_saved': pair['tokens_saved'], 'focused_passes': 100}))
