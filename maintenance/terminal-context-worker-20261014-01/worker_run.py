"""Fresh source/index/context plus observed, budgeted local worker delivery."""
import argparse
import json
from pathlib import Path
import resource
import time
import traceback
from worker_io import ROOT,FALSE,inputs,read,write,wire,sha,pin
from capsule_run import source_repository,check_lease

POLICY={'schema':'terminal-generic-context-worker-policy@1','sources':5,'tasks':4,
 'worker_profile':'experimental-planning-local-router-consumer@1','outer_wall_seconds':600,
 'source_body_execution':False,'full_instruction_bytes_required':True,'all_task_sources_required':True,
 'all_requirements_unresolved':True,'context_input_tokens_max':20000,'worker_input_tokens_max':20000,
 'native_shared_memory_mb':1024,'provider_usage':None,'actual_external_provider_invocations':0,
 'full_supervisor_task_admission_exercised':False,'separate_worker_uid_boundary_qualified':False,**FALSE}
MODES=('expanded','adaptive','decode_before_model')
FOLLOWUPS=('Continue planning using every required source and unresolved instruction.',
 'Check the remaining obligations against the same complete source context.')
SYSTEM='Review the complete original task and source context. Preserve all instruction, source and residual bytes. Representations grant no execution, completion or proof authority.'

def build_contexts(*,output,structural,corpus,instructions,native,metadata,tokenizer,descriptor,lease):
    from native_structural_ir import _owner
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_accelerate_py.agent_supervisor.planning.structural_codebase_context import run_with_structural_codebase_context
    from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as metadata_api
    from worker_metadata import select_task_rows
    from context_projection import compile_task_context,task_capsule_summaries
    from packing_run import pack_projection
    head=CodebaseHead.from_dict(structural['head'])
    metadata_api.validate_codebase_ir_metadata(output=output/'metadata',expected=metadata['native_metadata'],fresh_process=False)
    def build(context):
        materials=context.to_plan_create_materials();tasks=[]
        for task in corpus['tasks']:
            check_lease(lease)
            sources,codecs=select_task_rows(metadata_output=output/'metadata',native_metadata=metadata['native_metadata'],
                task=task,head=context.head.to_dict())
            projection=compile_task_context(task=task,instruction=instructions[task['task_id']],head=context.head.to_dict(),
                source_rows=sources,codec_rows=codecs,capsule_summaries=task_capsule_summaries(native['capsules'],set(sources)),
                tokenizer=tokenizer,arm='raw')
            packing=pack_projection(projection,instructions[task['task_id']],descriptor)
            tasks.append({'task_id':task['task_id'],'projection':projection,'packing':packing})
        return {'tasks':tasks,'native_structural_context':context.to_dict(),
            'native_plan_materials':{'scan':materials.scan,'extra':materials.extra,
                'current_facts_count':len(materials.current_facts),'current_roots':None},
            'worker_dispatched_inside_build_callback':False,**FALSE}
    with _owner(output/'structural',existing=True) as (index,_):
        contexts=run_with_structural_codebase_context(index,output/'source-repository',build,
            repository_id=head.repository_id,expected_head=head,parent_lease=lease,
            admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
    metadata_api.validate_codebase_ir_metadata(output=output/'metadata',expected=metadata['native_metadata'],fresh_process=False)
    return contexts

def make_request(task,mode,step,descriptor,previous):
    messages=[{'message_id':'system','role':'system','content':SYSTEM},
        {'message_id':'context','role':'user','content':task['projection']['rendered']}]
    for i,text in enumerate(FOLLOWUPS[:min(step,2)]):
        messages.append({'message_id':'followup:'+str(i+1),'role':'user','content':text})
    session=task['task_id']+':'+mode
    return {'schema':'terminal-complete-context-worker-request@1','request_id':session+':'+str(step),
        'session_id':session,'expected_head':task['packing']['nested_document']['context']['scope']['head'],
        'original_rendered':task['projection']['rendered'],
        'packed_wire':task['packing']['variants']['reference_lifted']['wire'],'messages':messages,
        'context_message_id':'context','max_input_tokens':20000,'tokenizer_descriptor':descriptor,
        'history_required_ids':[row['message_id'] for row in previous],
        'delivery_mode':mode,'previous_message_manifest':previous}

def dispatch_current(*,index,repository,head,request,lease,output_dir):
    from worker_capture import launch_capture
    check_lease(lease)
    index.observe_current(repository,expected_head=head,parent_lease=lease,
        admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
    result=launch_capture(request=request,repository=repository,lease=lease,output_dir=output_dir,timeout_seconds=30)
    index.observe_current(repository,expected_head=head,parent_lease=lease,
        admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
    return result

def dispatch_contexts(*,output,structural,contexts,descriptor,lease):
    from native_structural_ir import _owner
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from worker_capture import launch_capture
    head=CodebaseHead.from_dict(structural['head']);sessions=[]
    with _owner(output/'structural',existing=True) as (index,_):
        for task in contexts['tasks']:
            for mode in MODES:
                previous=[];calls=[]
                for step in range(4):
                    check_lease(lease)
                    request=make_request(task,mode,step,descriptor,previous)
                    # Structural build callbacks materialize data only. Worker
                    # launch is a separate resource-admitted operation, fenced
                    # by genuine source observations before and after delivery.
                    destination=output/'workers'/task['task_id']/mode/('turn-'+str(step))
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    observation=dispatch_current(index=index,repository=output/'source-repository',head=head,
                        request=request,lease=lease,output_dir=destination)
                    previous=observation['observation']['selected_message_manifest']
                    calls.append({'step':step,'retry_of':2 if step==3 else None,
                        'request':request,'capture':observation,'owner_current_before_and_after':True})
                sessions.append({'task_id':task['task_id'],'delivery_mode':mode,'calls':calls,
                    'actual_local_consumer_calls':4,'scripted_followups':True,'model_outputs_produced':False,**FALSE})
    return {'schema':'terminal-generic-context-worker-deliveries@1','sessions':sessions,
        'actual_low_level_native_worker_dispatches':48,'actual_local_router_consumer_calls':48,
        'actual_external_provider_invocations':0,'provider_usage':None,'source_body_execution':False,**FALSE}

FILES=['policy.json','corpus-manifest.json','lineage.json','structural-report.json','native-capsules.json',
    'codec-views.json','tokenizer.json','metadata-report.json','contexts.json','deliveries.json']

def run(output):
    resource.setrlimit(resource.RLIMIT_CPU,(480,480));resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    if output.resolve()!=output or output.parent!=ROOT or output.exists():raise ValueError('exclusive owned worker experiment required')
    output.mkdir(mode=0o700);started=time.monotonic();write(output/'policy.json',POLICY)
    corpus,bodies,instructions,lineage=inputs();write(output/'corpus-manifest.json',corpus);write(output/'lineage.json',lineage)
    repository=source_repository(output,bodies)
    for key,raw in instructions.items():
        path=output/'instructions'/key/'instruction.md';path.parent.mkdir(parents=True)
        with path.open('xb') as stream:stream.write(raw)
    from native_structural_ir import prepare_structural_ir,verify_structural_ir,_scheduler
    structural=prepare_structural_ir(repository=repository,output=output/'structural',
        repository_id='terminal-context-worker-20261014-01:'+output.name,expected_sources={p:sha(raw) for p,raw in bodies.items()})
    write(output/'structural-report.json',structural)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from native_capsules import build_native_capsules
    from capsule_codec import build_capsule_codec
    from token_cost_review import load_tokenizer
    from worker_metadata import build_records
    from metadata_projections import hydrate_and_verify_records
    with _scheduler().acquire(ResourceLane.ORCHESTRATION,cpu_slots=1,memory_mb=1024,child_process_slots=1,
            timeout=30,request_id='terminal-context-worker:observed-delivery') as lease:
        check_lease(lease)
        native=build_native_capsules(CodebaseIRManifest.from_dict(structural['manifest']),CodebaseHead.from_dict(structural['head']))
        write(output/'native-capsules.json',native)
        codecs={s['path']:{arm:build_capsule_codec(bodies[s['path']],s['path'],s['source_cid'],structural['head'],
            aliases=arm=='aliased') for arm in ['minified','aliased']} for s in structural['sources']}
        write(output/'codec-views.json',codecs)
        tokenizer,descriptor=load_tokenizer();write(output/'tokenizer.json',descriptor)
        records=build_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,
            native=native,codecs=codecs,lineage=lineage)
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=256,child_process_slots=1,
                timeout=20,request_id='terminal-context-worker:metadata') as child:
            check_lease(child)
            metadata=hydrate_and_verify_records(records=records,output=output/'metadata',source_snapshot={
                'schema':'terminal-context-worker-snapshot@1','head':structural['head'],
                'native_capsule_set_id':native['capsule_set_id'],'codec_views_sha256':sha(wire(codecs)),
                'instructions':{key:sha(value) for key,value in instructions.items()}})
        write(output/'metadata-report.json',metadata)
        contexts=build_contexts(output=output,structural=structural,corpus=corpus,instructions=instructions,
            native=native,metadata=metadata,tokenizer=tokenizer,descriptor=descriptor,lease=lease)
        write(output/'contexts.json',contexts)
        deliveries=dispatch_contexts(output=output,structural=structural,contexts=contexts,descriptor=descriptor,lease=lease)
        write(output/'deliveries.json',deliveries)
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    if inputs()[3]!=lineage:raise ValueError('selected public inputs changed during worker delivery')
    artifacts=[{'relative_path':name,**{k:v for k,v in pin(output/name).items() if k!='path'}} for name in sorted(FILES)]
    # Include exact worker stdout/stderr, process custody and fresh public router
    # allocation files, including any failed attempts retained by the launcher.
    for path in sorted((output/'workers').rglob('*')):
        if path.is_file():artifacts.append({'relative_path':path.relative_to(output).as_posix(),
            **{k:v for k,v in pin(path).items() if k!='path'}})
    result={'schema':'terminal-generic-context-worker-experiment@1','completed':True,'policy':POLICY,
        'native_head':structural['head'],'source_count':5,'task_count':4,'sessions':12,'worker_child_invocations':48,
        'local_consumer_calls':48,'actual_external_provider_invocations':0,'new_optimizer_updates':0,'new_prover_invocations':0,
        'source_body_execution':False,'metadata_original_record_counts':metadata['family_counts'],
        'native_capsule_inventory':native['complete_inventory'],'artifact_pins':sorted(artifacts,key=lambda v:v['relative_path']),
        'seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**FALSE}
    write(output/'result.json',result);print(json.dumps({'completed':True,'seconds':result['seconds'],
        'native_processes':48,'local_consumer_calls':48,'external_provider_invocations':0}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    try:run(Path(args.output))
    except BaseException as error:
        output=Path(args.output)
        if output.is_dir() and not (output/'failure.json').exists():write(output/'failure.json',{'class':type(error).__name__,'message':str(error),**FALSE})
        traceback.print_exc();raise
