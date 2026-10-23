"""Bind qualified native intent evidence and publish explicit remaining gates."""
import argparse
import json
import os
from pathlib import Path
import runpy
from intent_io import ROOT,FALSE,inputs,read,write,wire,sha

def finalize(args):
    from intent_verify import validate_result,artifact_check,fault_precondition
    from run_process import selected
    selected_raw={}
    def get(name):
        raw=read(ROOT/name,32*1024**2);selected_raw[name]=raw;return json.loads(raw)
    result=get(args.run+'/result.json');validate_result(result);artifacts=artifact_check(ROOT/args.run,result)
    process=get(args.run+'-process-report.json');tests=get(args.regression+'-process-report.json')
    fault=get(args.fault+'-fault-report.json');fault_process=get(args.fault+'-process-report.json')
    cold=get(args.cold+'-cold-report.json');cold_process=get(args.cold+'-process-report.json')
    if selected()!=cold_process['after']:raise ValueError('current selected producers differ from cold verification')
    helper=runpy.run_path(str(ROOT.parent/'terminal-reference-packing-20261014-01'/'finalize_stage.py'),run_name='sealed_public_binding_helpers')
    helper['validate_report_bindings'](run=args.run,result=result,result_raw=selected_raw[args.run+'/result.json'],
        process=process,tests=tests,cold=cold,cold_process=cold_process,faults=fault,fault_process=fault_process,
        fault_name=args.fault+'-fault-report.json',fault_raw=selected_raw[args.fault+'-fault-report.json'])
    fault_precondition(args.fault+'-fault-report.json',output=ROOT/args.run,result=result,result_raw=selected_raw[args.run+'/result.json'])
    inventories=json.loads(artifacts['intent-inventories.json']);grounding=json.loads(artifacts['grounding.json'])
    projections=json.loads(artifacts['logic-projections.json']);lean=json.loads(artifacts['lean-validation.json'])
    from clause_inventory import validate_instruction_inventory
    corpus,bodies,instructions,lineage=inputs()
    summary=[]
    for report in inventories:
        validate_instruction_inventory(report,task_id=report['task_id'],instruction=instructions[report['task_id']])
        if report['native_coverage']['receipt']['accepted'] is not False:raise ValueError('original task coverage cannot be promoted')
        ledger=report['native_requirement_ledger']
        summary.append({'task_id':report['task_id'],'instruction_bytes':report['instruction']['bytes'],
            'instruction_characters':report['instruction']['characters'],'lossless_line_units':len(report['units']),
            'manually_authored_candidate_documents':len(report['native_intent_documents']),
            'native_candidate_requirements':len(ledger['requirements']),
            'native_unsupported_source_units':len(report['residual_source_units']),
            'semantic_residual_units':len(report['semantic_residual_units']),
            'native_original_task_coverage_accepted':False,'all_requirement_semantics_verified':False})
    family_summary={}
    for task in projections['tasks']:
        for projected in task['family_report']['projections']:
            bucket=family_summary.setdefault(projected['family_id'],{})
            bucket[projected['status']]=bucket.get(projected['status'],0)+1
    lean_summary={'positive_declaration_compiles':lean['positive_compiles'],
        'false_type_controls_rejected':lean['false_type_controls_rejected'],
        'syntax_and_typechecks_only':True,'original_requirement_theorems_proved':0}
    status={'schema':'terminal-intent-coverage-improvement-status@1','completed_milestone':True,'selected_run':args.run,
        'selected_result_sha256':sha(selected_raw[args.run+'/result.json']),'instruction_inventory':summary,
        'source_count':5,'task_count':4,'complete_instruction_bytes':sum(row['instruction_bytes'] for row in summary),
        'source_ast_and_semantic_index_replayed':True,'per_unit_source_citations_are_lexical_nominations':True,
        'native_current_owner_observed_before_and_after':True,'metadata_original_record_counts':result['metadata_original_record_counts'],
        'logic_projection_summary':family_summary,'lean_validation_summary':lean_summary,
        'regression_tests':tests['tests'],'native_fault_controls':len(fault['controls']),
        'all_original_tasks_blocked_by_native_coverage':True,'all_original_task_semantics_unresolved':True,
        'full_original_task_satisfaction':False,'new_optimizer_updates':0,'external_provider_calls':0,
        'new_external_model_inferences':0,'provider_usage':None,'provider_token_savings_measured':False,
        'whole_source_runtime_equivalence_proved':False,'neural_convergence_proved':False,
        'full_supervisor_dispatch_exercised':False,'source_body_execution':False,
        'next_work':['typed constraints for numeric, quantifier, temporal and nonmutation requirements',
            'source-derived effect/behavior contracts with explicit language assumptions',
            'native typed supervisor dispatch with supported intent coverage',
            'paired external-model token and official task-outcome evaluation'],**FALSE}
    write(ROOT/'improvement-status-01.json',status)
    plan={'schema':'terminal-codebase-intent-ir-improvement-plan@9',
        'completed_work':['all four original instructions retained with exact UTF8 and character selectors',
            'native no-checkpoint IntentIR frontend baseline and source-accounted requirement ledgers',
            'separate authored unreviewed atomic candidates with complete semantic residuals',
            'native original-task coverage rejection for every incomplete instruction',
            'replayed source AST, symbols, effects and interfaces with task-scoped lexical citations',
            'native logic-family declaration projections and explicit unsupported-family records',
            'installed Lean compilation of generated declaration types with an actual false control',
            'fresh DuckDB/DuckLake hydration and cold reconstruction of all metadata'],
        'current_limits':{'clauses_are_automatically_understood':False,'lexical_source_citations_prove_entailment':False,
            'uninterpreted_declarations_prove_program_behavior':False,'candidate_statements_resolve_original_requirements':False,
            'native_original_task_coverage_complete':False,'full_supervisor_runtime_exercised':False,
            'provider_savings_or_task_outcomes_measured':False,'source_model_equivalence_proved':False,
            'optimizer_convergence_proved':False},
        'task_frontiers':summary,
        'next_gates':[
            {'order':1,'work':'Extend supported typed IntentIR constraints for quantities, comparisons, exact cardinality, temporal limits and negative effects.',
                'acceptance':'Every original clause has exact source spans, independently specified semantics and a supported native logic lowering; unsupported source and semantic residuals remain blocking.'},
            {'order':2,'work':'Build source-derived behavior models and proof-cache dependencies for each requirement.',
                'acceptance':'Bind proof obligations to current head/source/symbol/effect/logic/checker identities; stale code invalidates lookup. Lexical matches and uninterpreted atoms cannot satisfy behavioral obligations.'},
            {'order':3,'work':'Connect admitted complete IntentIR plans to the native typed supervisor task source and process-attested dispatch.',
                'acceptance':'Use a real state server and native owner grants, claims and receipts; earlier isolated metatask evidence is historical data only.'},
            {'order':4,'work':'Measure expanded versus adaptive context on the same actual model and official TerminalBench harness.',
                'acceptance':'Account for input/output/cache/retries/tool tokens, latency and every original acceptance criterion without omitted source or instructions.'},
            {'order':5,'work':'Train task-conditioned codebase_IR with declared train/validation/evaluation partitions and source-complete sidecars.',
                'acceptance':'No evaluation fitting; compare untrained, mean and SVD baselines and downstream task outcomes. Fixed finite training improvement is a separate empirical result.'},
            {'order':6,'work':'Prove source-to-model preservation and conditional optimizer convergence for explicit supported models.',
                'acceptance':'State Python/runtime/numerical assumptions; compile Lean theorem sources and actual false controls. Typechecking declarations does not prove semantic preservation or convergence.'}],
        'all_original_requirements_pending':True,**FALSE}
    write(ROOT/'improvement-plan-v9.json',plan)
    if artifact_check(ROOT/args.run,result)!=artifacts:raise ValueError('selected artifacts changed during finalization')
    fault_precondition(args.fault+'-fault-report.json',output=ROOT/args.run,result=result,result_raw=selected_raw[args.run+'/result.json'])
    if selected()!=cold_process['after'] or inputs()[3]!=lineage:raise ValueError('selected producers or source lineage changed during finalization')
    for name,raw in selected_raw.items():
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
        'selection_scope':'owned_public_full_instruction_source_bound_intent_evidence',
        'excluded_git_metadata':True,'symlink_targets_opened':False,'proof_authority':False}
    write(ROOT/'seal-config-01.json',config)
    from seal_training_evidence import seal
    manifest=seal(config,ROOT/'evidence-manifest.json');seal(config,ROOT/'evidence-manifest.json',verify=True)
    print(json.dumps({'sealed':True,'files':manifest['file_count'],'bytes':manifest['total_bytes'],
        'regression_tests':tests['tests']['tests'],'instruction_bytes':status['complete_instruction_bytes'],
        'original_native_task_coverage_accepted':0,'manifest_sha256':sha(read(ROOT/'evidence-manifest.json',1024**2))}))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('run','regression','fault','cold'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    for value in vars(args).values():
        if Path(value).name!=value or value in {'.','..'}:raise ValueError('owned selected names required')
    finalize(args)
