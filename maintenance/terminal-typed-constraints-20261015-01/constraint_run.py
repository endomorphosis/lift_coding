"""Experimental finite scheduler contracts, bound to the original source head."""
import argparse
import json
from pathlib import Path
import resource
import time
import traceback
from constraint_io import ROOT,FALSE,inputs,read,write,wire,sha,pin
from capsule_run import source_repository,check_lease
TASK='llm-inference-batching-scheduler'
POLICY={'schema':'terminal-typed-scheduler-constraint-policy@1','source_count':5,'task_count':4,
    'outer_wall_seconds':600,'parent_memory_mb':2048,'compiler_child_memory_mb':1024,
    'shared_native_resource_pool':True,'full_original_instruction_bytes_required':True,
    'source_body_execution':False,'contract_profile':'experimental-authored-finite-scheduler-model',
    'native_intent_rich_grammar_extended':False,'native_full_task_coverage_expected':'blocked',
    'metric_observations':'authored_exact_rationals_not_benchmark_runtime_measurements',
    'native_typed_logic_compilation_is_proof':False,'lean_proof_scope':'explicit_mathematical_finite_plan_model',
    'original_prompt_interpretation_proved':False,'provider_usage':None,'external_provider_calls':0,
    'new_optimizer_updates':0,'full_supervisor_dispatch_exercised':False,**FALSE}
FILES=['policy.json','corpus-manifest.json','lineage.json','structural-report.json','native-capsules.json',
    'codec-views.json','metadata-report.json','intent-inventories.json','source-grounding.json',
    'intent-logic-projections.json','structural-context.json','scheduler-contract.json',
    'constraint-projections.json','authored-cases.json','case-evaluations.json','lean-theory.json','lean-evidence.json']

def source_records(bodies):
    return [{'path':name,'sha256':sha(raw),'source_text':raw.decode('utf-8')} for name,raw in sorted(bodies.items())]

def build_constraint_materials(*,output,structural,corpus,bodies,instructions,lease):
    from intent_run import build_intent_materials
    base=build_intent_materials(output=output,structural=structural,corpus=corpus,bodies=bodies,instructions=instructions,lease=lease)
    from scheduler_constraints import build_scheduler_contract,authored_cases,evaluate_case
    from constraint_projections import build_constraint_projections
    from constraint_lean import build_lean_theory
    from native_structural_ir import _owner
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_accelerate_py.agent_supervisor.planning.structural_codebase_context import run_with_structural_codebase_context
    head=CodebaseHead.from_dict(structural['head'])
    def build(context):
        contract=build_scheduler_contract(instruction=instructions[TASK],head=context.head.to_dict(),source_records=source_records(bodies))
        projections=build_constraint_projections(contract=contract);cases=authored_cases();evaluations=[]
        for descriptor in cases:
            check_lease(lease);evaluation=evaluate_case(contract,descriptor['case'])
            if evaluation['evaluation_passed'] is not descriptor['expected_pass']:
                raise ValueError('finite scheduler checker disagrees with independent fixture expectation')
            observed={row['requirement_id'] for row in evaluation['violations']}
            if not set(descriptor['intended_violation_ids'])<=observed:
                raise ValueError('finite scheduler checker did not expose the expected clause violation')
            evaluations.append({'case_id':descriptor['case']['case_id'],'expected_pass':descriptor['expected_pass'],
                'intended_violation_ids':descriptor['intended_violation_ids'],'evaluation':evaluation})
        theory=build_lean_theory(contract=contract,cases=cases)
        return {**base,'contract':contract,'constraint_projections':projections,'cases':cases,'evaluations':evaluations,'theory':theory}
    with _owner(output/'structural',existing=True) as (index,_):
        return run_with_structural_codebase_context(index,output/'source-repository',build,
            repository_id=head.repository_id,expected_head=head,parent_lease=lease,
            admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)

def metadata_records(*,structural,bodies,instructions,corpus,native,codecs,lineage,built,lean):
    from constraint_metadata import build_records,row
    records=build_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,
        native=native,codecs=codecs,lineage=lineage)
    records['intent_inventories']=[row('intent-inventory',value) for value in built['inventories']]
    records['requirement_grounding']=[row('requirement-grounding',built['grounding'])]
    records['intent_logic_projections']=[row('intent-logic-projections',built['projections'])]
    records['contracts']=[row('experimental-candidate-scheduler-contract',built['contract'])]
    records['scheduler_constraint_projections']=[row('scheduler-constraint-projections',built['constraint_projections'])]
    records['scheduler_case_evaluations']=[row('authored-scheduler-case',{'descriptor':case,'evaluation':evaluation})
        for case,evaluation in zip(built['cases'],built['evaluations'])]
    records['scheduler_lean_theory']=[row('scheduler-lean-theory',built['theory'])]
    records['scheduler_lean_evidence']=[row('scheduler-lean-evidence',lean)]
    return records

def artifact_pins(output):
    names=list(FILES)
    for path in sorted((output/'lean').rglob('*')):
        if path.is_file():names.append(path.relative_to(output).as_posix())
    return [{'relative_path':name,**{key:value for key,value in pin(output/name).items() if key!='path'}} for name in sorted(names)]

def run(output):
    resource.setrlimit(resource.RLIMIT_CPU,(480,480));resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    if output.resolve()!=output or output.parent!=ROOT or output.exists():raise ValueError('exclusive owned constraint experiment required')
    output.mkdir(mode=0o700);started=time.monotonic();write(output/'policy.json',POLICY)
    corpus,bodies,instructions,lineage=inputs();write(output/'corpus-manifest.json',corpus);write(output/'lineage.json',lineage)
    repository=source_repository(output,bodies)
    for key,raw in instructions.items():
        target=output/'instructions'/key/'instruction.md';target.parent.mkdir(parents=True)
        with target.open('xb') as stream:stream.write(raw)
    from native_structural_ir import prepare_structural_ir,verify_structural_ir,_scheduler,_owner
    structural=prepare_structural_ir(repository=repository,output=output/'structural',
        repository_id='terminal-typed-constraints-20261015-01:'+output.name,expected_sources={name:sha(raw) for name,raw in bodies.items()})
    write(output/'structural-report.json',structural)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from native_capsules import build_native_capsules
    from capsule_codec import build_capsule_codec
    from metadata_projections import hydrate_and_verify_records
    from constraint_lean import compile_constraint_theory
    with _scheduler().acquire(ResourceLane.ORCHESTRATION,cpu_slots=1,memory_mb=2048,child_process_slots=1,
            timeout=30,request_id='terminal-typed-constraints:finite-model') as lease:
        native=build_native_capsules(CodebaseIRManifest.from_dict(structural['manifest']),CodebaseHead.from_dict(structural['head']))
        write(output/'native-capsules.json',native)
        codecs={s['path']:{arm:build_capsule_codec(bodies[s['path']],s['path'],s['source_cid'],structural['head'],aliases=arm=='aliased')
            for arm in ('minified','aliased')} for s in structural['sources']};write(output/'codec-views.json',codecs)
        built=build_constraint_materials(output=output,structural=structural,corpus=corpus,bodies=bodies,instructions=instructions,lease=lease)
        for key,name in [('inventories','intent-inventories.json'),('grounding','source-grounding.json'),('projections','intent-logic-projections.json'),
                ('structural_context','structural-context.json'),('contract','scheduler-contract.json'),('constraint_projections','constraint-projections.json'),
                ('cases','authored-cases.json'),('evaluations','case-evaluations.json'),('theory','lean-theory.json')]:write(output/name,built[key])
        head=CodebaseHead.from_dict(structural['head'])
        with _owner(output/'structural',existing=True) as (index,_):
            index.observe_current(repository,expected_head=head,parent_lease=lease,admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
            lean=compile_constraint_theory(built['theory'],output=output/'lean',lease=lease)
            index.observe_current(repository,expected_head=head,parent_lease=lease,admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
        write(output/'lean-evidence.json',lean)
        records=metadata_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,native=native,
            codecs=codecs,lineage=lineage,built=built,lean=lean)
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=256,child_process_slots=1,
                timeout=20,request_id='terminal-typed-constraints:metadata') as child:
            check_lease(child)
            metadata=hydrate_and_verify_records(records=records,output=output/'metadata',source_snapshot={
                'schema':'terminal-typed-constraint-metadata-snapshot@1','head':structural['head'],
                'contract_sha256':sha(wire(built['contract'])),'constraint_projections_sha256':sha(wire(built['constraint_projections'])),
                'case_evaluations_sha256':sha(wire(built['evaluations'])),'lean_theory_sha256':sha(wire(built['theory'])),
                'lean_evidence_sha256':sha(wire(lean))})
        write(output/'metadata-report.json',metadata)
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    if inputs()[3]!=lineage:raise ValueError('selected sealed source lineage changed')
    result={'schema':'terminal-typed-scheduler-constraint-experiment@1','completed':True,'policy':POLICY,'native_head':structural['head'],
        'source_count':5,'task_count':4,'authored_case_count':len(built['cases']),
        'accepted_authored_cases':sum(row['evaluation']['evaluation_passed'] for row in built['evaluations']),
        'rejected_authored_cases':sum(not row['evaluation']['evaluation_passed'] for row in built['evaluations']),
        'all_authored_case_expectations_matched':True,'new_optimizer_updates':0,'external_provider_calls':0,'source_body_execution':False,
        'metadata_original_record_counts':metadata['family_counts'],'native_capsule_inventory':native['complete_inventory'],
        'artifact_pins':artifact_pins(output),'seconds':time.monotonic()-started,
        'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**FALSE}
    write(output/'result.json',result);print(json.dumps({'completed':True,'seconds':result['seconds'],'authored_cases':result['authored_case_count']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    try:run(Path(args.output))
    except BaseException as error:
        output=Path(args.output)
        if output.is_dir() and not (output/'failure.json').exists():write(output/'failure.json',{'class':type(error).__name__,'message':str(error),**FALSE})
        traceback.print_exc();raise
