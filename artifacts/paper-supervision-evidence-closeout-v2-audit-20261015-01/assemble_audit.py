"""Standard-library-only assembly of retained evidence projections; no runtimes.

Usage: python assemble_audit.py --output /a/new/empty/directory
Inputs are this audit's workstream projections, never hidden/reference bodies.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
WS = BASE / 'workstreams'

def read_json(name):
    return json.loads((BASE / name).read_text())

def read_rows(name):
    return [json.loads(s) for s in (BASE / name).read_text().splitlines() if s]

def paths(row):
    return list(dict.fromkeys(row.get('evidence_paths', []) + [x['path'] for x in row.get('evidence', []) if 'path' in x]))

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.absolute()
    if out.resolve() != out:
        raise ValueError('No symlink output')
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Exclusive writes protect original evidence and a previously assembled audit.
    def write(name, data):
        p = out / name
        p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with p.open('x') as f:
            f.write(data)
        p.chmod(0o600)
    def js(name, data):
        write(name, json.dumps(data, indent=2, sort_keys=True) + '\n')
    def jl(name, data):
        write(name, ''.join(json.dumps(r, sort_keys=True) + '\n' for r in data))
    def tab(name, rows, fields):
        import io
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (list, dict)) else v for k, v in row.items()})
        write(name, stream.getvalue())

    findings = {k: read_json(f'workstreams/{k}_findings.json') for k in ['t1', 't2_t4', 'historical', 'cross_ir']}
    inputs = [r for p in sorted(WS.glob('*_inputs.jsonl')) for r in read_rows(str(p.relative_to(BASE)))]
    artifact_map = {}
    for r in inputs:
        key = (r['path'], r['sha256'])
        if key not in artifact_map:
            artifact_map[key] = {**r, 'workers': [], 'access_status': 'read_and_sha256_hashed',
                                 'authenticity_established': False, 'behavior_independently_reexecuted': False,
                                 'location_is_private': True, 'report_commit': None}
        artifact_map[key]['workers'].append(r['worker'])
    artifacts = sorted(artifact_map.values(), key=lambda r: (r['path'], r['sha256']))
    assert len(artifacts) <= 120
    assert sum(r['bytes'] for r in artifacts) <= 32 * 1024 * 1024
    jl('artifacts.jsonl', artifacts)
    artifact_by_path = {r['path']: r for r in artifacts}

    runs = []
    raw_observations = {}
    missing_fields = ['base_source', 'reference_task_revision', 'profile', 'cohort', 'timestamps', 'report_commit',
                      'executed_source_forest', 'actual_loaded_module_origins', 'model', 'cli_version', 'reasoning_effort',
                      'sampling_parameters', 'served_model_revision', 'requested_treatment', 'delivered_treatment',
                      'fallback_reason', 'validation_counts', 'source_parent_policy_lease_fence_bindings', 'key_provenance']
    for worker in ['t1', 't2_t4', 'historical']:
        for i, r in enumerate(read_rows(f'workstreams/{worker}_runs.jsonl')):
            key = r.get('run_id') or r.get('audit_observation_id') or f'{worker}:unbound-slot:{i + 1}'
            assert key not in raw_observations, 'Identity collision; resolve rather than silently merge'
            raw_observations[key] = r
            if worker == 't1':
                tokens = {k: r.get(k) for k in ['input_tokens', 'output_tokens', 'cached_input_tokens', 'reasoning_output_tokens', 'total_tokens']}
                reward, invoked, native_complete = r.get('reward'), r.get('invoked'), r.get('native_usage_complete')
                unit = 'benchmark_trial' if invoked else 'registered_uninvoked_slot'
                schema = r.get('counter_semantics')
            elif worker == 't2_t4':
                tokens = r.get('tokens') or {}
                reward, invoked, native_complete = r.get('official_reward'), r.get('status') == 'invoked', r.get('native_usage_complete')
                unit = 'benchmark_trial'
                schema = ('fresh input + cached input + cache-write input + output; reported completeness absent'
                          if r['study_id'] == 'X1' else 'input + output; cache and reasoning subsets')
            else:
                tokens = {'total_tokens': r.get('provider_total_tokens')}
                reward, invoked, native_complete = r.get('reward'), r.get('invoked'), None
                unit, schema = r.get('record_type'), r.get('usage_schema')
            reported_tokens = (r.get('reported_native_counts') or r.get('known_token_subtotals') or tokens)
            row = {k: r.get(k) for k in missing_fields}
            row.update(schema='paper-run-ledger@1', ledger_id=key, original_run_id=r.get('run_id'),
                       study_id=r['study_id'], task=r.get('task', r.get('task_id')), run_unit=unit,
                       planned=r.get('planned'), registered=r.get('registered'), invoked=invoked,
                       original_reward=reward, supervisor_completed=r.get('supervisor_completed', r.get('supervisor_completion')),
                       historical_accepted_node=r.get('accepted'), status=r.get('status', r.get('outcome')),
                       tokens=tokens, reported_tokens=reported_tokens, native_usage_complete=native_complete,
                       whole_pipeline_usage_complete=r.get('pipeline_usage_complete', r.get('whole_pipeline_usage_complete')),
                       usage_schema=schema, failure_category=r.get('failure_category', r.get('failure_categories')),
                       runtime_archive_sha256=r.get('runtime_archive_sha256'),
                       actual_loaded_module_origins=r.get('actual_loaded_module_origins', r.get('loaded_module_origins')),
                       participation=r.get('participation', {'doctor': r.get('doctor_participation'), 'index': r.get('index_participation')}),
                       clocks={'scope': 'separate; do not add overlapping clocks', 'reported': r.get('clocks', r.get('durations_seconds')),
                               'outer_invocation_seconds': r.get('outer_invocation_seconds', r.get('invocation_seconds')),
                               'controller_seconds': r.get('controller_seconds')},
                       evidence_paths=paths(r), evidence_tier=r.get('evidence_tier', 'see_source_observations'),
                       evidence_sha256={p: artifact_by_path[p]['sha256'] for p in paths(r) if p in artifact_by_path},
                       signature_verification='not_performed', independently_reexecuted=False,
                       limitations=r.get('limitations', []), source_observation=r, projection_worker=worker)
            runs.append(row)
    jl('runs.jsonl', runs)
    benchmark = [r for r in runs if r['projection_worker'] != 'historical']
    by_run = {r['ledger_id']: r for r in runs}
    # Distinct identity kinds prevent a provider call ID becoming an invented session.
    sessions = []
    seen_sessions = set()
    for worker in ['t1', 't2_t4', 'historical']:
        for i, r in enumerate(read_rows(f'workstreams/{worker}_sessions.jsonl')):
            sid = r.get('session_id')
            iid = r.get('invocation_id')
            kind = 'provider_session' if sid else 'provider_call_id_not_a_session'
            identity = sid or iid or f'{worker}:unbound-observation:{i+1}'
            identity_key = (kind, identity)
            assert identity_key not in seen_sessions, 'Do not double count a reused session'
            seen_sessions.add(identity_key)
            sessions.append({'schema': 'paper-session-ledger@1', 'ledger_id': f'{kind}:{identity}',
                             'identity_kind': kind, 'session_id': sid, 'invocation_id': iid,
                             'run_ids': r.get('run_ids', [r['run_id']] if r.get('run_id') else []),
                             'reported_usage': r.get('usage', r.get('reported_counts')),
                             'usage_complete': r.get('strict_usage_complete_reported', r.get('usage_complete')),
                             'evidence_paths': paths(r), 'signature_verification': 'not_performed',
                             'source_observation': r, 'combined_project_cost_authority': False})
    jl('sessions.jsonl', sessions)
    studies = findings['t1']['studies'] + findings['historical']['studies']
    for sid, label in [('T2', 'Security repair and distinct no-index predecessors'), ('T3', 'Earlier numerical comparison'),
                       ('T4', 'Later native/no-index/indexed numerical comparison'), ('X1', 'Grok source/metadata treatments')]:
        studies.append({'study_id': sid, 'label': label, 'cohorts_must_not_be_pooled': True,
                        'run_ids': [r['ledger_id'] for r in runs if r['study_id'] == sid],
                        'details': 'workstreams/t2_t4_findings.json'})
    js('studies.json', {'schema': 'paper-studies@1', 'studies': studies,
                       'missing_revision_label_map': 'H1,D1-D6,R1/R2 not invented; report-native identifiers retained',
                       'project_total_tokens': None})

    claims = []
    edges = []
    for worker, data in findings.items():
        for i, claim in enumerate(data.get('claims', [])):
            cid = claim.get('claim_id', claim.get('id', f'{worker}:{i}'))
            claims.append({'claim_id': cid, 'claim': claim.get('claim', claim.get('study_id', cid)),
                           'study_id': claim.get('study_id'), 'evidence_tier': claim.get('evidence_tier', 'see per-artifact tier'),
                           'status': claim.get('status', 'retained observation; not rerun'),
                           'evidence_paths': paths(claim), 'limitations': claim.get('limitations'), 'worker': worker})
            for p in paths(claim):
                edges.append({'from': cid, 'relation': 'derived-from', 'to': p, 'sha256': artifact_by_path.get(p, {}).get('sha256')})
        for e in data.get('edges', []):
            typ = e.get('relation', e.get('relationship', e.get('type')))
            targets = e.get('to') if isinstance(e.get('to'), list) else [e.get('to')]
            for target in targets:
                edges.append({**e, 'relation': typ, 'to': target})
    for r in runs:
        for p in r['evidence_paths']:
            edges.append({'from': p, 'relation': 'reports-on', 'to': r['ledger_id']})
    for s in sessions:
        for run in s['run_ids']:
            if s['identity_kind'] == 'provider_session':
                edges.append({'from': run, 'relation': 'same-session-as', 'to': s['ledger_id'], 'identity_kind': s['identity_kind']})
            else:
                edges.append({'from': s['ledger_id'], 'relation': 'reports-on', 'to': run,
                              'identity_kind': s['identity_kind'], 'session_correspondence': 'unavailable'})
    tab('claim_evidence_map.csv', claims, ['claim_id', 'claim', 'study_id', 'evidence_tier', 'status', 'evidence_paths', 'limitations', 'worker'])
    jl('evidence_graph.jsonl', edges)

    encoders = sum((read_rows(f'workstreams/{w}_encoder_deployments.jsonl') for w in ['t1', 't2_t4', 'cross_ir']), [])
    jl('encoder_deployment_ledger.jsonl', encoders)
    actual_ir = read_rows('workstreams/t1_cross_ir_trace.jsonl')
    domains = ['IntentIR', 'CodebaseIR', 'SecurityIR', 'LegalIR', 'UI/UX IR']
    stages = dict(zip(domains, ['prompt_to_intent', 'source_to_codebase_preparation_or_inference', 'source_to_security', 'source_to_legal', 'source_to_uiux']))
    traces = []
    for r in benchmark:
        for domain in domains:
            known = next((x for x in actual_ir if x['run_id'] == r['original_run_id'] and x['stage'].replace('UIUX', 'UI/UX') == domain), None)
            deployment = next((x for x in encoders if r['original_run_id'] is not None and x.get('run_id') == r['original_run_id'] and domain == 'CodebaseIR' and x.get('domain') == 'CodebaseIR/Source384'), None)
            intent_advisor = next((x for x in encoders if r['original_run_id'] is not None and x.get('run_id') == r['original_run_id'] and domain == 'IntentIR' and x.get('domain') == 'IntentIR'), None)
            row = {'schema': 'paper-cross-ir-trace@1', 'run_id': r['original_run_id'], 'ledger_id': r['ledger_id'],
                   'study_id': r['study_id'], 'domain': domain, 'stage': stages[domain],
                   'status': 'unavailable/unsupported', 'evidence_paths': r['evidence_paths'],
                   'independently_checked_result': False, 'behavior_reexecuted_here': False,
                   'applicability': 'not independently recovered; absent observation is not an inapplicability decision',
                   'intent_to_codebase_admitted_correspondence': 'unavailable/unsupported',
                   'complete_joined_counterexample': 'not established', 'separate_action_admission': 'not independently joined',
                   'limitation': 'No compatible per-trial stage receipt recovered in bounded inspection'}
            if known:
                row.update(status=known['status'].replace('_', ' '), stage_observation=known,
                           limitation='Retained stage result; no automatic promotion to qualified joined semantics')
            if deployment:
                row.update(status='actually invoked', stage_observation=deployment,
                           limitation='Zero target training; unsupported unchanged predictions; no source proof authority')
            if intent_advisor:
                row.update(status='actually invoked', stage_observation=intent_advisor,
                           limitation='Advisor invoked and failed open without checkpoint; learned intent inference not established')
            if r['original_run_id']:
                row['cross_domain_join_observation'] = next((x for x in actual_ir if x['run_id'] == r['original_run_id'] and x['stage'] == 'joined_counterexample_check'), None)
                row['action_stage_observation'] = next((x for x in actual_ir if x['run_id'] == r['original_run_id'] and x['stage'] == 'separately_authorized_action'), None)
            if domain == 'SecurityIR' and r['original_run_id'] == 'fix-code-vulnerability__z4cVfSR':
                row.update(status='actually invoked', stage_observation=read_rows('workstreams/t2_t4_proof_observations.jsonl')[0],
                           limitation='Source-bound local guard contract only; SecurityIR obligations not discharged; no full static analysis')
            traces.append(row)
    assert len(traces) <= 200
    assert all(r['status'] == 'unavailable/unsupported' for r in traces if r['run_id'] is None)
    jl('cross_ir_trace.jsonl', traces)
    implementation = findings['cross_ir']['implementation_rows']
    tab('cross_ir_implementation_matrix.csv', implementation,
        ['domain', 'stage', 'trial', 'status', 'caller', 'claim', 'runtime_invocation_established', 'independently_checked_result', 'evidence_paths', 'remaining_gap'])
    tab('source_to_caller_to_claim.csv', implementation,
        ['domain', 'stage', 'caller', 'evidence_paths', 'claim', 'status', 'remaining_gap'])
    js('logic_family_inventory.json', findings['cross_ir']['logic_families'])

    exceptions = []
    for r in runs:
        reasons = []
        if r['invoked'] is False:
            reasons.append('not invoked')
        if r['original_reward'] == 0 or r['historical_accepted_node'] is False or r['failure_category']:
            reasons.append('failure or rejected node; retain original outcome scope')
        if r['invoked'] and r['reported_tokens'].get('total_tokens') is None:
            reasons.append('missing token observation; not zero')
        if r['run_unit'] == 'benchmark_trial' and r['invoked'] and r['original_reward'] is None:
            reasons.append('missing reward; retain in enrolled cohort')
        if r['run_unit'] == 'benchmark_trial' and r['native_usage_complete'] is not True:
            reasons.append('native usage completeness not established')
        if reasons:
            exceptions.append({'ledger_id': r['ledger_id'], 'study_id': r['study_id'], 'run_unit': r['run_unit'],
                               'reasons': reasons, 'reward': r['original_reward'], 'invoked': r['invoked'],
                               'reported_total': r['reported_tokens'].get('total_tokens'), 'evidence_paths': r['evidence_paths']})
    jl('failed_uninvoked_missing_observations.jsonl', exceptions)
    aggregate_missing = {'historical_32': '32 original cells not individually recovered; 16/32 usage observed; see studies.json for all outcome classes',
                         'historical_24': 'Separate 24-cell pilot; 10 useful labels; original individual rows not recovered',
                         'unknown_gaps': 'No global registry census; inventory completeness applies to the bounded named evidence only',
                         'configuration_failure': read_json('workstreams/t2_t4_joins.json')}
    js('aggregate_failures_and_preparation_inventory.json', aggregate_missing)

    missing = []
    contradictions = []
    for worker, d in findings.items():
        missing += [{'workstream': worker, **x} for x in d.get('missing', d.get('missing_evidence', []))]
        contradictions += [{'workstream': worker, **x} for x in d.get('contradictions', d.get('contradictions_and_qualifications', []))]
    missing.append({'field': 'supplied v2 package/PDF identity', 'reason': 'Original supplied file unavailable; user authorized reconstructing a working package. Exact title is confirmed for increment-016, not original byte identity.', 'smallest_remedy': 'Author selects this declared base or supplies original package identity.'})
    jl('missing_evidence.jsonl', missing)
    jl('contradictions.jsonl', contradictions)
    lines = ['# Missing evidence and bounded stopping reasons', '', 'These are unavailable or uninspected fields, not proof that the underlying events never occurred.', '']
    for i, x in enumerate(missing, 1):
        lines += [f'## {i}. {x.get("field", x.get("item", x.get("gap", "Unresolved evidence")))}', '', '```json', json.dumps(x, indent=2), '```', '']
    write('missing_evidence.md', '\n'.join(lines))
    write('contradictions.md', '# Contradictions and claim qualifications\n\n' + '\n\n'.join('```json\n'+json.dumps(x, indent=2)+'\n```' for x in contradictions))

    result_rows = []
    for r in benchmark:
        result_rows.append({'study': r['study_id'], 'run_id': r['original_run_id'], 'audit_id': r['ledger_id'],
                            'requested_profile': r['requested_treatment'] or r['profile'], 'delivered_profile': r['delivered_treatment'],
                            'invoked': r['invoked'], 'reward': r['original_reward'], 'reported_total_tokens': r['reported_tokens'].get('total_tokens'),
                            'native_usage_complete': r['native_usage_complete'], 'whole_pipeline_complete': r['whole_pipeline_usage_complete'],
                            'supervisor_completed': r['supervisor_completed'], 'evidence_tier': r['evidence_tier']})
    tab('results.csv', result_rows, list(result_rows[0]))
    lines = ['# Retained Terminal-Bench observations', '', 'Rows are distinct historical trials or explicitly uninvoked/unbound slots. A reported token total is not automatically complete pipeline usage. Different source revisions and profiles are not repeated samples or a pooled comparison.', '', '| Study | Original run or audit slot | Profile | Reward | Reported tokens | Native usage complete |', '|---|---|---|---:|---:|---|']
    for r in result_rows:
        lines.append('| ' + ' | '.join(str(r.get(k)) if r.get(k) is not None else 'unavailable' for k in ['study', 'run_id' if r['run_id'] else 'audit_id', 'requested_profile', 'reward', 'reported_total_tokens', 'native_usage_complete']) + ' |')
    lines += ['', 'T1 final baseline is a native-input supervisor; T2/T3/T4 native-codex profiles are native harness controls. The tables do not relabel these as one baseline. See workstreams/*_report.md for cohort-specific interpretation.', '', 'No dollars or project-wide token total are inferred. Historical non-Terminal-Bench cohorts and positive reuse denominators are retained separately in studies.json and the historical report.']
    write('results.md', '\n'.join(lines)+'\n')

    checks = []
    def check(name, actual, expected):
        checks.append({'check': name, 'actual': actual, 'expected': expected, 'passed': actual == expected})
    t1hist = [r for r in benchmark if r['study_id'] == 'T1' and r['invoked']]
    check('T1 nine historical invoked', len(t1hist), 9)
    check('T1 known subtotal, not project total', sum(r['tokens']['total_tokens'] for r in t1hist if r['tokens']['total_tokens'] is not None), 2523452)
    check('T1 missing usage failures', sum(r['tokens']['total_tokens'] is None for r in t1hist), 3)
    check('fresh no-index independent identity', by_run['fix-code-vulnerability__2f3LChX']['tokens']['total_tokens'], 282802)
    check('native control counted once', sum(r['original_run_id'] == 'fix-code-vulnerability__VfZu8VN' for r in runs), 1)
    for run, total in [('fix-code-vulnerability__6Cahzwm',720840),('fix-code-vulnerability__wox8jVM',445333),('largest-eigenval__8vAYxJm',113883),('largest-eigenval__beFUuMt',358492),('largest-eigenval__ePRwqVj',333973)]:
        check(run, by_run[run]['tokens']['total_tokens'], total)
    for run, total in [('largest-eigenval__WS7vi7k',1310764),('largest-eigenval__gB4UUzB',1621661),('largest-eigenval__kzYcAuM',2452634)]:
        check('Grok reported incomplete:' + run, by_run[run]['reported_tokens']['total_tokens'], total)
    for c in findings['t1']['arithmetic']['checks']:
        check('T1:' + str(c.get('run_id') or c.get('audit_observation_id')), c['input_plus_output_equal_total'], True)
    for c in findings['t2_t4']['checks']:
        check('T2-T4:' + c['check'] + ':' + str(c.get('run_id', c.get('invocation_id'))), c['passed'], True)
    historic_checks = read_json('workstreams/historical_numerical_checks.json')
    for c in historic_checks['checks']:
        check('historical:' + str(c.get('check', c.get('name', c.get('label')))), c['passed'], True)
    js('audit/numerical_audit.json', {'schema':'paper-evidence-arithmetic@1', 'passed': all(c['passed'] for c in checks),
                                    'checks': checks, 'project_total_tokens': None,
                                    'scope': 'Arithmetic/count/schema over retained projections; not authenticity, billing, causal effect or new execution',
                                    'native_receipt_reconciliation': 'audit/native_usage_reconciliation.json'})
    assert all(c['passed'] for c in checks), 'Arithmetic mismatch'
    runtime_rows = [{k: r.get(k) for k in ['ledger_id', 'study_id', 'report_commit', 'executed_source_forest', 'runtime_archive_sha256', 'actual_loaded_module_origins', 'evidence_paths']} for r in runs]
    js('runtime_manifest.json', {'rows': runtime_rows, 'archives_rehashed_in_this_audit': False,
                                 'build_time_origins_not_live_loaded_origins': findings['t1'].get('host_build_module_origins'),
                                 't1_source_runtime_observations': findings['t1'].get('source_runtime'),
                                 'current_heads_not_combined_into_runtime_forest': True})
    js('proof_scorer_reuse_audit.json', {'historical': read_json('workstreams/historical_proof_scorer_reuse.json'),
                                       'T2': read_rows('workstreams/t2_t4_proof_observations.jsonl'),
                                       'expected_axiom_strings_are_not_recovered_stdout': True,
                                       'no_new_solver_or_build_execution': True})

    # Public derivative deliberately exports no original IDs, source paths, hashes or timestamps.
    anonymous = []
    aliases = []
    for i, r in enumerate(result_rows, 1):
        alias = f'trial-{i:03d}'
        aliases.append({'alias': alias, 'ledger_id': r['audit_id'], 'original_run_id': r['run_id']})
        anonymous.append({'alias': alias, 'study': r['study'], 'profile': r['requested_profile'], 'invoked': r['invoked'],
                          'reward': r['reward'], 'reported_total_tokens': r['reported_total_tokens'],
                          'native_usage_complete': r['native_usage_complete']})
    tab('anonymous/results.csv', anonymous, list(anonymous[0]))
    js('private/alias_map.json', aliases)
    js('private/original_provenance_inventory.json', {'artifacts': artifacts, 'private_author_material': True,
                                                    'raw_transcripts_exported': False, 'signature_verification': 'not_performed'})
    der = out/'anonymous/results.csv'
    js('anonymous/release_inventory.json', {'derivatives': [{'path': 'results.csv', 'sha256': hashlib.sha256(der.read_bytes()).hexdigest(), 'bytes': der.stat().st_size}],
                                           'release_authorized': False, 'uploaded': False, 'original_signatures_inherited': False,
                                           'anonymity_guaranteed': False, 'correlation_risk': 'Exact counts and treatment names may identify public studies even without raw IDs.',
                                           'review_required': 'Author provenance/license/workshop anonymization review; full audit is private.'})
    js('audit/assembly_summary.json', {'studies': len(studies), 'run_records': len(runs),
                                      'benchmark_rows': len(benchmark), 'identified_benchmark_trials': sum(r['original_run_id'] is not None for r in benchmark),
                                      'session_and_call_records': len(sessions), 'artifacts': len(artifacts),
                                      'unique_evidence_bytes': sum(r['bytes'] for r in artifacts), 'cross_ir_rows':len(traces),
                                      'encoder_deployment_rows':len(encoders), 'claims':len(claims), 'missing_items':len(missing),
                                      'arithmetic_checks':len(checks), 'passed': True,
                                      'original_behavior_reexecutions':0, 'model_calls':0, 'solver_executions':0})
    print(json.dumps({'output': str(out), 'run_records': len(runs), 'artifacts':len(artifacts), 'checks':len(checks), 'passed':True}))

if __name__ == '__main__':
    os.umask(0o077)
    main()
