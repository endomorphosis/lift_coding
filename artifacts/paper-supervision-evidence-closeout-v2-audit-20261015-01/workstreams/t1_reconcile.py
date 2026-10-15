"""Recompute bounded T1 evidence projections; no runtime imports or execution."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent.parent))
from audit_io import Reader, OUT, write_json, write_jsonl

r = Reader('t1')
ROOT = Path('/home/barberb/lift_coding')
B = ROOT / 'artifacts/supervisor-portable-codex-worker-fix-20261014-01'
R = ROOT / 'artifacts/supervisor-retrieval-query-runtime-20261014-01'
F = ROOT / 'maintenance/terminal-frontier-runtime-20261011-01'
plan_path = ROOT / 'external/ipfs_accelerate/docs/architecture/terminal_bench_token_reduction.plan.md'
history_path = B / 'all-retained/comparison.json'
history = r.json(history_path)
paired = r.json(B / 'matched-pilot/comparison/paired.json')
binding = r.json(B / 'matched-pilot/comparison/binding-evidence.json')
pilot = r.json(B / 'pilot-result.json')
intent = r.json(B / 'matched-pilot/intent.json')
origins = r.json(B / 'runtime-campaign/canonical-host-imports.json')
freeze = r.json(B / 'runtime-campaign/released-source-freeze.json')
build = r.json(B / 'runtime-campaign/build-result.json')
retrieval = r.json(R / 'result.json')
retrieval_candidate = r.json(R / 'relocated-pilot/observation.json')
retrieval_control = r.json(R / 'matched-pilot/plain01/receipt.json')
frontier = r.json(F / 'token-reduction-summary.json')
frontier_validation = r.json(F / 'validation.json')
offline = r.json(ROOT / 'maintenance/terminal-indexed-context-20261011-01/offline-benchmark/benchmark.json')
old_partial_path = ROOT / 'artifacts/supervisor-portable-codex-20261014-01/pilot-result.json'
old_partial = r.json(old_partial_path)
final = {}
for arm in ['native01', 'packet01']:
    final[arm] = {
        'receipt': r.json(B / f'matched-pilot/{arm}/receipt.json'),
        'observation': r.json(B / f'matched-pilot/{arm}-observation.json'),
    }

def evidence(paths, tier='report'):
    return {'evidence_paths': [str(p) for p in paths], 'evidence_tier': tier,
            'evidence_hashes': {str(p): r.seen[str(p)]['sha256'] for p in paths},
            'signature_verification': 'not_performed', 'key_provenance': None,
            'behavior_independently_reexecuted': False}

def base_run(run_id, study_id, cohort):
    return {'schema': 'paper-evidence-run@1', 'run_id': run_id,
        'study_id': study_id, 'task': 'fix-code-vulnerability', 'cohort': cohort,
        'planned': None, 'registered': None, 'invoked': True,
        'timestamps': {}, 'base_source': None, 'reference_task_revision': None,
        'report_commit': None, 'executed_source_forest': None,
        'runtime_archive_sha256': None, 'runtime_archive_independently_rehashed': False,
        'actual_loaded_module_origins': None, 'model': None, 'provider': None,
        'cli_version': None, 'reasoning_effort': None,
        'sampling_parameters': None, 'served_model_revision': None,
        'requested_treatment': None, 'delivered_treatment': None, 'fallback_reason': None,
        'reward': None, 'supervisor_completed': None, 'validation_counts': None,
        'failure_category': None, 'input_tokens': None, 'output_tokens': None,
        'cached_input_tokens': None, 'reasoning_output_tokens': None,
        'total_tokens': None, 'native_usage_complete': None,
        'pipeline_usage_complete': None, 'dollars': None,
        'counter_semantics': 'input + output; cached input and reasoning output are subsets',
        'clocks': {}, 'session_binding_status': 'unavailable',
        'source_policy_lease_fence_observations': {}, 'limitations': []}

runs, sessions, encoder, cross_ir = [], [], [], []
session_index = {}
def add_sessions(reconciliation, run, paths, tier='report'):
    found = reconciliation.get('sessions', [])
    run['session_binding_status'] = 'retained_native_session_ids' if found else 'unavailable'
    for s in found:
        sid = s.get('thread_id')
        if not sid:
            continue
        key = (s.get('provider'), sid, s.get('workspace_binding_sha256'))
        if key in session_index:
            prior = session_index[key]
            assert prior['usage'] == s.get('known_counter_subtotals')
            prior['run_ids'] = sorted(set(prior['run_ids'] + [run['run_id']]))
            continue
        row = {'schema': 'paper-evidence-session@1', 'session_id': sid,
               'run_ids': [run['run_id']] if run['run_id'] else [],
               'audit_observation_ids': [run['audit_observation_id']] if run.get('audit_observation_id') else [],
               'study_ids': [run['study_id']],
               'provider': s.get('provider'), 'model': s.get('model'),
               'invocation_ids': s.get('invocation_ids'),
               'workspace_binding_sha256': s.get('workspace_binding_sha256'),
               'selected_rollout_sha256': s.get('selected_rollout_sha256'),
               'selected_observation_ordinal': s.get('selected_observation_ordinal'),
               'observed_token_count_records': s.get('observed_token_count_records'),
               'usage': s.get('known_counter_subtotals'),
               'strict_usage_complete_reported': s.get('strict_usage_complete'),
               'status': s.get('status'), 'reasons': s.get('reasons'),
               'counter_semantics': 'final reconciled cumulative input + output once per native session',
               'cached_and_reasoning_tokens_are_subsets': True,
               'native_reconciler_rerun': False, 'raw_native_log_reinspected': False,
               'provider_usage_authenticated': False,
               **evidence(paths, tier)}
        sessions.append(row)
        session_index[key] = row

final_ids = {value['receipt']['trials'][0]['trial']: arm for arm, value in final.items()}
for h in history['rows']:
    run = base_run(h['trial'], 'T1', 'nine-retained-attempts-across-revisions')
    run.update({
        'requested_treatment': h.get('configured_input_variant'),
        'reward': h.get('official_reward'), 'supervisor_completed': h.get('native_task_completed'),
        'exception_type': h.get('exception_type'),
        'failure_category': 'failed_without_verifier_reward_and_missing_usage' if h.get('official_reward') is None else None,
        'runtime_archive_sha256': h.get('runtime_archive_sha256'),
        'model': h.get('model'), 'provider': 'codex_cli', 'cli_version': h.get('cli_version'),
        'reasoning_effort': h.get('reasoning_effort'),
        'native_usage_complete': h.get('native_usage_complete_observed'),
        'input_tokens': h['tokens'].get('input_tokens'), 'output_tokens': h['tokens'].get('output_tokens'),
        'cached_input_tokens': h['tokens'].get('cached_input_tokens'), 'total_tokens': h['tokens'].get('total_tokens'),
        'source_receipts_reported': h.get('source_receipts'),
        'doctor_participation': h.get('doctor_observation'),
        'index_participation': h.get('indexed_context_observation'),
        'initial_index_participation': h.get('initial_indexed_context_observation'),
        'clocks': {'outer_receipt_invocation_seconds': [v.get('invocation_seconds') for v in h.get('source_receipts', [])],
                  'trial_durations_seconds': h.get('durations_seconds'),
                  'supervisor_seconds': h.get('supervisor_seconds'),
                  'supervisor_phases_seconds': h.get('supervisor_phases_seconds'),
                  'clock_scopes_overlap_and_are_not_added': True},
        **evidence([history_path]),
    })
    rec = h.get('usage_accounting', {}).get('reconciliation', {})
    run['reasoning_output_tokens'] = rec.get('known_counter_subtotals', {}).get('reasoning_output_tokens')
    paths = [history_path]
    if h['trial'] == 'fix-code-vulnerability__6VzktdR':
        run['delivered_treatment'] = 'native_fallback'
        run['fallback_reason'] = 'plan reports utf8-div4 complete-message estimate native15800 < packet16039'
        run['limitations'].append('Delivered fallback established by retained plan, not independently replayed here.')
        run.update(evidence([history_path, plan_path]))
    if h['trial'] in final_ids:
        arm = final_ids[h['trial']]
        q = final[arm]['receipt']; obs = final[arm]['observation']; sup = q['trials'][0]['supervisor']
        paths += [B / f'matched-pilot/{arm}/receipt.json', B / f'matched-pilot/{arm}-observation.json', B / 'pilot-result.json']
        run.update(evidence(paths, 'original_record_and_reconstructed_join'))
        run['requested_treatment'] = h['configured_input_variant']
        run['delivered_treatment'] = pilot['observed_arms'][arm]['actual_representation']
        run['planned'] = True
        run['timestamps'] = {'plan_frozen_at': intent['frozen_at'], 'observed_at_ms': sup.get('observation', {}).get('captured_at_ms')}
        run['base_source'] = paired['assigned_tasks'][0]['tree_id']
        run['acceptance_binding'] = paired['assigned_tasks'][0]['acceptance_binding']
        run['caller_lifecycle'] = {k: {j: sup.get(k, {}).get(j) for j in ['schema', 'status', 'operation', 'tree_id', 'objective_id', 'audit_receipt_id']} for k in ['start', 'stop']}
        run['task_state'] = sup.get('task_state')
        run['doctor_dispatch_policy'] = q.get('doctor_dispatch_policy')
        run['planning_strategy'] = q.get('planning_strategy')
        run['input_delivery_observations'] = {k: obs.get(k) for k in ['coding_input_audit', 'coding_input_census', 'semantic_decision_input_audit', 'nomination_delivery']}
        run['source_policy_lease_fence_observations'] = {'owner_bindings': obs.get('semantic_decision_owner_bindings'), 'source_freshness_revalidated': False, 'lease_and_fence_independently_checked': False}
        run['first_coding_user_message_bytes'] = pilot['observed_arms'][arm]['first_coding_user_message_bytes']
        run['coding_tool_calls'] = pilot['observed_arms'][arm]['coding_tool_calls']
        run['dialogue_attempt_count'] = pilot['observed_arms'][arm].get('dialogue_attempt_count')
        run['expansion_count'] = pilot['observed_arms'][arm].get('expansion_count')
        run['intent_preplanning'] = sup.get('intent_preplanning')
        run['host_build_module_origin_evidence'] = str(B / 'runtime-campaign/canonical-host-imports.json')
        run['executed_source_forest'] = {'status': 'partial_selected_file_hashes_not_complete_import_forest', 'source_freeze_evidence': str(B / 'runtime-campaign/released-source-freeze.json'), 'complete_import_closure_claimed': False}
        for stage in ['IntentIR', 'CodebaseIR', 'SecurityIR', 'LegalIR', 'UI/UX IR', 'joined_counterexample_check', 'separately_authorized_action']:
            status = 'unavailable/unsupported'; details = {}
            if stage == 'IntentIR':
                status = 'actually_invoked'
                details = {'stage_outcome': 'fail_open_no_checkpoint', 'learned_inference_established': False, **sup.get('intent_preplanning', {})}
            elif stage == 'CodebaseIR':
                status = 'actually_invoked'
                details = {'stage_outcome': 'indexed preparation and local security-code@1 adaptation reported', 'formal_translation_authority': False, 'complete_codebase_formalization_established': False, 'code_learning': h.get('code_learning_observation')}
            elif stage == 'separately_authorized_action':
                status = 'actually_invoked'
                details = {'start_stop_receipts': run['caller_lifecycle'], 'supervisor_completed': run['supervisor_completed'], 'independent_authorization_reverification': False}
            cross_ir.append({'study_id': 'T1', 'run_id': run['run_id'], 'stage': stage, 'status': status, 'details': details, **evidence(paths, 'original_record_and_reconstructed_join')})
        run['limitations'].append('Selected host imports were observed during packaging; complete live worker import closure was not recovered.')
        rec = sup.get('provider_usage_accounting', {}).get('reconciliation', rec)
        assert q['trials'][0]['reward']['reward'] == run['reward']
        assert sup['task_completed'] == run['supervisor_completed']
        assert r.seen[str(B / f'matched-pilot/{arm}/receipt.json')]['sha256'] == h['source_receipts'][0]['sha256']
    add_sessions(rec, run, paths, run['evidence_tier'])
    learn = h.get('code_learning_observation')
    if learn:
        encoder.append({'domain': learn.get('domain'), 'study_id': 'T1', 'run_id': run['run_id'],
            'checkpoint_sha256_reported': learn.get('checkpoint_sha256'), 'checkpoint_bytes_rehashed': False,
            'parent_checkpoint_sha256': None, 'training_data_source_inventory': None,
            'train_validation_holdout_groups': None, 'clone_controls': None, 'rights_provenance': None,
            'optimizer_hyperparameters': None, 'actual_updates': None, 'epochs_completed': learn.get('epochs_completed'),
            'sample_count': learn.get('sample_count'), 'training_elapsed_seconds': learn.get('training_elapsed_seconds'),
            'hardware_memory': None, 'embedding_tokenizer_decoder_versions': None,
            'holdout_evaluated': learn.get('holdout_evaluated'), 'formal_translation_authority': learn.get('formal_translation_authority'),
            'reconstruction_loss_before': learn.get('reconstruction_loss_before'),
            'reconstruction_loss_after': learn.get('reconstruction_loss_after'),
            'independent_qualification': 'unavailable; training reconstruction is not semantic/security accuracy',
            'runtime_inference_consumption_proof': None, 'new_training_steps_after_admission': learn.get('new_training_steps_after_admission'),
            'receipt_sha256_reported': learn.get('receipt_sha256'), 'amortization_horizon': None,
            'limitations': ['Do not infer 384D head, LegalIR transfer, training of other domains, or proof authority from this descriptor.'],
            **evidence(paths, run['evidence_tier'])})
    run['limitations'] += ['No model run or hidden-verifier execution repeated; retained reward remains observed reward.', 'No complete pipeline cost, billing settlement, or provider authentication established.']
    runs.append(run)

uninvoked = base_run(None, 'T1', 'portable-codex-partial-pair')
uninvoked.update({'audit_slot_id': 'portable-codex-20261014-01-packet01', 'planned': True,
    'registered': None, 'invoked': False, 'requested_treatment': 'decision-packet',
    'failure_category': 'not_invoked_after_native_worker_setup_failure',
    **evidence([old_partial_path], 'report')})
runs.append(uninvoked)

for arm in ['control', 'candidate']:
    obs = retrieval['attempt_population'][arm]
    run = base_run(retrieval_control['trials'][0]['trial'] if arm == 'control' else None, 'T1-retrieval', 'query-reference-sequential-pair')
    run.update({'audit_observation_id': f'T1-retrieval-{arm}', 'requested_treatment': 'plain_packet' if arm == 'control' else 'retrieval_query_reference',
        'delivered_treatment': None, 'reward': obs['reward'], 'supervisor_completed': obs['task_completed'],
        'runtime_archive_sha256': retrieval['runtime']['archive_sha256'],
        'model': retrieval['attempt_population']['model'], 'provider': retrieval['attempt_population']['provider'],
        'cli_version': '0.158.0', 'reasoning_effort': 'high',
        'input_tokens': obs['native_usage']['input_tokens'], 'output_tokens': obs['native_usage']['output_tokens'],
        'cached_input_tokens': obs['native_usage']['cached_input_tokens'], 'total_tokens': obs['native_usage']['total_tokens'],
        'native_usage_complete': obs['native_usage']['complete_native_usage'],
        'failure_category': 'dialogue_ValueError_and_reward_zero_source_guard_failed' if arm == 'control' else 'historical_input_audit_timeout_delivery_unverified',
        'limitations': ['No eligible accepted-task paired savings; failed control retained.', 'Candidate actual query-reference delivery remains unknown after timed-out audit and missing retained CAS/native parents.', 'Later host changes do not establish precise container rejection cause.'],
        **evidence([R / 'result.json', R / ('matched-pilot/plain01/receipt.json' if arm == 'control' else 'relocated-pilot/observation.json')], 'original_record_and_reconstructed_join')})
    rec = retrieval_control['trials'][0]['supervisor']['provider_usage_accounting']['reconciliation'] if arm == 'control' else retrieval_candidate['candidate_usage']['reconciliation']
    run['reasoning_output_tokens'] = rec['known_counter_subtotals']['reasoning_output_tokens']
    add_sessions(rec, run, [Path(p) for p in run['evidence_paths']], run['evidence_tier'])
    runs.append(run)

for mode, obs in frontier['modes'].items():
    run_id = Path(obs['report_path']).parent.parent.name
    run = base_run(run_id, 'T1-frontier-lead', 'concurrent-intent-transport-pair')
    run.update({'requested_treatment': mode, 'delivered_treatment': obs.get('actual_intent_projection', {}).get('transport') if obs.get('actual_intent_projection') else None,
        'reward': obs['official_reward'], 'supervisor_completed': obs['native_task_completed'],
        'runtime_archive_sha256': frontier['runtime_archive_sha256'],
        'native_usage_complete': obs['native_usage_complete_observed'],
        'input_tokens': obs['tokens']['input_tokens'], 'output_tokens': obs['tokens']['output_tokens'],
        'cached_input_tokens': obs['tokens']['cached_input_tokens'], 'total_tokens': obs['tokens']['total_tokens'],
        'clocks': {'supervisor_phases_seconds': obs['phases_seconds'], 'clock_scopes_overlap_and_are_not_added': True},
        'failure_category': 'exact_input_audit_timeout',
        'input_delivery_observations': obs['context_input_audit'],
        'source_report_path_reported': obs['report_path'], 'source_report_sha256_reported': obs['report_sha256'],
        'initial_code_autoencoder': obs['initial_code_autoencoder'],
        'limitations': ['Original per-run supervisor report not separately read in 26-file bound.', 'Native session identities not recovered from selected summary.', 'No independent exact model-input reconstruction despite compact roundtrip and reported prompt hashes.', 'Seven broader security-profile failures retained; measured-path reachability not established by this audit.'],
        **evidence([F / 'token-reduction-summary.json', F / 'validation.json'])})
    runs.append(run)

known = sum(h['tokens']['total_tokens'] for h in history['rows'] if h['tokens']['total_tokens'] is not None)
arith = []
for run in runs:
    if run['total_tokens'] is not None:
        ok = run['input_tokens'] + run['output_tokens'] == run['total_tokens']
        assert ok
        arith.append({'run_id': run['run_id'], 'audit_observation_id': run.get('audit_observation_id'), 'input_plus_output_equal_total': ok})
assert known == pilot['all_history_known_observed_token_subtotal']
assert len(history['rows']) == 9
assert sum(h['tokens']['total_tokens'] is None for h in history['rows']) == 3
for arm, final_arm in [('baseline', 'native01'), ('candidate', 'packet01')]:
    assert sum(s['known_counter_subtotals']['total_tokens'] for s in paired[arm]['usage']['sessions']) == pilot['observed_arms'][final_arm]['usage']['total_tokens']
    assert r.seen[str(B / f'matched-pilot/{final_arm}/receipt.json')]['sha256'] == pilot['observed_arms'][final_arm]['receipt_sha256']
assert r.seen[str(B / 'all-retained/comparison.json')]['sha256'] == pilot['all_history_report_sha256']
assert r.seen[str(B / 'matched-pilot/comparison/paired.json')]['sha256'] == pilot['paired_report_sha256']
assert build['archive_sha256'] == pilot['archive_sha256'] == intent['archive_sha256']

findings = {
    'schema': 'paper-t1-evidence-findings@1', 'objective': 'paper-supervision-evidence-closeout-v2',
    'scope': 'Direct local read-only audit authorized; no supervisor state mutation or new execution.',
    'read_files': len(r.seen), 'read_bytes': sum(v['bytes'] for v in r.seen.values()),
    'studies': [
        {'study_id': 'T1', 'population': 'nine historical invoked attempts across different revisions, plus one known uninvoked slot', 'final_pair_task': 'fix-code-vulnerability', 'mechanism': 'actually delivered decision packet @2', 'native_harness_baseline': False},
        {'study_id': 'T1-retrieval', 'population': 'one failed control and one successful later query-reference candidate', 'delivery_qualified': False},
        {'study_id': 'T1-frontier-lead', 'population': 'one concurrently executed expanded/compact pair', 'delivery_qualified': False},
        {'study_id': 'T1-offline-indexed-lead', 'population': 'three authored synthetic fixtures', 'benchmark_execution': False, 'provider_calls': 0},
        {'study_id': 'T1-python-view-lead', 'population': 'authored transport sessions', 'benchmark_execution': False, 'provider_calls': 0},
    ],
    'arithmetic': {'checks': arith, 'nine_trial_known_subtotal': known, 'complete_history_total': None,
        'known_usage_trials': 6, 'missing_usage_trials': 3,
        'final_pair_delta': 720840 - 445333, 'final_pair_reduction_fraction': (720840 - 445333)/720840,
        'first_message_byte_reduction_fraction': (63104 - 56442)/63104,
        'retrieval_pair_total': 508303 + 548438,
        'frontier_pair_delta': 565786 - 402169,
        'frontier_reduction_fraction': (565786 - 402169)/565786,
        'scope': 'Recomputed arithmetic over retained counters only, not independent usage authenticity or behavioral reexecution.'},
    'integrity_joins': {'two_original_final_receipt_hashes_match_reports': True, 'all_retained_hash_matches_pilot': True,
        'paired_report_hash_matches_pilot': True, 'archive_pin_agrees_in_build_intent_pilot': True,
        'archive_bytes_rehashed': False, 'complete_import_forest_recovered': False, 'signature_verification': 'not_performed'},
    'host_build_module_origins': origins,
    'source_runtime': {'report_commit': None, 'report_current_file': str(plan_path),
        'runtime_archive_sha256_reported': build['archive_sha256'], 'runtime_archive_bytes_reported': build['archive_bytes'],
        'selected_source_freeze': str(B / 'runtime-campaign/released-source-freeze.json'),
        'complete_import_closure_claimed': freeze['complete_import_closure_claimed'],
        'actual_trial_worker_loaded_origins': None, 'runtime_manifest_not_read_reason': '6,319,244 bytes exceeds 2 MiB per-file bound'},
    'contradictions_and_qualifications': [
        {'claim': 'Configured packet in earlier278471/404456 comparison demonstrates compression', 'finding': 'Contradicted: candidate delivered native fallback because local estimate preferred native.', 'evidence_paths': [str(plan_path), str(history_path)]},
        {'claim': '38.22% session reduction equals prompt compression effect', 'finding': 'Unsupported: first message differs10.56%, tool calls13vs9, caches and trajectories differ; one sequential pair.', 'evidence_paths': [str(B / 'pilot-result.json')]},
        {'claim': 'All final candidate input measurement interfaces complete', 'finding': 'Generic coding_input_census unavailable; separate coding-input and historical decision-dialogue audits verified. Preserve both fields.', 'evidence_paths': [str(B / 'matched-pilot/packet01-observation.json')]},
        {'claim': 'Whole history uses2523452 tokens', 'finding': 'Only six known totals in nine retained attempts; three missing usage failures and uninvoked slot preserved.', 'evidence_paths': [str(history_path), str(old_partial_path)]},
        {'claim': '28.9% lead proves exact source-to-model equivalence', 'finding': 'Both3-second exact-input audits timed out. Hashes, sizes and compact roundtrip do not replace final-input audit.', 'evidence_paths': [str(F / 'token-reduction-summary.json')]},
        {'claim': '71 focused passes establish full security profile qualification', 'finding': 'Broader suite82passed7failed6skipped; absent Operation.SECURITY_ADVISE registration before cache path. Exact measured-path dependency requires further read-only caller trace.', 'evidence_paths': [str(F / 'validation.json')]},
        {'claim': 'Compact source references beat a native-reference baseline', 'finding': 'Six-read authored comparison compact47816bytes versus native refs47593; compact overhead223bytes, and one-read overhead633bytes.', 'evidence_paths': [str(ROOT / 'artifacts/supervisor-python-code-view-session-20261012/README.md')]},
        {'claim': 'T1 exercised a trained IntentIR and complete policy joins', 'finding': 'Original final receipts show intent preplanning fail_open_no_checkpoint; LegalIR/UIUX/counterexample joins not established by recovered trial callers.', 'evidence_paths': [str(B / 'matched-pilot/native01/receipt.json'), str(B / 'matched-pilot/packet01/receipt.json')]},
    ],
    'offline_indexed_lead': offline,
    'frontier_validation': frontier_validation,
    'missing_evidence': [
        {'field': 'Original usage receipts for3 historical failures', 'paths': [h['source_receipts'][0]['path'] for h in history['rows'] if h['tokens']['total_tokens'] is None], 'reason': 'Retained aggregate records missing usage; raw original failures not separately read within26-file allocation; absence of aggregate counters is not proof no provider work occurred.', 'smallest_remedy': 'Read those named receipts/declared safe diagnostics under a new bounded read allocation, keeping unknown totals if no trustworthy observation.'},
        {'field': 'Complete experiment source forest and runtime archive byte rehash', 'paths': [str(B / 'runtime-campaign/runtime/manifest.json'), str(B / 'runtime-campaign/runtime/runtime.tar.gz')], 'reason': '6.3MB manifest and1.35GB archive exceed bounded inspection size; partial source pins/build origins recovered.', 'smallest_remedy': 'Propose separately bounded streaming metadata/hash validation; no runtime execution needed.'},
        {'field': 'Retrieval candidate original Harbor trial ID', 'paths': [str(R / 'relocated-pilot/observation.json')], 'reason': 'Selected observation binds native sessions but lacks original Harbor trial ID.', 'smallest_remedy': 'Follow retained relocation execution receipt path read-only; do not invent identity.'},
        {'field': 'Retrieval candidate exact delivered query reference', 'paths': [str(R / 'diagnostics/candidate-query01-retained-diagnostic.json')], 'reason': 'Final report says audit_timeout and native state/capsule/CAS parents not retained after container cleanup.', 'smallest_remedy': 'Retain unknown historical delivery; prospective separately approved trial with audit custody only if needed.'},
        {'field': 'All registered/uninvoked slots outside named portable-codex packet', 'paths': [str(B / 'matched-pilot/intent.json')], 'reason': 'Only named bounded cohort searched; no global experiment registry census.', 'smallest_remedy': 'Read named prior intentions/registrations under further bounded allocation.'},
        {'field': 'Frontier18 recovered hits and seven-failure measured-path reachability', 'paths': [str(F / 'installed-qualification-01/qualification.json'), str(F / 'deployment-cache-validation.json')], 'reason': 'Existing selected validation summary supports failureclass but not caller reachability or18hit count;26-file bound reached.', 'smallest_remedy': 'Inspect the named receipts and relevant archived caller without executing tests.'},
        {'field': 'General restoration coverage', 'paths': [str(B / 'matched-pilot/packet01-observation.json')], 'reason': 'Historical packet/native input replay reported verified; no general invertible editable whole-codebase mapping established.', 'smallest_remedy': 'Limit claim to recorded packet/input restoration; broader restoration is a separate proposed qualification.'},
    ],
    'search_routes': ['Filename-only named matched-pilot/all-retained roots', 'Current token-reduction plan selected numerical-result passages', 'Named maintenance frontier/indexed summaries', 'Named Python code-view README', 'Named retrieval result and relocation observation'],
    'edges': [
        {'relation': 'reports-on', 'from': str(B / 'pilot-result.json'), 'to': [str(B / f'matched-pilot/{a}/receipt.json') for a in final]},
        {'relation': 'derived-from', 'from': 'T1 final arithmetic', 'to': str(B / 'matched-pilot/comparison/paired.json')},
        {'relation': 'same-session-as', 'from': str(history_path), 'to': str(B / 'matched-pilot/comparison/paired.json'), 'scope': 'final four native session identities only; deduplicated'},
        {'relation': 'supersedes-configuration', 'from': str(B / 'matched-pilot/intent.json'), 'to': str(old_partial_path), 'replaces_original_observations': False},
        {'relation': 'contradicts', 'from': str(R / 'result.json'), 'to': 'claim of independently verified retrieval-reference savings'},
    ],
    'claims': [
        {'claim_id': 'T1-final-observed-pair', 'claim': 'One matched task pair delivered packet@2, both passed, observed720840vs445333tokens.', 'evidence_tier': 'original_record_and_reconstructed_join', 'evidence_paths': [str(B / 'matched-pilot/comparison/paired.json'), str(B / 'matched-pilot/comparison/binding-evidence.json'), str(B / 'pilot-result.json')], 'limitations': 'No causal, generalized, full pipeline cost or billing conclusion.'},
        {'claim_id': 'T1-history-incomplete', 'claim': 'Nine invoked attempts: six pass and three missing-usage failures;2523452knownsubtotal only.', 'evidence_tier': 'report', 'evidence_paths': [str(history_path)], 'limitations': 'Different revisions, not repeated samples of final policy.'},
    ],
}
write_jsonl('workstreams/t1_runs.jsonl', runs)
write_jsonl('workstreams/t1_sessions.jsonl', sessions)
write_jsonl('workstreams/t1_cross_ir_trace.jsonl', cross_ir)
write_jsonl('workstreams/t1_encoder_deployments.jsonl', encoder)
write_json('workstreams/t1_findings.json', findings)
lines = ['# T1: retained evidence reconciliation', '',
    'Read-only local recovery inspected26 hashed files (1,626,469bytes). No models, solvers, tests, builds, hidden graders or supervisor-state operations ran. These are retained observations plus fresh arithmetic/hash joins; no original run was independently reexecuted.', '',
    'The final pair is recovered at original-receipt level: native trialfix-code-vulnerability__6Cahzwm and packet trialfix-code-vulnerability__wox8jVM both record original reward1 and supervisor completion. Four distinct native sessions reconcile to720,840 and445,333 tokens. The candidate delivered decision_packet@2, one coding dialogue and zero expansions. Build, intent and result agree on archivef89c7ace1f4387bcb020f223758609dac607c8e6258c208189bbd8dec2f652f8; archive bytes were not rehashed.', '',
    'The observed difference is275,507tokens (38.2203%). First coding message bytes differ63,104→56,442 (10.5572%), and coding tools13→9; cache/input trajectories differ. The session difference cannot be assigned solely to task-text deduplication, interpreted as a general causal benefit, or pooled with unlike revisions. Cached input652,032/390,144 is already included in input. The baseline here is native-input supervisor, not native Codex harness.', '',
    '| Trial | Requested | Reward | Total tokens | Exception |',
    '|---|---|---:|---:|---|']
for h in history['rows']:
    lines.append(f"| {h['trial']} | {h['configured_input_variant']} | {h['official_reward']} | {h['tokens']['total_tokens']} | {h['exception_type']} |")
lines += ['',
    'The six known totals sum2,523,452; three failed records have unavailable usage, never zero. The earlier278,471/404,456 successful configured-packet comparison delivered native fallback. A separate portable-codex packet slot was planned but never invoked after the native worker setup failure. These different archives/configurations are historical development attempts, not nine replications of the final treatment.', '',
    'Retained later retrieval attempts report508,303tokens/reward0 for control and548,438/reward1 for candidate. The control provider exit0 did not establish successful supervisor completion: dialogue processing raised ValueError. Source guards failed after concurrent host edits, whose causal relation to rejection is unknown. Candidate delivery remains independently unverified because its historical audit timed out and exact native/CAS parents were not retained. No eligible accepted-task savings comparison exists for those two attempts.', '',
    'The frontier lead is recovered as original local summaries:565,786 versus402,169tokens, both passing, concurrently executed. Both three-second exact-input audits timed out. Prompt hashes/sizes and compact roundtrip did not establish independent reconstruction of complete delivered model inputs. Its71focused passes coexist with broader82passes/7failures/6skips. The stated failures arise at absent Operation.SECURITY_ADVISE registration before cache code; this audit cannot establish whether that dependency touched the measured path. The18-hit lead remains unverified within this bound.', '',
    'Offline indexed fixtures reproduce17,846→8,427;32,899→8,493;62,802→8,403 local o200k_base representation counts, with0provider calls and no task solving. All omitted expansion responses increase candidate counts to17,178/30,555/56,784 before later framing/history. The saved indexed commit is242f605508c7b6ec9020388eb887798625fb561d; it is a reported implementation identity, not a runtime inferred from the current checkout.', '',
    'The Python session lead preserves the stronger native-reference control:159,553 full-native bytes,47,593 cached-native-reference bytes and47,816 compact-reference bytes at six reads. Compact is223bytes larger than native references and adds633bytes on one read. The147 finite tests and matching fixture outputs support that authored codec/broker scope; provider tokens, production tool registration and general behavioral correctness remain unavailable.', '',
    'Actual T1 intent preplanning ran before goal decomposition but both final arms report fail_open_no_checkpoint. The retained source-learning descriptor reports24epochs/358samples and lower reconstruction loss, with holdout_evaluated=false and formal_translation_authority=false. It does not establish the384D domain head, LegalIR transfer, qualified runtime semantic inference or a complete joined Intent/Codebase/Security/Legal/UIUX policy-counterexample trace. Doctor dispatch in this pair is explicitly model-only/model_router.', '',
    'Historical input and packet-round audits are reported verified, without post-publication source freshness recertification. The generic candidate coding_input_census separately remains unavailable; it must not be silently promoted by the successful specialized audit. The policy review treats one source-linked capsule as optional without proving its irrelevance or repository-wide closure. Nomination@2 and required task-text references are retained; arbitrary whole-codebase editable inversion is not established.', '',
    'Complete source-forest reconstruction remains unavailable: the6,319,244-byte runtime manifest exceeds the2MiB per-file inspection bound, and the1.35GB archive was not hashed. Selected source pins and build-time module origins remain distinct from report commit, current source and complete live worker import origins. See t1_findings.json for exact gaps and minimal remedies; t1_inputs.jsonl contains the fresh private hash inventory.', '',
    'Reproduce fresh bounded arithmetic and projections in a fresh authorized output directory using the preserved t1_reconcile.py and audit_io.py. The script uses exclusive output creation and intentionally refuses to overwrite this audit. Reproduction of provider usage authenticity requires retained original native logs; behavioral outcomes require separately approved execution.']
report = OUT / 'workstreams/t1_report.md'
with report.open('x') as f:
    f.write('\n'.join(lines) + '\n')
report.chmod(0o600)
print(json.dumps({'runs': len(runs), 'sessions': len(sessions), 'cross_ir_rows': len(cross_ir), 'encoder_rows': len(encoder), 'known_history_total': known, 'read_files': len(r.seen)}))
