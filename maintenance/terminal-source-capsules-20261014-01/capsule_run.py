"""Current indexed source -> genuine capsules -> native context -> local costs."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import time
import traceback
from capsule_io import ROOT,FALSE,inputs,read,write,wire,sha,pin

POLICY={'schema':'terminal-source-capsule-policy@1','sources':5,'tasks':4,
 'source_bytes_per_file':8192,'source_total_bytes':15788,'native_edges_max':512,
 'native_symbols_max':57,'native_capsule_report_bytes_max':8*1024**2,
 'full_instruction_bytes_required':True,'all_task_sources_required':True,'unresolved_requirements_retained':True,
 'raw_source_required_before_edit':True,'learned_scores_used_for_omission':False,
 'context_input_tokens_max':20000,'outer_wall_seconds':300,'cpu_seconds_hard_limit':240,
 'address_space_bytes_hard_limit':8*1024**3,'file_bytes_hard_limit':32*1024**2,
 'native_shared_memory_mb':1024,'source_body_execution':False,'provider_usage':None,
 'token_measurement':'pinned offline o200k full serialized counterfactual messages',**FALSE}

def source_repository(output,bodies):
 repository=output/'source-repository';repository.mkdir()
 for path,raw in sorted(bodies.items()):
  target=repository/path;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as stream:stream.write(raw)
 commands=[['init','-q'],['add','--',*sorted(bodies)],['-c','user.name=Source capsule experiment',
  '-c','user.email=local-experiment@localhost','commit','-q','-m','Fixed public source-only capsule corpus']]
 for command in commands:
  result=subprocess.run(['git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false',
   '-c','init.templateDir=','-C',str(repository),*command],stdout=subprocess.PIPE,
   stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,timeout=10)
  if result.returncode or result.stderr:raise ValueError('exclusive source-only Git capture failed')
 return repository

def check_lease(lease):
 from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import LeaseCancelledError
 if lease.cancelled:raise LeaseCancelledError('native source capsule lease cancelled')

def build_indexed_contexts(*,output,structural,corpus,instructions,native,metadata,tokenizer,descriptor,lease):
 from native_structural_ir import _owner,_scheduler
 from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
 from ipfs_accelerate_py.agent_supervisor.planning.structural_codebase_context import run_with_structural_codebase_context
 from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as metadata_api
 from metadata_selection import select_task_rows
 from context_projection import compile_task_context,task_capsule_summaries
 from scenario_costs import evaluate_scenarios
 head=CodebaseHead.from_dict(structural['head'])
 metadata_api.validate_codebase_ir_metadata(output=output/'metadata',expected=metadata['native_metadata'],fresh_process=False)
 def build(context):
  materials=context.to_plan_create_materials()
  result=[]
  for task in corpus['tasks']:
   check_lease(lease)
   sources,codecs=select_task_rows(metadata_output=output/'metadata',native_metadata=metadata['native_metadata'],
    task=task,head=context.head.to_dict())
   paths=set(sources);summaries=task_capsule_summaries(native['capsules'],paths)
   projections={arm:compile_task_context(task=task,instruction=instructions[task['task_id']],
    head=context.head.to_dict(),source_rows=sources,codec_rows=codecs,capsule_summaries=summaries,
    tokenizer=tokenizer,arm=arm) for arm in ['raw','minified','aliased']}
   measured=evaluate_scenarios(projections,sources,codecs,descriptor)
   result.append({'task_id':task['task_id'],'source_paths':sorted(paths),'projections':projections,'scenarios':measured})
  return {'tasks':result,'native_structural_context':context.to_dict(),
   'native_plan_materials':{'scan':materials.scan,'extra':materials.extra,
    'current_facts_count':len(materials.current_facts),'current_roots':None},
   'native_context_compiler_exercised':True,'native_plan_create_service_activated':False,
   'source_views_selected_through_actual_duckdb':True,'data_not_published_inside_observation':True,**FALSE}
 with _owner(output/'structural',existing=True) as (index,_):
  result=run_with_structural_codebase_context(index,output/'source-repository',build,
   repository_id=head.repository_id,expected_head=head,parent_lease=lease,
   admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
 metadata_api.validate_codebase_ir_metadata(output=output/'metadata',expected=metadata['native_metadata'],fresh_process=False)
 return result

def run(output):
 resource.setrlimit(resource.RLIMIT_CPU,(240,240));resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
 resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
 if output.resolve()!=output or output.parent!=ROOT or output.exists():raise ValueError('exclusive owned experiment required')
 output.mkdir(mode=0o700);write(output/'policy.json',POLICY);started=time.monotonic()
 corpus,bodies,instructions,lineage=inputs()
 write(output/'corpus-manifest.json',corpus);write(output/'lineage.json',lineage)
 repository=source_repository(output,bodies)
 for task in corpus['tasks']:
  directory=output/'instructions'/task['task_id'];directory.mkdir(parents=True)
  with (directory/'instruction.md').open('xb') as stream:stream.write(instructions[task['task_id']])
 from native_structural_ir import prepare_structural_ir,_owner,_scheduler,verify_structural_ir
 structural=prepare_structural_ir(repository=repository,output=output/'structural',
  repository_id='terminal-source-capsules-20261014-01:'+output.name,
  expected_sources={p:sha(raw) for p,raw in bodies.items()})
 write(output/'structural-report.json',structural)
 from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
 from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
 from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
 from native_capsules import build_native_capsules
 from capsule_codec import build_capsule_codec,expand_capsule_codec
 from token_cost_review import load_tokenizer
 from metadata_selection import build_records
 from metadata_projections import hydrate_and_verify_records
 with _scheduler().acquire(ResourceLane.ORCHESTRATION,cpu_slots=1,memory_mb=1024,child_process_slots=1,
  timeout=30,request_id='terminal-source-capsules:context-cost') as lease:
  check_lease(lease)
  native=build_native_capsules(CodebaseIRManifest.from_dict(structural['manifest']),CodebaseHead.from_dict(structural['head']))
  write(output/'native-capsules.json',native)
  codecs={}
  for source in structural['sources']:
   path=source['path'];codecs[path]={}
   for arm in ['minified','aliased']:
    record=build_capsule_codec(bodies[path],path,source['source_cid'],structural['head'],aliases=arm=='aliased')
    if expand_capsule_codec(record,structural['head'],source['sha256'],source['source_cid'],expected_path=path)!=bodies[path]:
     raise ValueError('complete original source roundtrip differs')
    codecs[path][arm]=record
  write(output/'codec-views.json',codecs)
  tokenizer,descriptor=load_tokenizer();write(output/'tokenizer.json',descriptor)
  records=build_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,
   native=native,codecs=codecs,lineage=lineage)
  with lease.acquire_child(lane=ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=256,child_process_slots=1,
   timeout=20,request_id='terminal-source-capsules:metadata') as child:
   check_lease(child)
   metadata=hydrate_and_verify_records(records=records,output=output/'metadata',
    source_snapshot={'schema':'terminal-source-capsule-snapshot@1','head':structural['head'],
     'native_capsule_set_id':native['capsule_set_id'],'codec_views_sha256':sha(wire(codecs)),
     'instructions':{key:sha(value) for key,value in instructions.items()}})
  write(output/'metadata-report.json',metadata)
  contexts=build_indexed_contexts(output=output,structural=structural,corpus=corpus,instructions=instructions,
   native=native,metadata=metadata,tokenizer=tokenizer,descriptor=descriptor,lease=lease)
  # Derived contexts become durable only after both genuine owner observations.
  write(output/'context-costs.json',contexts)
 verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
 if inputs()[3]!=lineage:raise ValueError('selected sealed public inputs changed')
 files=['policy.json','corpus-manifest.json','lineage.json','structural-report.json','native-capsules.json',
  'codec-views.json','tokenizer.json','metadata-report.json','context-costs.json']
 artifacts=[{'relative_path':name,**{k:v for k,v in pin(output/name).items() if k!='path'}} for name in sorted(files)]
 result={'schema':'terminal-current-source-capsule-experiment@1','completed':True,'policy':POLICY,
  'native_head':structural['head'],'source_count':5,'task_count':4,
  'native_capsule_inventory':native['complete_inventory'],'old_adapter_refusal':native['sealed_adapter_outcome'],
  'metadata_original_record_counts':metadata['family_counts'],'source_roundtrips':10,'context_compilations':12,
  'paired_local_scenarios':32,'artifact_pins':artifacts,'provider_invocations':0,'new_optimizer_updates':0,
  'new_prover_invocations':0,'native_structural_context_and_plan_materials_exercised':True,
  'native_context_compiler_exercised':True,'planning_requirements_all_unresolved':True,
  'token_accounting_is_counterfactual':True,'source_body_execution':False,
  'seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**FALSE}
 write(output/'result.json',result);print(json.dumps({'completed':True,'seconds':result['seconds'],
  'source_roundtrips':10,'context_compilations':12,'counterfactual_pairs':32,'provider_invocations':0}))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
 try:run(Path(args.output))
 except BaseException as error:
  destination=Path(args.output)
  if destination.is_dir() and not (destination/'failure.json').exists():
   write(destination/'failure.json',{'class':type(error).__name__,'message':str(error),**FALSE})
  traceback.print_exc();raise
