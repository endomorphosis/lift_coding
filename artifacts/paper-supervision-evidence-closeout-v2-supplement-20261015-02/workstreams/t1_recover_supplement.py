"""Bounded original-record recovery. Stdlib only; no source/runtime mutation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).absolute().parent.parent))
from audit_io import Reader, OUT

parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', default=str(OUT / 'workstreams'))
args = parser.parse_args()
dest = Path(args.output_dir).absolute()
if not dest.is_relative_to(OUT) or dest.resolve() != dest:
    raise ValueError('Outputs must stay in this new supplement')
dest.mkdir(exist_ok=True, parents=True)
dest.chmod(0o700)
r = Reader('t1')
root = Path('/home/barberb/lift_coding')
old = root / 'artifacts/paper-supervision-evidence-closeout-v2-audit-20261015-01'
prior_runs_path = old / 'workstreams/t1_runs.jsonl'
prior_runs = [json.loads(line) for line in prior_runs_path.read_text().splitlines()]
prior_sessions = [json.loads(line) for line in (old / 'workstreams/t1_sessions.jsonl').read_text().splitlines()]
prior_sessions_by_id = {v['session_id']: v for v in prior_sessions}
prior_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [prior_runs_path, old / 'workstreams/t1_sessions.jsonl', old / 'workstreams/t1_findings.json']}

def emit(name, obj, jsonl=False):
    p = dest / name
    with p.open('x') as f:
        if jsonl:
            for row in obj:
                f.write(json.dumps(row, sort_keys=True) + '\n')
        elif isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.write('\n')
    p.chmod(0o600)

def ev(path):
    path = str(path)
    return {'evidence_paths': [path], 'evidence_sha256': r.seen[path]['sha256'],
            'evidence_tier': 'original_record', 'signature_verification': 'not_performed',
            'behavioral_reexecution': False, 'raw_native_logs_read': False}

runs, sessions, joins, slots = [], [], [], []
campaigns = ['supervisor-native-input-live-20261013-01', 'supervisor-nomination-publish-fix-20261014-01',
             'supervisor-task-text-projection-20261014-01', 'supervisor-portable-codex-20261014-01']
earlier = [v for v in prior_runs if v.get('source_receipts_reported') and v.get('evidence_tier') == 'report']
receipts = {}

def sessions_from_reconciliation(sup, run_id, path):
    reconciliation = (sup.get('provider_usage_accounting') or {}).get('reconciliation') or {}
    for s in reconciliation.get('sessions', []):
        sid = s.get('thread_id')
        if not sid:
            continue
        prev = prior_sessions_by_id.get(sid)
        counters = s.get('known_counter_subtotals')
        if prev:
            assert prev['usage'] == counters
        sessions.append({'session_id': sid, 'run_id': run_id,
            'invocation_ids': s.get('invocation_ids'), 'provider': s.get('provider'), 'model': s.get('model'),
            'workspace_binding_sha256': s.get('workspace_binding_sha256'),
            'selected_rollout_sha256': s.get('selected_rollout_sha256'),
            'selected_observation_ordinal': s.get('selected_observation_ordinal'),
            'counters': counters, 'status': s.get('status'),
            'strict_usage_complete_reported': s.get('strict_usage_complete'),
            'counter_semantics': 'input+output; cache and reasoning are subsets',
            'relation_to_prior': 'same-session-as' if prev else 'newly-recovered-session-binding',
            'additional_token_charge': False if prev else None,
            'native_reconciler_executed_here': False, **ev(path)})

for prev in earlier:
    parent = prev['source_receipts_reported'][0]
    path = Path(parent['path'])
    data = r.json(path)
    receipts[str(path)] = data
    assert len(data['trials']) == 1
    t = data['trials'][0]
    sup = t.get('supervisor') or {}
    meta = t.get('agent_context') or {}
    assert t['trial'] == prev['run_id']
    assert r.seen[str(path)]['sha256'] == parent['sha256']
    expected_reward = t.get('reward')
    reward = expected_reward.get('reward') if isinstance(expected_reward, dict) else None
    assert reward == prev['reward']
    accounting = sup.get('provider_usage_accounting') or {}
    total = accounting.get('report_provider_total_tokens')
    assert total == prev['total_tokens']
    if total is not None:
        assert meta['n_input_tokens'] + meta['n_output_tokens'] == total
    dialogues = [{k: d.get(k) for k in ['schema', 'status', 'selected_representation', 'native_content_tokens', 'packet_first_content_tokens', 'expansion_count']} for d in sup.get('semantic_decision_dialogues', [])]
    row = {'run_id': t['trial'], 'study_id': 'T1', 'status': 'invoked',
           'reward': reward, 'supervisor_completed': sup.get('task_completed'),
           'exception_type': t.get('exception_type'), 'supervisor_report_present': bool(sup),
           'reported_provider_invocation_record_count': len(sup.get('provider_invocations') or []),
           'provider_invocation_record_count_is_usage_or_dispatch_proof': False,
           'input_tokens': meta.get('n_input_tokens'), 'output_tokens': meta.get('n_output_tokens'),
           'cached_input_tokens': meta.get('n_cache_tokens'), 'total_tokens': total,
           'billing_verified': False, 'whole_pipeline_total': None,
           'clocks': {'outer_invocation_seconds': data.get('invocation_seconds'),
                      'trial_durations_seconds': t.get('durations_seconds'), 'nested_clocks_not_added': True},
           'dialogues': dialogues, 'prior_aggregate_hash_join': True,
           'model': data.get('model'), 'provider': 'codex_cli', 'cli_version': data.get('cli_version'),
           'reasoning_effort': data.get('reasoning_effort'),
           'configured_doctor_policy': data.get('doctor_dispatch_policy'),
           'report_commit': None, 'executed_source_forest': None, 'loaded_module_origins': None,
           'runtime_archive_sha256_from_prior': prev.get('runtime_archive_sha256'),
           'original_task_inputs_unchanged': data.get('original_task_inputs_unchanged'),
           'limitations': ['No missing counter is replaced by zero.', 'Receipt hash agreement establishes retained-byte linkage, not provider authenticity or a new behavioral result.'],
           **ev(path)}
    sessions_from_reconciliation(sup, t['trial'], path)
    runs.append(row)
    joins.append({'relation': 'reports-on', 'from': str(prior_runs_path), 'to': str(path), 'run_id': t['trial'], 'reported_sha256': parent['sha256'], 'observed_sha256': r.seen[str(path)]['sha256'], 'matches': True})

diagnostics = {
    'fix-code-vulnerability__94TTSCp': root / 'artifacts/supervisor-native-input-live-20261013-01/matched-pilot/packet01-observation.json',
    'fix-code-vulnerability__zZ44wta': root / 'artifacts/supervisor-task-text-projection-20261014-01/matched-pilot/packet01-setup-failure.json',
    'fix-code-vulnerability__coj9Jqt': root / 'artifacts/supervisor-portable-codex-20261014-01/matched-pilot/native01-shared-setup-failure.json',
}
diagnostic_keys = ['schema', 'trial', 'failure_stage', 'stage', 'exception_type', 'driver_stage_started',
    'driver_started', 'supervisor_report_present', 'provider_native_usage_available',
    'provider_attempt_metadata_present', 'provider_attempt_receipts_present',
    'provider_native_counters', 'reported_native_counters', 'unknown_usage_reported_as_zero',
    'reported_zero_provider_usage_claimed', 'raw_remote_publisher_error_retained',
    'publisher_error_retention_limitation', 'legacy_exposure_script_called_without_packaged_binding',
    'legacy_nvm_vendor_tree_required_but_absent_in_portable_mode', 'packet01_invoked',
    'standard_Codex_install_returncode', 'nomination_prepare_or_publish_started']
for row in runs:
    if row['run_id'] in diagnostics:
        p = diagnostics[row['run_id']]
        d = r.json(p)
        row['failure_diagnostic'] = {k: d[k] for k in diagnostic_keys if k in d}
        row['diagnostic_evidence'] = ev(p)

for campaign in campaigns:
    p = root / 'artifacts' / campaign / 'matched-pilot/intent.json'
    d = r.json(p)
    for arm in ['native01', 'packet01']:
        receipt_path = p.parent / arm / 'receipt.json'
        matching = [v for v in runs if v['evidence_paths'] == [str(receipt_path)]]
        assert len(matching) <= 1
        slots.append({'slot_id': campaign + '/' + arm, 'study_id': 'T1', 'task': d.get('task'),
            'planned': True, 'canonical_registration_established': False,
            'invoked': bool(matching), 'run_id': matching[0]['run_id'] if matching else None,
            'not_invoked_evidence': str(diagnostics['fix-code-vulnerability__coj9Jqt']) if not matching else None,
            'plan_frozen_at': d.get('frozen_at'), 'population': d.get('population'),
            'provider': d.get('provider'), 'model': d.get('model'),
            'archive_pin_reported_by_intent': d.get('archive_sha256'),
            'requested_treatment': 'native-input' if arm == 'native01' else 'decision-packet', **ev(p)})
assert len(slots) == 8 and sum(v['invoked'] for v in slots) == 7

retrieval_root = root / 'artifacts/supervisor-retrieval-query-runtime-20261014-01'
candidate_path = retrieval_root / 'matched-pilot/query01/receipt.json'
candidate = r.json(candidate_path)
candidate_trial = candidate['trials'][0]
candidate_sup = candidate_trial['supervisor']
candidate_id = candidate_trial['trial']
assert candidate_id == 'fix-code-vulnerability__VkepsZo'
candidate_diagnostic_path = retrieval_root / 'diagnostics/candidate-query01-retained-diagnostic.json'
cd = r.json(candidate_diagnostic_path)
pin = cd['original_artifact_pins'][str(candidate_path)]
pin_hash = pin['sha256'] if isinstance(pin, dict) else pin
assert r.seen[str(candidate_path)]['sha256'] == pin_hash
execution_path = retrieval_root / 'relocated-pilot/execution-status.json'
execution = r.json(execution_path)
candidate_usage = candidate_sup['provider_usage_accounting']['reconciliation']['known_counter_subtotals']
assert candidate_usage['total_tokens'] == 548438 == candidate_usage['input_tokens'] + candidate_usage['output_tokens']
candidate_row = {'run_id': candidate_id, 'study_id': 'T1-retrieval',
    'prior_audit_observation_id': 'T1-retrieval-candidate', 'prior_run_id_was_null': True,
    'relation': 'same-session-as', 'additional_trial': False, 'additional_token_charge': False,
    'reward': candidate_trial['reward']['reward'], 'supervisor_completed': candidate_sup['task_completed'],
    'counters': candidate_usage, 'delivered_query_reference_verified': False,
    'actual_query_reference_delivered': None,
    'audit_gap': {k: cd['audit_gap'].get(k) for k in ['cause_established', 'driver_timeout_policy', 'observer_actual_query_reference_delivered', 'stronger_actual_reference_delivery_claim_verified', 'retained_semantic_decision_input_subaudit_present']},
    'offline_replay': {k: cd['offline_historical_replay_readiness'].get(k) for k in ['available_offline_from_this_trial', 'native_state_capsule_or_cas_export_present', 'needed_inputs', 'reason']},
    'execution': {k: execution.get(k) for k in ['schema', 'started_at', 'finished_at', 'seconds', 'returncode', 'isolated_sources_verified_after', 'original_candidate_preparation_unchanged']},
    'audit_provider_calls_zero_scope': 'Audit itself made zero provider calls, not the historical trial.',
    'diagnostic_evidence': ev(candidate_diagnostic_path), 'execution_evidence': ev(execution_path), **ev(candidate_path)}
runs.append(candidate_row)
sessions_from_reconciliation(candidate_sup, candidate_id, candidate_path)
joins.append({'relation': 'same-session-as', 'from': 'prior:T1-retrieval-candidate:null-trial-id', 'to': candidate_id, 'new_trial': False, 'new_usage_charge': False, 'original_receipt_hash_matches_diagnostic': True})

frontier_root = root / 'maintenance/terminal-frontier-runtime-20261011-01'
qpath = frontier_root / 'installed-qualification-01/qualification.json'
qualification = r.json(qpath)
probe = qualification['frontier_probe']
worker = probe['worker']
assert worker['exact_deferred_native_hits_recovered'] == 18
assert len(worker['actual_emitted_cli_invocations']) == 18
assert all(v['returncode'] == 0 for v in worker['actual_emitted_cli_invocations'])
deployment_path = frontier_root / 'deployment-cache-validation.json'
deployment = r.json(deployment_path)
xml_path = root / 'maintenance/terminal-bounded-context-20261011-01/deployment-cache-validation-03.xml'
xml = ET.fromstring(r.read(xml_path))
failed = []
for case in xml.iter('testcase'):
    fail = case.find('failure')
    if fail is not None:
        content = fail.text or ''
        failed.append({'classname': case.get('classname'), 'test_name': case.get('name'),
            'failure_message': fail.get('message'), 'missing_SECURITY_ADVISE': 'SECURITY_ADVISE' in content,
            'security_autoencoder_hub_in_trace': 'security_autoencoder_hub.py' in content,
            'attribute_error_in_trace': 'AttributeError' in content})
assert len(failed) == 7
assert all(v['missing_SECURITY_ADVISE'] and v['security_autoencoder_hub_in_trace'] for v in failed)
assert r.seen[str(xml_path)]['sha256'] == deployment['checks'][1]['sha256']
frontier_live = []
for prev in prior_runs:
    if prev.get('study_id') != 'T1-frontier-lead':
        continue
    p = Path(prev['source_report_path_reported'])
    sup = r.json(p)
    assert r.seen[str(p)]['sha256'] == prev['source_report_sha256_reported']
    row = {'run_id': prev['run_id'], 'study_id': 'T1-frontier-lead',
           'reward_reported_by_prior_summary': prev['reward'],
           'official_reward_field_in_supervisor_report': sup.get('official_reward'),
           'original_verifier_result_separately_read': False,
           'supervisor_completed': sup.get('task_completed'),
           'reported_native_usage_complete_in_prior_summary': prev.get('native_usage_complete'),
           'doctor_profile': sup.get('doctor_profile'), 'doctor_profile_experimental': sup.get('doctor_profile_experimental'),
           'implementation_route': sup.get('implementation_route'), 'code_retrieval_transport': sup.get('code_retrieval_transport'),
           'semantic_transport': sup.get('semantic_transport'), 'intent_requirements_transport': sup.get('intent_requirements_transport'),
           'intent_preplanning_status': sup.get('intent_preplanning', {}).get('status'),
           'context_input_audit_status': sup.get('context_input_audit', {}).get('status'),
           'context_input_audit_reason': sup.get('context_input_audit', {}).get('reason'),
           'doctor_dispatch': {k: sup.get('doctor_dispatch', {}).get(k) for k in ['analysis_status', 'route', 'status', 'provider_calls', 'residual_work_proposals']},
           'runtime_archive_sha256_from_prior': prev['runtime_archive_sha256'],
           'relation_to_prior': 'reports-on', 'additional_trial': False, **ev(p)}
    frontier_live.append(row)
    for inv in sup.get('provider_invocations', []):
        native = inv.get('native_rollout_usage') or {}
        counters = native.get('usage') or {}
        assert counters['input_tokens'] + counters['output_tokens'] == prev['total_tokens']
        sessions.append({'session_id': native.get('thread_id'), 'run_id': prev['run_id'],
            'invocation_ids': [inv.get('invocation_id')], 'model': inv.get('model'), 'provider': inv.get('provider'),
            'counters': counters, 'rollout_sha256': native.get('rollout_sha256'),
            'native_usage_schema': native.get('schema'), 'usage_available': native.get('usage_available'),
            'task_complete_observed': native.get('task_complete_observed'),
            'strict_usage_complete_field_present': 'strict_usage_complete' in native,
            'reported_native_usage_complete_in_prior_summary': prev.get('native_usage_complete'),
            'counter_semantics': 'input+output; cached input is a subset',
            'relation_to_prior': 'newly-recovered-session-binding-for-existing-trial',
            'additional_token_charge': False, 'raw_native_logs_read': False, **ev(p)})
    runs.append(row)
frontier = {'scope': 'Retained qualification and JUnit records; no new execution',
    'authored_passive_probe': {k: probe['passive_public_fixture'].get(k) for k in ['scope', 'complete_hit_count', 'selected_hit_count', 'deferred_hit_count', 'full_context_bytes', 'frontier_context_bytes', 'selected_transport']},
    'worker': {'exact_deferred_hits_recovered': 18, 'emitted_cli_invocations': 18,
               'all_emitted_cli_returncodes_zero': True, 'provider_calls': probe.get('provider_calls'),
               'qualification_elapsed_seconds': qualification.get('elapsed_seconds'),
               'worker_elapsed_seconds': worker.get('elapsed_seconds'),
               'signed_plan_admission_claimed': qualification.get('signed_plan_admission_claimed'),
               'official_verifier_executed': qualification.get('official_verifier_executed'),
               'training_or_proving_performed': probe.get('training_or_proving_performed')},
    'production_quota_probe': {k: probe['production_quota_probe'].get(k) for k in ['scope', 'complete_hit_count', 'included_hit_count', 'omitted_hit_count', 'native_fact_rows_replayed', 'retrieval_model', 'full_context_bytes', 'frontier_context_bytes', 'selected_context_bytes', 'selected_transport', 'provider_calls']},
    'qualification_evidence': ev(qpath),
    'seven_failures': failed, 'failure_evidence': ev(xml_path),
    'deployment_validation': {k: deployment.get(k) for k in ['broader_failure', 'checks', 'focused_passed', 'provider_calls']},
    'deployment_validation_evidence': ev(deployment_path),
    'live_profile_observations': frontier_live,
    'reachability_status': 'partial',
    'reachability_conclusion': 'All seven failures concern frozen-security advice tests; both measured live reports select experimental generic Doctor and model_router, with full code retrieval and native semantic transport. This establishes different declared paths but is not a complete archived caller/import reachability proof.',
    'remaining_gap': 'Need exact archived generic-versus-frozen-security branch and loaded-module evidence to rule out shared dependency reachability; no new test needed for static inspection.',
    'not_a_task_efficacy_measurement': 'Eighteen recovered hits are an authored provider-free expansion qualification; they are not eighteen benchmark successes or measured live retrieval hits.'}

gaps = [
    {'prior_missing_entry': 1, 'field': 'Original usage receipts for3 historical failures', 'status': 'partial',
     'closed_part': 'All three original outer receipts and bounded failure diagnostics recovered and hash-bound.',
     'remaining': 'No native usage observations retained; null totals remain unknown, despite diagnostics recording failure before driver start.',
     'minimal_remedy': 'Retain missing counters; only trustworthy preexisting accounting observations could close usage completeness.'},
    {'prior_missing_entry': 3, 'field': 'Retrieval candidate original Harbor trial ID', 'status': 'closed',
     'resolution': 'fix-code-vulnerability__VkepsZo recovered from original receipt, hash-matched to diagnostic; same two native sessions and548438tokens, not an additional trial.'},
    {'prior_missing_entry': 4, 'field': 'Retrieval candidate exact delivered query reference', 'status': 'unresolved',
     'resolution': 'Original receipt and diagnostic confirm audit_timeout under at-most3-second budget; exact native state/capsule/CAS parents not retained and container absent.',
     'minimal_remedy': 'Keep historical delivery unknown; a separately approved prospective custody-qualified trial only if this missing causal evidence is essential.'},
    {'prior_missing_entry': 5, 'field': 'All registered/uninvoked slots outside named portable-codex packet', 'status': 'partial',
     'closed_part': 'Four earlier plans bind8slots/7invocations; with prior final plan the named five-configuration history has10plannedslots/9invoked/1uninvoked.',
     'remaining': 'Canonical registration receipts and all-project enrollment are not established by these local plans.',
     'minimal_remedy': 'Report bounded named cohort; inspect a specified preexisting registry export only if a broader population claim is needed.'},
    {'prior_missing_entry': 6, 'field': 'Frontier18 recovered hits and seven-failure measured-path reachability', 'status': 'partial',
     'closed_part': 'Original qualification confirms18deferred hits/18successful worker expansions in authored fixture; original JUnit identifies7frozen-security registration failures; original live reports identify generic profile/full code retrieval.',
     'remaining': 'No whole-callgraph reachability proof;18hits are not live-task retrieval efficacy.',
     'minimal_remedy': 'Static read of exact archived branch/import closure if needed, without rerunning tests.'},
    {'prior_missing_entry': 8, 'field': 'Seven earlier original receipts and original native-log verification', 'status': 'partial',
     'closed_part': 'All seven original receipt bytes hash-match prior aggregate commitments and retain outcomes/counters. With previous final pair all9original outer receipts are now recovered.',
     'remaining': 'Provider authenticity and original raw native-log reprocessing not established.',
     'minimal_remedy': 'Preserve receipt-level scope; separately bounded allowlisted native-log accounting inspection if necessary.'},
]
known_earlier_total = sum(v['total_tokens'] for v in runs if v.get('study_id') == 'T1' and v.get('total_tokens') is not None)
assert known_earlier_total == 1357279
assert known_earlier_total + 720840 + 445333 == 2523452
summary = {'schema': 'paper-t1-recovery-supplement@1', 'objective': 'paper-supervision-evidence-closeout-v2',
    'original_inputs': len(r.seen), 'original_bytes': sum(v['bytes'] for v in r.seen.values()),
    'prior_projection_hashes': prior_hashes, 'original_receipt_hash_joins': joins,
    'known_earlier_subtotal': known_earlier_total, 'known_nine_trial_subtotal_unchanged': 2523452,
    'complete_history_total': None, 'missing_usage_trials': 3,
    'new_historical_trials_added': 0, 'candidate_identity_recovered': candidate_id,
    'new_provider_calls': 0, 'new_training': False, 'new_solvers': False, 'new_builds_or_tests': False,
    'supervisor_state_mutated': False, 'old_audit_modified': False,
    'routes': ['Prior allowlisted runs -> seven exact original receipt paths',
               'Named failure observation/setup metadata', 'Four named prior launch intentions',
               'Named relocation diagnostic -> candidate original receipt and native session binding',
               'Named installed frontier qualification -> exact18hit metadata',
               'Deployment-cache validation -> exact hash-bound JUnit',
               'Prior frontier source_report_path_reported -> two original live supervisor reports'],
    'read_limit_reached': len(r.seen) == 22, 'large_runtime_archives_not_read_by_this_workstream': True}

emit('t1_run_updates.jsonl', runs, True)
emit('t1_session_updates.jsonl', sessions, True)
emit('t1_slot_inventory.jsonl', slots, True)
emit('t1_gap_status.jsonl', gaps, True)
emit('t1_frontier_qualification.json', frontier)
emit('t1_integrity_joins.json', summary)
report = '''# T1 original-record recovery supplement

This supplement inspected 22 original files through the bounded hash reader. It changes no historical outcome, token count, source pin, or prior audit. No provider, solver, build, test, training, grader, service, or supervisor-state action ran.

All seven earlier original T1 outer receipts match their prior aggregate SHA-256 commitments. Together with the already recovered final pair, all nine original outer receipts are now located and hash-joined. The four earlier successes retain 1,357,279 known tokens; adding the final pair retains the known subtotal of 2,523,452. This is not a complete history total or provider-authenticated billing.

The three failures still have no native counters or supervisor report. Their separate bounded diagnostics record failures before driver start: nomination publication raises ValueError; the legacy installer cannot resolve Node22; and portable worker setup omits the packaged native-binary binding. These diagnostics narrow the execution stage, but missing usage remains unknown rather than zero. A Harbor wrapper return code of zero did not establish task acceptance in any of these records.

The earlier configured-packet success now has original dialogue evidence for native fallback: selected_representation=native, local native estimate15,800 versus packet16,039. Its404,456tokens remain an observed native-input trajectory, not delivered-compression efficacy.

Four original prior intentions establish eight planned slots with seven invocations. Joined to the previously recovered final-pair intention, this named history comprises ten planned slots, nine invoked trials and the one uninvoked portable packet slot. This closes the named plan census, not canonical registration or an all-project enrollment census.

The retrieval candidate is now identified as fix-code-vulnerability__VkepsZo. Its original receipt matches the retained diagnostic hash and the same two native session identities previously attached to the null-ID candidate observation. Its548,438tokens are not added again. The candidate passed and completed, but exact query-reference delivery remains unknown: the final input audit timed out under an at-most-three-second limit, and native state/capsule/CAS parents were not retained after container cleanup. A zero provider-call count inside that audit describes only the auditor, not the historical trial's two calls.

The frontier qualification recovers18deferred native hits through18successful worker expansions in an authored passive source fixture. It made zero provider calls and executed no original task verifier. The separate production-quota probe returned five hits, selected two and omitted three; full context was7,992bytes versus8,860 for frontier, so it selected full transport. Eighteen recovered fixture hits must not be reported as live benchmark retrieval efficacy.

Original JUnit bytes match the deployment-validation commitment and identify all seven failures as frozen-security advice tests raising AttributeError for missing Operation.SECURITY_ADVISE in the registration path. Both actual frontier supervisor reports independently match their retained hashes and select experimental generic Doctor, model_router, full code retrieval, native semantic transport, and missing Intent checkpoint; only expanded/compact intent transport differs. This establishes profile separation, not complete callgraph unreachability of the failing shared dependency. That final static caller question remains partial. Both historical exact-input audits remain timed out.

The original frontier reports expose two native session IDs and their counters. The earlier summary's reward1 remains retained, while the supervisor report itself has official_reward=null; the separate original verifier output was not read in this allocation. The native usage envelope records usage_available/task_complete_observed, but lacks a newer strict_usage_complete field. The supplement preserves schema distinctions rather than manufacturing a stronger completeness assertion.

New JSONL rows are evidence updates for existing trials/sessions, not new trials or charges. t1_gap_status.jsonl reports closed/partial/unresolved fields and minimal remedies. No raw transcripts, argv, secrets, hidden/reference code, or candidate bodies are exported.

Reproduce in a fresh subdirectory of this supplement using:

```sh
python workstreams/t1_recover_supplement.py --output-dir "$PWD/replay-t1"
```

Run from the supplement root. Existing output files are never overwritten. This reproduces metadata projections and arithmetic only; the source reader rejects changed evidence and enforces its allocation.
'''
for a, b in {'estimate15,800':'estimate 15,800', 'packet16,039':'packet 16,039', 'Its404,456tokens':'Its 404,456 tokens', 'Its548,438tokens':'Its 548,438 tokens', 'recovers18deferred':'recovers 18 deferred', 'through18successful':'through 18 successful', 'was7,992bytes':'was 7,992 bytes', 'versus8,860':'versus 8,860', 'reward1':'reward 1'}.items():
    report = report.replace(a, b)
emit('t1_report.md', report)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha for p, sha in prior_hashes.items())
print(json.dumps({'input_files': len(r.seen), 'runs_updated': len(runs), 'sessions_updated': len(sessions),
                  'planned_slots_this_supplement': len(slots), 'gap_rows': len(gaps), 'old_projection_hashes_unchanged': True}))
