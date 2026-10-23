"""Summarize observed local worker payloads and seal their public evidence."""
import argparse
import json
import os
from pathlib import Path
import runpy
from worker_io import ROOT,REFERENCE,FALSE,inputs,read,write,wire,sha,pin

def main(args):
    for name in [args.run,args.regression,args.fault,args.cold]:
        if not name or Path(name).name!=name or name in {'.','..'}:raise ValueError('local selected names required')
    from worker_verify import validate_result,artifact_check,validate_deliveries
    result_raw=read(ROOT/args.run/'result.json');result=json.loads(result_raw)
    validate_result(result);artifacts=artifact_check(ROOT/args.run,result)
    retained={}
    def report(name):
        raw=read(ROOT/name);retained[name]=raw;return json.loads(raw)
    process=report(args.run+'-process-report.json');tests=report(args.regression+'-process-report.json')
    faults=report(args.fault+'-fault-report.json');fault_process=report(args.fault+'-process-report.json')
    cold=report(args.cold+'-cold-report.json');cold_process=report(args.cold+'-process-report.json')
    custody=runpy.run_path(str(REFERENCE/'finalize_stage.py'),run_name='sealed_reference_report_joins')
    custody['validate_report_bindings'](run=args.run,result=result,result_raw=result_raw,process=process,tests=tests,
        cold=cold,cold_process=cold_process,faults=faults,fault_process=fault_process,
        fault_name=args.fault+'-fault-report.json',fault_raw=retained[args.fault+'-fault-report.json'])
    for entry in cold_process['after']:
        if pin(Path(entry['path']))!=entry:raise ValueError('final worker producer drift')
    contexts=json.loads(artifacts['contexts.json']);deliveries=json.loads(artifacts['deliveries.json'])
    descriptor=json.loads(artifacts['tokenizer.json'])
    validate_deliveries(output=ROOT/args.run,contexts=contexts,deliveries=deliveries,
        descriptor=descriptor,artifacts=artifacts,head=result['native_head'])
    observed={};per_task=[]
    for session in deliveries['sessions']:
        mode=session['delivery_mode'];task=session['task_id']
        for scenario,n in [('one_turn',1),('three_turn_history',3),('three_turn_history_retry',4)]:
            tokens=sum(call['capture']['observation']['consumer']['input_local_tokens'] for call in session['calls'][:n])
            row={'task_id':task,'delivery_mode':mode,'scenario':scenario,'observed_local_input_tokens':tokens,
                'selected_forms':[c['capture']['observation']['selection']['selected_form'] for c in session['calls'][:n]],
                'provider_usage':None}
            per_task.append(row);observed[(task,mode,scenario)]=row
    totals=[]
    for scenario in ['one_turn','three_turn_history','three_turn_history_retry']:
        tasks=sorted({s['task_id'] for s in deliveries['sessions']})
        baseline=sum(observed[(task,'expanded',scenario)]['observed_local_input_tokens'] for task in tasks)
        for mode in ['adaptive','decode_before_model']:
            candidate=sum(observed[(task,mode,scenario)]['observed_local_input_tokens'] for task in tasks)
            differences=[observed[(task,'expanded',scenario)]['observed_local_input_tokens']-
                observed[(task,mode,scenario)]['observed_local_input_tokens'] for task in tasks]
            if mode=='decode_before_model' and any(differences):raise ValueError('decode control input cost changed')
            if mode=='adaptive' and any(v<0 for v in differences):raise ValueError('adaptive worker regressed complete input cost')
            totals.append({'scenario':scenario,'delivery_mode':mode,'expanded_local_tokens':baseline,
                'selected_local_tokens':candidate,'signed_difference':baseline-candidate,
                'local_reduction_fraction':(baseline-candidate)/baseline,'provider_savings':None})
    status={'schema':'terminal-context-worker-improvement-status@1','completed_milestone':True,'selected_run':args.run,
        'native_head':result['native_head'],'metadata_original_record_counts':result['metadata_original_record_counts'],
        'native_capsule_inventory':result['native_capsule_inventory'],'unique_selected_tests':tests['tests']['tests'],
        'actual_native_low_level_worker_processes':48,'actual_native_router_local_consumer_calls':48,
        'extra_retained_source_fault_worker_processes':1,'actual_external_provider_invocations':0,
        'native_shared_resource_admission_used':True,'full_supervisor_task_admission_exercised':False,
        'separate_worker_uid_boundary_qualified':False,'all_full_messages_and_final_budgets_verified_at_consumer':True,
        'all_original_instructions_sources_and_residuals_preserved':True,'all_requirements_remain_unresolved':True,
        'previously_delivered_history_is_immutable_ordered_prefix':True,'positive_cold_after_faults_qualified':True,
        'source_changed_after_actual_child_birth_refused_before_candidate_return':True,
        'overbudget_and_rewritten_or_reordered_history_refused_before_launch':True,
        'per_task_observed_local_costs':per_task,'aggregate_observed_local_input_costs':totals,
        'provider_usage':None,'actual_terminal_bench_task_outcomes':None,'model_outputs_produced':False,
        'compression_promoted_to_supervisor_default':False,'source_body_execution':False,
        'new_optimizer_updates':0,'new_prover_invocations':0,**FALSE}
    write(ROOT/'improvement-status-01.json',status)
    plan={'schema':'terminal-codebase-intent-ir-improvement-plan@7',
        'measured_scope':'Real low-level supervisor processes and native router local-consumer delivery; no external model or task actuation.',
        'next_work':[
          {'priority':1,'id':'generic-native-task-admission-and-provider-boundary',
           'implementation':['Introduce a distinctly versioned generic planning task admission profile with complete source and instruction provenance.',
             'Keep complete unresolved requirements mandatory; never borrow Bottle/finite-proof-query admission or completion receipts.',
             'Carry exact worker UID/container custody and original resource leases into actual model invocation.',
             'Preserve full delivered history and enforce final message budget after every materialization step.'],
           'acceptance':['Current local captures acknowledge input only; they are not model inference or native full-supervisor task dispatch.',
             'Retain per-task expanded fallback and report actual provider input/output usage before claiming provider savings.']},
          {'priority':2,'id':'paired-official-benchmark-and-total-work-accounting',
           'implementation':['Run fixed paired task/model/config populations through the official verifier.',
             'Measure task success, model interpretation of references, tool expansions, retries, output usage and setup/index/training work.',
             'Persist whole-task spending and failed attempt work across restart using original native resource custody.'],
           'acceptance':['No task success, total provider savings or durable global budget is inferred from local endpoint captures.']},
          {'priority':3,'id':'complete-intent-current-codebase-matching',
           'implementation':['Decode all instruction goals, guards, prohibitions, effects and bounds with source-span-accounted residuals.',
             'Join intent atoms against current AST, graph, interfaces, effects, vectors and contracts in DuckDB/DuckLake.',
             'Require actual planner coverage and negative omission checks before relevance-based source reduction.'],
           'acceptance':['Advisory learned relevance cannot discharge unsupported instructions or source obligations.']},
          {'priority':4,'id':'source-to-model-equivalence-and-proof-cache',
           'implementation':['Develop constrained discrete CodebaseIR decoding with exact bindings, literals, effects, types and control flow.',
             'Project supported fragments through genuine logic-family checkers and Lean.',
             'Bind conditional proof-cache entries and reverse dependencies to exact source/head/target/checker identities.'],
           'acceptance':['Data reconstruction, source runtime semantics, finite training improvement and asymptotic convergence remain separate claims.']}
        ],'observed_local_costs':totals,**FALSE}
    write(ROOT/'follow-up-plan-01.json',plan);inputs()
    if read(ROOT/args.run/'result.json')!=result_raw:raise ValueError('selected worker result changed during finalization')
    artifact_check(ROOT/args.run,result);custody['verify_selected_report_bytes'](ROOT,retained)
    files=[]
    for base,dirs,names in os.walk(ROOT,followlinks=False):
        dirs[:]=[v for v in dirs if v not in {'.git','__pycache__','.pytest_cache'}]
        for name in names:
            path=Path(base)/name
            if path.is_symlink():raise ValueError('unexpected owned evidence symlink')
            files.append(path.relative_to(ROOT).as_posix())
    config={'schema':'terminal-codebase-ir-evidence-selection@1','root':str(ROOT),
        'files':sorted(files+['seal-config-01.json']),'selection_scope':'owned_public_generic_worker_delivery_artifacts',
        'excluded_git_metadata':True,'symlink_targets_opened':False,'proof_authority':False}
    write(ROOT/'seal-config-01.json',config)
    from seal_training_evidence import seal
    manifest=seal(config,ROOT/'evidence-manifest.json');seal(config,ROOT/'evidence-manifest.json',verify=True)
    print(json.dumps({'sealed':True,'files':manifest['file_count'],'bytes':manifest['total_bytes'],
        'tests':tests['tests']['tests'],'observed_native_processes':48,'extra_fault_child':1,'provider_usage':None,
        'local_costs':totals}))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ['run','regression','fault','cold']:parser.add_argument('--'+name,required=True)
    main(parser.parse_args())
