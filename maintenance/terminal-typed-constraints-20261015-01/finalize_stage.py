"""Publish finite-model proof results with the original task residuals intact."""
import argparse
import json
import os
from pathlib import Path
import runpy
from constraint_io import ROOT,FALSE,inputs,read,write,wire,sha

def finalize(args):
    from constraint_verify import validate_result,artifact_check,fault_precondition
    from run_process import selected
    retained={}
    def get(name):
        raw=read(ROOT/name,32*1024**2);retained[name]=raw;return json.loads(raw)
    result=get(args.run+'/result.json');validate_result(result);artifacts=artifact_check(ROOT/args.run,result)
    process=get(args.run+'-process-report.json');tests=get(args.regression+'-process-report.json')
    faults=get(args.fault+'-fault-report.json');fault_process=get(args.fault+'-process-report.json')
    cold=get(args.cold+'-cold-report.json');cold_process=get(args.cold+'-process-report.json')
    if selected()!=cold_process['after']:raise ValueError('current producers differ from selected cold replay')
    helper=runpy.run_path(str(ROOT.parent/'terminal-reference-packing-20261014-01'/'finalize_stage.py'),run_name='public_binding_helpers')
    helper['validate_report_bindings'](run=args.run,result=result,result_raw=retained[args.run+'/result.json'],process=process,tests=tests,
        cold=cold,cold_process=cold_process,faults=faults,fault_process=fault_process,fault_name=args.fault+'-fault-report.json',
        fault_raw=retained[args.fault+'-fault-report.json'])
    fault_precondition(args.fault+'-fault-report.json',output=ROOT/args.run,result=result,result_raw=retained[args.run+'/result.json'])
    from scheduler_constraints import validate_scheduler_contract
    from constraint_projections import validate_constraint_projections
    from constraint_lean import validate_constraint_lean_evidence
    from constraint_run import source_records,TASK
    corpus,bodies,instructions,lineage=inputs()
    contract=json.loads(artifacts['scheduler-contract.json']);projections=json.loads(artifacts['constraint-projections.json'])
    lean=json.loads(artifacts['lean-evidence.json']);theory=json.loads(artifacts['lean-theory.json'])
    inventories=json.loads(artifacts['intent-inventories.json'])
    validate_scheduler_contract(contract,instruction=instructions[TASK],head=result['native_head'],source_records=source_records(bodies))
    validate_constraint_projections(projections,contract=contract)
    validate_constraint_lean_evidence(lean,theory=theory,output=ROOT/args.run/'lean')
    if any(row['native_coverage']['receipt']['accepted'] is not False for row in inventories):
        raise ValueError('original task coverage cannot be promoted by finite-model proofs')
    status={'schema':'terminal-typed-scheduler-constraint-improvement-status@1','completed_milestone':True,'selected_run':args.run,
        'selected_result_sha256':sha(retained[args.run+'/result.json']),'source_count':5,'task_count':4,
        'original_instruction_bytes_retained':sum(row['instruction']['bytes'] for row in inventories),
        'typed_contract_clauses':len(contract['clauses']),
        'authored_case_count':result['authored_case_count'],'accepted_authored_cases':result['accepted_authored_cases'],
        'rejected_authored_cases':result['rejected_authored_cases'],'all_authored_case_expectations_matched':True,
        'native_projection_scope':'source_bound_quantified_FOL_and_integer_SMT_compilation_only',
        'finite_model_proofs':{'positive_compiles':lean['positive_compiles'],
            'false_theorem_controls_rejected':lean['false_controls_rejected'],'proved_theorems':lean['proved_theorems'],
            'proof_scope':lean['proof_scope']},
        'regression_tests':tests['tests'],'native_fault_controls':len(faults['controls']),
        'metadata_original_record_counts':result['metadata_original_record_counts'],
        'all_original_tasks_still_blocked':True,'original_prompt_interpretation_verified':False,
        'finite_python_checker_equivalent_to_lean_model_proved':False,
        'FOL_SMT_Lean_interpretation_correspondence_proved':False,
        'supplied_metrics_are_runtime_measurements':False,'physical_input_immutability_proved':False,
        'input_observation_bytes_proved_to_encode_request_model':False,
        'source_body_execution':False,'new_optimizer_updates':0,'external_provider_calls':0,'provider_usage':None,
        'full_supervisor_dispatch_exercised':False,'original_task_satisfaction':False,'source_runtime_equivalence':False,
        'source_to_model_equivalence':False,'training_convergence_proved':False,**FALSE}
    write(ROOT/'improvement-status-01.json',status)
    plan={'schema':'terminal-codebase-intent-ir-improvement-plan@10',
        'completed_fragment':{'scope':'explicitly_authored_bounded_finite_scheduler_candidate',
            'constraints':['bucket-qualified exact-once request coverage and uniqueness',
                'sequence divisibility and ceil64 lower bound with heads32/hidden4096',
                'identical shapes within bucket-qualified batch IDs','global eight-shape cap over both buckets',
                'strict exact-rational metric thresholds','equality of supplied before/after UTF8 byte observations'],
            'native_representations':'real sorted equality/quantifiers and native integer SMT compilations',
            'proofs':'Lean kernel checked finite-model theorems and closed authored cases',
            'original_instructions':'all four complete originals and native coverage rejections retained'},
        'evidence_summary':{'authored_cases':result['authored_case_count'],'regression_tests':tests['tests'],
            'native_fault_controls':len(faults['controls']),'finite_model_theorems':lean['proved_theorems']},
        'remaining_semantic_bridges':[
            {'order':1,'work':'Bind parsed request JSONL and actual plan files to the finite model.',
                'acceptance':'Bounded byte-exact parser rejects duplicates, extras, missing fields and changed file observations; proving equality of supplied strings is not a claim of filesystem immutability.'},
            {'order':2,'work':'Prove correspondence among the Python checker, typed FOL structure, integer SMT obligations and Lean semantics.',
                'acceptance':'Independent cross-language checks and kernel-checked lowering proofs cover exact supported operators, domains, bucket identities and source-bound constants; compilation alone is insufficient.'},
            {'order':3,'work':'Resolve scheduler interpretation ambiguities and formalize source-derived metric calculations.',
                'acceptance':'Explicitly address bucket-local versus global batch IDs, nonnegative length domains, generation rounding, declared versus request-derived shape costs, strict thresholds and Python floating-point behavior.'},
            {'order':4,'work':'Integrate fully covered IntentIR plans with the native typed supervisor runtime and proof cache.',
                'acceptance':'No unsupported source or semantic residual may be silently waived. Bind validated proof dependencies to current codebase owner observations and actual native task/grant/claim/dispatch lifecycle.'},
            {'order':5,'work':'Measure paired model token usage and official benchmark task outcomes.',
                'acceptance':'Same model and task inputs; include full history, setup, tool output, retries, provider caches and every original acceptance condition.'},
            {'order':6,'work':'Train and evaluate codebase_IR with explicit partitioning and conditional convergence assumptions.',
                'acceptance':'No held-out fitting; compare simple baselines and downstream outcomes. Mathematical finite-model proofs neither establish source/model equivalence nor optimizer convergence.'}],
        'contract_interpretation_and_runtime_correspondence_unproved':True,
        'all_original_task_requirements_pending':True,'full_task_satisfaction':False,**FALSE}
    write(ROOT/'improvement-plan-v10.json',plan)
    if artifact_check(ROOT/args.run,result)!=artifacts:raise ValueError('selected evidence changed during finalization')
    fault_precondition(args.fault+'-fault-report.json',output=ROOT/args.run,result=result,result_raw=retained[args.run+'/result.json'])
    if selected()!=cold_process['after'] or inputs()[3]!=lineage:raise ValueError('producer or input lineage changed during finalization')
    for name,raw in retained.items():
        if read(ROOT/name,32*1024**2)!=raw:raise ValueError('selected report changed during finalization')
    names=[]
    for base,dirs,files in os.walk(ROOT,followlinks=False):
        dirs[:]=[name for name in dirs if name not in {'.git','__pycache__','.pytest_cache'}]
        for name in files:
            path=Path(base)/name
            if path.is_symlink():raise ValueError('unexpected public evidence symlink')
            relative=path.relative_to(ROOT).as_posix()
            if relative not in {'evidence-manifest.json','seal-config-01.json'}:names.append(relative)
    names.append('seal-config-01.json')
    config={'schema':'terminal-codebase-ir-evidence-selection@1','root':str(ROOT),'files':sorted(names),
        'selection_scope':'owned_public_finite_scheduler_candidate_contract_evidence','excluded_git_metadata':True,
        'symlink_targets_opened':False,'proof_authority':False}
    write(ROOT/'seal-config-01.json',config)
    from seal_training_evidence import seal
    manifest=seal(config,ROOT/'evidence-manifest.json');seal(config,ROOT/'evidence-manifest.json',verify=True)
    print(json.dumps({'sealed':True,'files':manifest['file_count'],'bytes':manifest['total_bytes'],
        'tests':tests['tests']['tests'],'authored_cases':result['authored_case_count'],
        'finite_model_theorems':len(lean['proved_theorems']),'manifest_sha256':sha(read(ROOT/'evidence-manifest.json',1024**2))}))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('run','regression','fault','cold'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    for value in vars(args).values():
        if Path(value).name!=value or value in {'.','..'}:raise ValueError('owned selected names required')
    finalize(args)
