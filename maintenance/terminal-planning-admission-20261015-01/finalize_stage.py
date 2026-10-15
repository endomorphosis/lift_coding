"""Publish bounded planning-admission evidence and remaining improvement gates."""
import argparse
import json
from pathlib import Path
from admission_io import ROOT,FALSE,inputs,read,write,wire,sha

def finalize(args):
    import runpy
    from admission_verify import validate_result,artifact_check,fault_precondition
    retained={}
    def get(name):
        raw=read(ROOT/name,32*1024**2);retained[name]=raw;return json.loads(raw)
    result=get(args.run+'/result.json');validate_result(result);acquired=artifact_check(ROOT/args.run,result)
    process=get(args.run+'-process-report.json');tests=get(args.regression+'-process-report.json')
    faults=get(args.fault+'-fault-report.json');fault_process=get(args.fault+'-process-report.json')
    cold=get(args.cold+'-cold-report.json');cold_process=get(args.cold+'-process-report.json')
    from run_process import selected
    if selected()!=cold_process['after']:raise ValueError('current producer inventory differs from selected cold replay')
    reference=ROOT.parent/'terminal-reference-packing-20261014-01'
    verify=runpy.run_path(str(reference/'finalize_stage.py'),run_name='public_evidence_binding_helpers')
    verify['validate_report_bindings'](run=args.run,result=result,result_raw=retained[args.run+'/result.json'],
        process=process,tests=tests,cold=cold,cold_process=cold_process,faults=faults,fault_process=fault_process,
        fault_name=args.fault+'-fault-report.json',fault_raw=retained[args.fault+'-fault-report.json'])
    fault_precondition(args.fault+'-fault-report.json',output=ROOT/args.run,result=result,result_raw=retained[args.run+'/result.json'])
    inputs();cost=cold['cost_observation']
    status={'schema':'terminal-planning-admission-improvement-status@1','completed_milestone':True,
        'selected_run':args.run,'result_sha256':sha(retained[args.run+'/result.json']),
        'native_local_planning_metatasks_admitted':8,'actual_claim_fenced_worker_deliveries':8,
        'historical_native_signed_reports_replayed':8,'declared_observation_artifacts_created':8,
        'original_instructions_retained':4,'original_sources_retained':5,'original_benchmark_tasks_admitted':0,
        'regression_tests':tests['tests'],'native_fault_controls':len(faults['controls']),
        'actual_extra_fault_workers':faults['actual_extra_worker_children'],'cost_observation':cost,
        'authority_scope':'fresh-isolated-experimental-profile-registry-and-coordinator',
        'native_profile_capabilities':['read','edit','test','isolated_worktree','write_worktree'],
        'actual_permit_scope':'single-request-local-planning-observation',
        'private_authority_retained':False,'current_authority_recreated_from_public_evidence':False,
        'full_supervisor_dispatch_exercised':False,'actual_external_provider_invocations':0,
        'provider_usage':None,'provider_token_savings_qualified':False,'source_body_execution':False,
        'original_task_satisfaction':False,'source_to_model_equivalence':False,'convergence_proved':False,
        'remaining_work':['complete original IntentIR semantics and codebase coverage',
            'native typed supervisor task-source and dispatch integration',
            'same-model provider and official-harness paired evaluation',
            'source-to-model semantics and conditional convergence proofs'],**FALSE}
    write(ROOT/'improvement-status-01.json',status)
    plan={'schema':'terminal-codebase-intent-ir-improvement-plan@8',
        'current_pipeline':['full prompt and repository bytes','current native CodebaseIR head',
            'DuckDB/DuckLake structural metadata and complete-context capsules',
            'lossless reference packing with whole-message token selection',
            'distinct signed planning-observation graph and formally consistent future plan',
            'native pending task materialization','native coordinator task claim',
            'owner-memory single-use permit','native resource-admitted process and local router observation',
            'current-owner exit check','declared full-input observation artifact'],
        'measured_local_cost':cost,
        'formal_scope':{'plan_consistency':'native formal consistency of intended metatask effects',
            'artifact_integrity':'exact retained bytes and portable historical fixture signatures',
            'original_code_behavior_proved':False,'original_intent_coverage_complete':False,
            'neural_source_equivalence_proved':False,'optimizer_convergence_proved':False},
        'next_gates':[
            {'order':1,'work':'Represent every original instruction clause in native IntentIR with exact UTF8 source spans and unresolved residuals.',
                'acceptance':'Native coverage adapter admits all mandatory units without unsupported semantics; paraphrase, omission and contradiction controls reject.'},
            {'order':2,'work':'Join each requirement to current source symbols, effects, interfaces, contracts and tests through the native codebase owner.',
                'acceptance':'Head and source changes invalidate plans, projections and proof-cache keys before reuse; no vector similarity or cached receipt grants proof authority.'},
            {'order':3,'work':'Integrate the metatask with a genuine typed supervisor task source and its process-attested dispatch lifecycle.',
                'acceptance':'Real READY state server, lifecycle-bound runtime, native grant, actual task claim and supported dispatch receipt; no copied typed-daemon IDs.'},
            {'order':4,'work':'Run paired expanded/adaptive trials through the same external model and official benchmark harness.',
                'acceptance':'Measure actual provider input/output, cache, retries, tool output, latency and full task outcomes; preserve budgets and task coverage.'},
            {'order':5,'work':'Extend source-derived semantics into supported logic families and Lean with explicit language assumptions.',
                'acceptance':'Compile generated theorems and genuine false controls; distinguish syntax roundtrips, mathematical integer models and Python execution behavior.'},
            {'order':6,'work':'Train the codebase representation only on declared training partitions and compare held-out reconstruction and planning outcomes.',
                'acceptance':'No test leakage; deterministic optimizer replay, OOV accounting, untrained/mean/SVD baselines and source-complete sidecars; promote only measured improvements.'},
            {'order':7,'work':'Prove convergence for an explicit objective, update rule, numerical model and stated assumptions.',
                'acceptance':'Lean-checked conditional theorem plus empirical curves and false controls; finite loss improvement does not establish universal neural or task convergence.'}],
        'fixture_authority_is_account_authority':False,'public_evidence_is_dispatch_capability':False,
        'all_original_benchmark_requirements_pending':True,'provider_token_savings_qualified':False,**FALSE}
    write(ROOT/'improvement-plan-v8.json',plan)
    if artifact_check(ROOT/args.run,result)!=acquired:raise ValueError('selected artifacts changed during finalization')
    fault_precondition(args.fault+'-fault-report.json',output=ROOT/args.run,result=result,result_raw=retained[args.run+'/result.json'])
    for name,raw in retained.items():
        if read(ROOT/name,32*1024**2)!=raw:raise ValueError('selected reports changed during finalization')
    if selected()!=cold_process['after']:raise ValueError('producer inventory changed during finalization')
    names=[]
    for path in sorted(ROOT.rglob('*')):
        relative=path.relative_to(ROOT)
        if '.git' in relative.parts or '__pycache__' in relative.parts:continue
        if path.is_symlink():raise ValueError('public evidence stage symlink refused')
        if path.is_file() and relative.as_posix() not in {'evidence-manifest.json','seal-config-01.json'}:
            names.append(relative.as_posix())
    names.append('seal-config-01.json');names.sort()
    config={'schema':'terminal-codebase-ir-evidence-selection@1','root':str(ROOT),'files':names,
        'selection_scope':'owned_public_planning_admission_experiment','excluded_git_metadata':True,
        'symlink_targets_opened':False,'proof_authority':False}
    write(ROOT/'seal-config-01.json',config)
    from seal_training_evidence import seal
    manifest=ROOT/'evidence-manifest.json';seal(config,manifest);seal(config,manifest,verify=True)
    print(json.dumps({'sealed':True,'manifest_sha256':sha(read(manifest,1024**2)),
        'native_metatasks':8,'regression_tests':tests['tests']['tests'],'native_fault_controls':len(faults['controls']),
        'local_input_tokens_saved':cost['local_input_tokens_saved']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--regression',required=True)
    parser.add_argument('--fault',required=True);parser.add_argument('--cold',required=True);args=parser.parse_args()
    for value in vars(args).values():
        if Path(value).name!=value or value in {'.','..'}:raise ValueError('owned selected names required')
    finalize(args)
