"""Source-bound IntentIR candidates and explicit native semantic frontiers."""
import argparse
import json
from pathlib import Path
import resource
import time
import traceback
from intent_io import ROOT,FALSE,inputs,read,write,wire,sha,pin
from capsule_run import source_repository,check_lease

POLICY={'schema':'terminal-source-bound-intent-policy@1','source_count':5,'task_count':4,
    'outer_wall_seconds':600,'shared_native_resource_pool':True,'parent_memory_mb':2048,
    'complete_original_instruction_bytes_required':True,'complete_original_source_bytes_required':True,
    'source_body_execution':False,'manual_candidates_are_semantic_evidence':False,
    'native_original_task_coverage_expected':'blocked_unsupported_source_units',
    'logic_projection_scope':'unverified_intent_declarations_and_types',
    'provider_usage':None,'external_provider_calls':0,'new_optimizer_updates':0,
    'full_supervisor_invoked':False,**FALSE}
FILES=['policy.json','corpus-manifest.json','lineage.json','structural-report.json','native-capsules.json',
    'codec-views.json','tokenizer.json','metadata-report.json','intent-inventories.json','grounding.json',
    'logic-projections.json','lean-validation.json','structural-context.json']

def source_records(bodies):
    return [{'path':name,'sha256':sha(raw),'source_text':raw.decode('utf-8')} for name,raw in sorted(bodies.items())]

def build_intent_materials(*,output,structural,corpus,bodies,instructions,lease):
    from native_structural_ir import _owner
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_accelerate_py.agent_supervisor.planning.structural_codebase_context import run_with_structural_codebase_context
    from clause_inventory import build_instruction_inventory
    from requirement_grounding import build_requirement_grounding
    from logic_projections import build_logic_projections
    head=CodebaseHead.from_dict(structural['head'])
    def build(context):
        check_lease(lease)
        inventories=[build_instruction_inventory(task_id=task['task_id'],instruction=instructions[task['task_id']])
            for task in corpus['tasks']]
        grounding=build_requirement_grounding(inventories=inventories,source_records=source_records(bodies),
            structural_manifest=structural['manifest'],head=context.head.to_dict(),corpus=corpus)
        projections=build_logic_projections(inventories=inventories)
        materials=context.to_plan_create_materials()
        return {'inventories':inventories,'grounding':grounding,'projections':projections,
            'structural_context':{'native_context':context.to_dict(),
                'native_plan_materials':{'scan':materials.scan,'extra':materials.extra,
                    'current_facts_count':len(materials.current_facts)},
                'current_owner_entry_and_exit_checks_required':True,'worker_dispatched_inside_build_callback':False,
                'new_optimizer_updates':0,'external_provider_calls':0,'source_body_execution':False,**FALSE}}
    with _owner(output/'structural',existing=True) as (index,_):
        built=run_with_structural_codebase_context(index,output/'source-repository',build,
            repository_id=head.repository_id,expected_head=head,parent_lease=lease,
            admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
    return built

def metadata_records(*,structural,bodies,instructions,corpus,native,codecs,lineage,built,lean):
    from intent_metadata import build_records,row
    records=build_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,
        native=native,codecs=codecs,lineage=lineage)
    records['intent_inventories']=[row('intent-inventory',value) for value in built['inventories']]
    records['requirement_grounding']=[row('requirement-grounding',built['grounding'])]
    records['intent_logic_projections']=[row('intent-logic-projections',built['projections'])]
    records['intent_lean_validation']=[row('intent-lean-validation',lean)]
    return records

def artifact_pins(output):
    names=list(FILES)
    for path in sorted((output/'lean').rglob('*')):
        if path.is_file():names.append(path.relative_to(output).as_posix())
    return [{'relative_path':name,**{key:value for key,value in pin(output/name).items() if key!='path'}} for name in sorted(names)]

def run(output):
    resource.setrlimit(resource.RLIMIT_CPU,(480,480));resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    if output.resolve()!=output or output.parent!=ROOT or output.exists():raise ValueError('exclusive owned intent experiment required')
    output.mkdir(mode=0o700);started=time.monotonic();write(output/'policy.json',POLICY)
    corpus,bodies,instructions,lineage=inputs();write(output/'corpus-manifest.json',corpus);write(output/'lineage.json',lineage)
    repository=source_repository(output,bodies)
    for key,raw in instructions.items():
        path=output/'instructions'/key/'instruction.md';path.parent.mkdir(parents=True)
        with path.open('xb') as stream:stream.write(raw)
    from native_structural_ir import prepare_structural_ir,verify_structural_ir,_scheduler,_owner
    structural=prepare_structural_ir(repository=repository,output=output/'structural',
        repository_id='terminal-intent-coverage-20261015-01:'+output.name,expected_sources={key:sha(raw) for key,raw in bodies.items()})
    write(output/'structural-report.json',structural)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from native_capsules import build_native_capsules
    from capsule_codec import build_capsule_codec
    from token_cost_review import load_tokenizer
    from metadata_projections import hydrate_and_verify_records
    from logic_projections import compile_lean_projections
    with _scheduler().acquire(ResourceLane.ORCHESTRATION,cpu_slots=1,memory_mb=2048,child_process_slots=1,
            timeout=30,request_id='terminal-intent-coverage:source-bound-ir') as lease:
        check_lease(lease)
        native=build_native_capsules(CodebaseIRManifest.from_dict(structural['manifest']),CodebaseHead.from_dict(structural['head']))
        write(output/'native-capsules.json',native)
        codecs={s['path']:{arm:build_capsule_codec(bodies[s['path']],s['path'],s['source_cid'],structural['head'],
            aliases=arm=='aliased') for arm in ('minified','aliased')} for s in structural['sources']}
        write(output/'codec-views.json',codecs);_,descriptor=load_tokenizer();write(output/'tokenizer.json',descriptor)
        built=build_intent_materials(output=output,structural=structural,corpus=corpus,bodies=bodies,instructions=instructions,lease=lease)
        write(output/'intent-inventories.json',built['inventories']);write(output/'grounding.json',built['grounding'])
        write(output/'logic-projections.json',built['projections']);write(output/'structural-context.json',built['structural_context'])
        head=CodebaseHead.from_dict(structural['head'])
        with _owner(output/'structural',existing=True) as (index,_):
            index.observe_current(repository,expected_head=head,parent_lease=lease,
                admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
            lean=compile_lean_projections(built['projections'],output=output/'lean',lease=lease)
            index.observe_current(repository,expected_head=head,parent_lease=lease,
                admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
        write(output/'lean-validation.json',lean)
        records=metadata_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,native=native,
            codecs=codecs,lineage=lineage,built=built,lean=lean)
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=256,child_process_slots=1,
                timeout=20,request_id='terminal-intent-coverage:metadata') as child:
            check_lease(child)
            metadata=hydrate_and_verify_records(records=records,output=output/'metadata',source_snapshot={
                'schema':'terminal-intent-coverage-metadata-snapshot@1','head':structural['head'],
                'inventory_sha256':sha(wire(built['inventories'])),'grounding_sha256':sha(wire(built['grounding'])),
                'logic_projection_sha256':sha(wire(built['projections'])),'lean_validation_sha256':sha(wire(lean))})
        write(output/'metadata-report.json',metadata)
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    if inputs()[3]!=lineage:raise ValueError('sealed selected input lineage changed during run')
    result={'schema':'terminal-source-bound-intent-experiment@1','completed':True,'policy':POLICY,'native_head':structural['head'],
        'source_count':5,'task_count':4,'new_optimizer_updates':0,'external_provider_calls':0,'source_body_execution':False,
        'metadata_original_record_counts':metadata['family_counts'],'native_capsule_inventory':native['complete_inventory'],
        'artifact_pins':artifact_pins(output),'seconds':time.monotonic()-started,
        'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**FALSE}
    write(output/'result.json',result);print(json.dumps({'completed':True,'seconds':result['seconds'],'sources':5,'instructions':4}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    try:run(Path(args.output))
    except BaseException as error:
        output=Path(args.output)
        if output.is_dir() and not (output/'failure.json').exists():write(output/'failure.json',{'class':type(error).__name__,'message':str(error),**FALSE})
        traceback.print_exc();raise
