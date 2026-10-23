"""Experimental finite scheduler contracts, bound to the original source head."""
import argparse
import json
from pathlib import Path
import resource
import time
import traceback
from jsonl_io import ROOT,FALSE,inputs,read,write,wire,sha,pin
from capsule_run import source_repository,check_lease
TASK='llm-inference-batching-scheduler'
POLICY={'schema':'terminal-byte-bound-jsonl-model-policy@1','source_count':5,'task_count':4,
    'outer_wall_seconds':600,'parent_memory_mb':2048,'compiler_child_memory_mb':1024,
    'shared_native_resource_pool':True,'source_body_execution':False,'full_original_instructions_retained':True,
    'file_validation_bracket':'entry_and_exit_after_candidate_files_already_exist',
    'files':'four_owned_authored_request_and_plan_JSONL_files_per_case',
    'model_rows_source':'strict_parsing_of_observed_file_bytes_only',
    'metrics_source':'explicit_authored_exact_rationals_not_runtime_measurements',
    'formal_parser_correctness_proved':False,'physical_filesystem_immutability_proved':False,
    'original_task_satisfaction':False,'new_optimizer_updates':0,'external_provider_calls':0,
    'provider_usage':None,'full_supervisor_dispatch_exercised':False,**FALSE}
FILES=['policy.json','corpus-manifest.json','lineage.json','structural-report.json','native-capsules.json',
    'codec-views.json','base-materials.json','metadata-report.json','file-case-report.json','lean-theory.json','lean-evidence.json']

def source_records(bodies):
    return [{'path':name,'sha256':sha(raw),'source_text':raw.decode('utf-8')} for name,raw in sorted(bodies.items())]

def build_base_materials(*,output,structural,corpus,bodies,instructions,lease):
    from constraint_run import build_constraint_materials
    return build_constraint_materials(output=output,structural=structural,corpus=corpus,bodies=bodies,instructions=instructions,lease=lease)

def metadata_records(*,structural,bodies,instructions,corpus,native,codecs,lineage,base,filecases,theory,lean):
    from jsonl_metadata import build_records,row
    records=build_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,
        native=native,codecs=codecs,lineage=lineage)
    records['intent_inventories']=[row('intent-inventory',value) for value in base['inventories']]
    records['requirement_grounding']=[row('requirement-grounding',base['grounding'])]
    records['intent_logic_projections']=[row('intent-logic-projections',base['projections'])]
    records['contracts']=[row('experimental-candidate-scheduler-contract',base['contract'])]
    records['scheduler_constraint_projections']=[row('scheduler-constraint-projections',base['constraint_projections'])]
    records['jsonl_file_observations']=[row('jsonl-file-observation',{'case_id':entry['spec']['case_id'],
        'before':entry['before'],'after':entry['after']}) for entry in filecases['entries']]
    records['jsonl_file_models']=[row('jsonl-file-model',entry) for entry in filecases['entries']]
    records['jsonl_lean_theory']=[row('jsonl-derived-model-theory',theory)]
    records['jsonl_lean_evidence']=[row('jsonl-derived-model-evidence',lean)]
    return records

def artifact_pins(output):
    names=list(FILES)
    for path in sorted((output/'lean').rglob('*')):
        if path.is_file():names.append(path.relative_to(output).as_posix())
    for path in sorted((output/'file-cases').rglob('*')):
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
        repository_id='terminal-jsonl-model-20261015-01:'+output.name,expected_sources={name:sha(raw) for name,raw in bodies.items()})
    write(output/'structural-report.json',structural)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from native_capsules import build_native_capsules
    from capsule_codec import build_capsule_codec
    from metadata_projections import hydrate_and_verify_records
    from jsonl_lean import compile_constraint_theory,build_lean_theory
    from file_case_run import run_file_cases,validate_file_case_run
    with _scheduler().acquire(ResourceLane.ORCHESTRATION,cpu_slots=1,memory_mb=2048,child_process_slots=1,
            timeout=30,request_id='terminal-jsonl-model:finite-model') as lease:
        native=build_native_capsules(CodebaseIRManifest.from_dict(structural['manifest']),CodebaseHead.from_dict(structural['head']))
        write(output/'native-capsules.json',native)
        codecs={s['path']:{arm:build_capsule_codec(bodies[s['path']],s['path'],s['source_cid'],structural['head'],aliases=arm=='aliased')
            for arm in ('minified','aliased')} for s in structural['sources']};write(output/'codec-views.json',codecs)
        base=build_base_materials(output=output,structural=structural,corpus=corpus,bodies=bodies,instructions=instructions,lease=lease)
        write(output/'base-materials.json',base)
        head=CodebaseHead.from_dict(structural['head'])
        with _owner(output/'structural',existing=True) as (index,_):
            index.observe_current(repository,expected_head=head,parent_lease=lease,admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
            filecases=run_file_cases(output=output/'file-cases',contract=base['contract'])
            index.observe_current(repository,expected_head=head,parent_lease=lease,admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
            write(output/'file-case-report.json',filecases)
            theory=build_lean_theory(contract=base['contract'],cases=filecases['derived_cases'])
            write(output/'lean-theory.json',theory)
            lean=compile_constraint_theory(theory,output=output/'lean',lease=lease)
            index.observe_current(repository,expected_head=head,parent_lease=lease,admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
        write(output/'lean-evidence.json',lean)
        records=metadata_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,native=native,
            codecs=codecs,lineage=lineage,base=base,filecases=filecases,theory=theory,lean=lean)
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=256,child_process_slots=1,
                timeout=20,request_id='terminal-jsonl-model:metadata') as child:
            check_lease(child)
            metadata=hydrate_and_verify_records(records=records,output=output/'metadata',source_snapshot={
                'schema':'terminal-byte-bound-jsonl-metadata-snapshot@1','head':structural['head'],
                'contract_sha256':sha(wire(base['contract'])),'base_materials_sha256':sha(wire(base)),
                'file_cases_sha256':sha(wire(filecases)),'lean_theory_sha256':sha(wire(theory)),
                'lean_evidence_sha256':sha(wire(lean))})
        write(output/'metadata-report.json',metadata)
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    if inputs()[3]!=lineage:raise ValueError('selected sealed source lineage changed')
    pins=artifact_pins(output)
    validate_file_case_run(filecases,output=output/'file-cases',contract=base['contract'])
    result={'schema':'terminal-byte-bound-jsonl-model-experiment@1','completed':True,'policy':POLICY,'native_head':structural['head'],
        'source_count':5,'task_count':4,'file_case_count':len(filecases['entries']),
        'outcome_counts':filecases['counts'],'all_fixture_expectations_matched':True,
        'new_optimizer_updates':0,'external_provider_calls':0,'source_body_execution':False,
        'metadata_original_record_counts':metadata['family_counts'],'native_capsule_inventory':native['complete_inventory'],
        'artifact_pins':pins,'seconds':time.monotonic()-started,
        'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**FALSE}
    write(output/'result.json',result);print(json.dumps({'completed':True,'seconds':result['seconds'],'file_cases':result['file_case_count']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    try:run(Path(args.output))
    except BaseException as error:
        output=Path(args.output)
        if output.is_dir() and not (output/'failure.json').exists():write(output/'failure.json',{'class':type(error).__name__,'message':str(error),**FALSE})
        traceback.print_exc();raise
